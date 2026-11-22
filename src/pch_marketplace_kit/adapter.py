"""The port between the hub and one Marketplace: what an adapter must provide and the errors it may raise."""
from dataclasses import dataclass, field
from typing import Any, Protocol

from pch_marketplace_kit.domain import ListingCandidate


# optional canonical fields an adapter may declare it provides; the others are "not applicable" for it
CAPABILITIES: frozenset[str] = frozenset({"description", "images", "location", "seller", "condition", "published_at"})


class InvalidParams(ValueError):
    """Marketplace Query params rejected by an adapter; each error is (location inside params, message)."""

    def __init__(self, errors: list[tuple[tuple[str, ...], str]]):
        super().__init__("; ".join(f"{'.'.join(loc)}: {msg}" for loc, msg in errors))
        self.errors = errors


class TransientMarketplaceError(Exception):
    """Worth retrying later: network, timeout, 5xx, 429 once the HTTP client's own retries are exhausted."""


class PermanentMarketplaceError(Exception):
    """Retrying will not help: 4xx, unexpected response schema. `status` is the HTTP status when there is one."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Rejected:
    """A listing the Marketplace returned without the minimum data to become a Listing."""

    external_id: str | None
    reason: str


@dataclass(frozen=True)
class Page:
    candidates: list[ListingCandidate]
    rejected: list[Rejected] = field(default_factory=list)
    next_cursor: Any | None = None
    # results sorted newest first: a fully unchanged page means everything after it is known too
    newest_first: bool = False


class MarketplaceAdapter(Protocol):
    """Port to one Marketplace. Adapters translate only: no persistence, dedup or notifications."""

    marketplace: str
    # optional canonical fields this Marketplace can provide; the others are "not applicable" (ADR-0005)
    capabilities: frozenset[str]

    def validate_params(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return normalised params for a Marketplace Query, or raise InvalidParams."""
        ...

    def fetch_page(self, params: dict[str, Any], cursor: Any | None) -> Page:
        """Fetch one page (cursor None = first page). Raises only Transient/PermanentMarketplaceError."""
        ...
