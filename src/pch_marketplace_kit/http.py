"""Rate-limited HTTP client shared by the Marketplace adapters (one instance per Marketplace).

Enforces a minimum interval between requests, timeouts, retries with exponential backoff and jitter,
`Retry-After` on 429, and classifies failures as Transient/PermanentMarketplaceError for the pipeline.
"""
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from pch_marketplace_kit.adapter import PermanentMarketplaceError, TransientMarketplaceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HttpPolicy:
    min_interval_s: float = 2.0
    timeout_s: float = 30.0
    max_retries: int = 3
    backoff_base_s: float = 2.0
    backoff_cap_s: float = 60.0
    # a longer Retry-After would stall the worker: fail as transient and let the next run try
    max_retry_after_s: float = 120.0


def equal_jitter(delay: float) -> float:
    """Between half and all of the delay: keeps retries spread out without collapsing to zero."""
    return delay / 2 + random.uniform(0, delay / 2)


class _Retry(Exception):
    def __init__(self, reason: str, status: int | None = None, retry_after: float | None = None):
        super().__init__(reason)
        self.status = status
        self.retry_after = retry_after


class MarketplaceHttp:
    def __init__(
        self,
        marketplace: str,
        policy: HttpPolicy,
        session: Any | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        jitter: Callable[[float], float] = equal_jitter,
    ):
        self.marketplace = marketplace
        self.policy = policy
        self.session = session if session is not None else requests.Session()
        self.clock = clock
        self.sleep = sleep
        self.wall_clock = wall_clock
        self.jitter = jitter
        self._last_request_at: float | None = None

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
        response = self.get(url, params=params, headers=headers)
        try:
            return response.json()
        except ValueError as exc:
            raise PermanentMarketplaceError(f"{self.marketplace}: expected JSON from {_redact(url)}, got {response.headers.get('Content-Type', 'unknown content')}") from exc

    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> requests.Response:
        delay = 0.0
        for attempt in range(self.policy.max_retries + 1):
            self._wait(delay)
            try:
                return self._attempt(url, params, headers)
            except _Retry as retry:
                if attempt == self.policy.max_retries:
                    raise TransientMarketplaceError(f"{self.marketplace}: {retry} after {attempt + 1} attempts") from None
                if retry.retry_after is not None:
                    if retry.retry_after > self.policy.max_retry_after_s:
                        raise TransientMarketplaceError(
                            f"{self.marketplace}: Retry-After of {retry.retry_after:.0f} s exceeds {self.policy.max_retry_after_s:.0f} s"
                        ) from None
                    delay = retry.retry_after
                else:
                    delay = self.jitter(min(self.policy.backoff_cap_s, self.policy.backoff_base_s * 2**attempt))
                logger.warning(
                    "marketplace request retried",
                    extra={"event": "http_retry", "marketplace": self.marketplace, "attempt": attempt + 1, "status": retry.status,
                           "reason": str(retry), "delay_s": delay, "url": _redact(url)},
                )
        raise AssertionError("unreachable")

    def _attempt(self, url: str, params: dict | None, headers: dict | None) -> requests.Response:
        self._last_request_at = self.clock()
        try:
            response = self.session.request("GET", url, params=params, headers=headers, timeout=self.policy.timeout_s)
        except requests.Timeout as exc:
            raise _Retry("timeout") from exc
        except requests.ConnectionError as exc:
            raise _Retry("connection error") from exc
        status = response.status_code
        if status == 429:
            raise _Retry("HTTP 429", status, self._retry_after(response.headers.get("Retry-After")))
        if status >= 500:
            raise _Retry(f"HTTP {status}", status)
        if status >= 400:
            raise PermanentMarketplaceError(f"{self.marketplace}: HTTP {status} from {_redact(url)}", status=status)
        return response

    def _wait(self, backoff: float) -> None:
        """One sleep covering both the backoff and the minimum interval since the previous request."""
        interval_left = 0.0
        if self._last_request_at is not None:
            interval_left = self.policy.min_interval_s - (self.clock() - self._last_request_at)
        wait = max(backoff, interval_left)
        if wait > 0:
            self.sleep(wait)

    def _retry_after(self, value: str | None) -> float | None:
        if not value:
            return None
        if value.strip().isdigit():
            return float(value.strip())
        try:
            return max(0.0, (parsedate_to_datetime(value) - self.wall_clock()).total_seconds())
        except (TypeError, ValueError):
            return None  # unparseable: fall back to backoff


def _redact(url: str) -> str:
    """Drop query and fragment: they can carry session ids or tokens."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
