"""Test helpers for adapter packages: a fake HTTP session and clock, and contract checks.

Nothing here touches the network or really sleeps. Use them from pytest:

    time = FakeTime()
    session = FakeSession(time, [response(200, payload)])
    adapter = MyAdapter(session=session, clock=time.clock, sleep=time.sleep)
    page = adapter.fetch_page(adapter.validate_params({...}), None)
    assert_valid_page(page)
"""
import json
from datetime import UTC, datetime
from typing import Any

import requests

from pch_marketplace_kit.adapter import CAPABILITIES, MarketplaceAdapter, Page, Rejected
from pch_marketplace_kit.domain import ListingCandidate

WALL_START = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def response(status: int, body: object = None, headers: dict | None = None, raw: bytes | None = None, url: str = "https://marketplace.test/api") -> requests.Response:
    """A real `requests.Response` with a JSON body (or `raw` bytes)."""
    r = requests.Response()
    r.status_code = status
    r._content = raw if raw is not None else json.dumps(body if body is not None else {}).encode()
    r.headers.update({"Content-Type": "application/json", **(headers or {})})
    r.url = url
    return r


class FakeTime:
    """Monotonic clock that only moves when the code under test sleeps."""

    def __init__(self, start: float = 1000.0):
        self.start = start
        self.now = start
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def wall(self) -> datetime:
        return datetime.fromtimestamp(WALL_START.timestamp() + (self.now - self.start), UTC)


class FakeSession:
    """Plays back scripted outcomes (responses or exceptions) and records each call with its time."""

    def __init__(self, time: FakeTime, outcomes: list):
        self.time = time
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []
        self.cookies = requests.cookies.RequestsCookieJar()

    def request(self, method, url, params=None, headers=None, timeout=None, **kwargs):
        self.calls.append({"method": method, "url": url, "params": params, "headers": headers, "timeout": timeout, "at": self.time.now, **kwargs})
        if not self.outcomes:
            raise AssertionError(f"unexpected request: {method} {url}")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def assert_adapter_shape(adapter: MarketplaceAdapter) -> None:
    """The static part of the contract: a Marketplace name and known capabilities."""
    assert isinstance(adapter.marketplace, str) and adapter.marketplace, "marketplace must be a non-empty string"
    assert adapter.marketplace == adapter.marketplace.lower() and adapter.marketplace.isidentifier(), "marketplace must be a lower-case identifier"
    assert isinstance(adapter.capabilities, frozenset), "capabilities must be a frozenset"
    unknown = adapter.capabilities - CAPABILITIES
    assert not unknown, f"unknown capabilities: {sorted(unknown)}"
    assert callable(adapter.validate_params) and callable(adapter.fetch_page)


def assert_valid_page(page: Page, capabilities: frozenset[str] | None = None) -> None:
    """A page honours the contract; with `capabilities`, no candidate fills a field the adapter did not declare."""
    assert isinstance(page, Page), f"fetch_page must return a Page, got {type(page).__name__}"
    assert all(isinstance(c, ListingCandidate) for c in page.candidates), "candidates must be ListingCandidate"
    assert all(isinstance(r, Rejected) and r.reason for r in page.rejected), "rejected entries must be Rejected with a reason"
    ids = [c.external_id for c in page.candidates]
    assert len(ids) == len(set(ids)), "a page must not repeat an external_id"
    assert all(c.raw_payload for c in page.candidates), "every candidate keeps its original payload"
    if capabilities is not None:
        fields = {"description": "description", "images": "images", "location": "location", "seller": "seller_external_id",
                  "condition": "condition", "published_at": "published_at"}
        for capability, field in fields.items():
            if capability not in capabilities:
                filled = [c.external_id for c in page.candidates if getattr(c, field)]
                assert not filled, f"{field} filled without the {capability!r} capability: {filled[:5]}"
