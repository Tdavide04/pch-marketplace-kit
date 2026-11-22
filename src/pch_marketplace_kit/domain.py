"""Pure domain types shared by the adapters and the hub: the canonical form of a listing."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, get_args
from urllib.parse import urlsplit

PriceStatus = Literal["priced", "free", "on_request", "missing"]
# canonical item condition; adapters map their own scale onto it and keep the original in condition_raw (ADR-0005)
Condition = Literal["new", "like_new", "good", "fair", "poor", "not_applicable"]
# total cost = price + shipping + mandatory fees; unknown shipping is never treated as zero (ADR-0011)
ShippingStatus = Literal["known", "unknown", "pickup_only"]

PRICE_STATUSES: tuple[str, ...] = get_args(PriceStatus)
CONDITIONS: tuple[str, ...] = get_args(Condition)
SHIPPING_STATUSES: tuple[str, ...] = get_args(ShippingStatus)
CENT = Decimal("0.01")


def is_web_url(value: object) -> bool:
    """http(s) with a host: marketplace data is untrusted and ends up in links (no javascript:, data:, ...)."""
    if not isinstance(value, str):
        return False
    parts = urlsplit(value.strip())
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc)


@dataclass(frozen=True)
class ListingCandidate:
    """A listing just translated into the canonical form, not yet reconciled with known Listings.

    Construction enforces the minimum a Listing needs; adapters turn a ValueError into a Rejected Listing.
    Optional fields are None when missing (ADR-0005).
    """

    external_id: str
    title: str
    url: str
    price_status: PriceStatus
    raw_payload: dict[str, Any]
    price_amount: Decimal | None = None
    currency: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    location: dict[str, Any] | None = None
    seller_external_id: str | None = None
    seller_name: str | None = None
    condition: Condition | None = None
    condition_raw: str | None = None
    published_at: datetime | None = None
    shipping_status: ShippingStatus = "unknown"
    shipping_amount: Decimal | None = None
    fees_amount: Decimal | None = None  # mandatory fees the buyer pays (e.g. buyer protection), same currency

    def __post_init__(self) -> None:
        for name in ("external_id", "title", "url"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not is_web_url(self.url):
            raise ValueError("url must be an http(s) URL")
        if not all(is_web_url(image) for image in self.images):
            raise ValueError("image URLs must be http(s) URLs")
        if self.price_status not in PRICE_STATUSES:
            raise ValueError(f"unknown price status {self.price_status!r}")
        if (self.price_status == "priced") != (self.price_amount is not None):
            raise ValueError("an amount is required exactly when the price status is 'priced'")
        if self.price_amount is not None:
            if not isinstance(self.price_amount, Decimal) or not self.price_amount.is_finite():
                raise ValueError("price amount must be a finite Decimal")
            if self.price_amount < 0 or self.price_amount != self.price_amount.quantize(CENT):
                raise ValueError("price amount must be non-negative with at most two decimals")
            if not self.currency or len(self.currency) != 3:
                raise ValueError("a three-letter currency is required with a price amount")
        if self.shipping_status not in SHIPPING_STATUSES:
            raise ValueError(f"unknown shipping status {self.shipping_status!r}")
        if (self.shipping_status == "known") != (self.shipping_amount is not None):
            raise ValueError("a shipping amount is required exactly when shipping is 'known'")
        for name in ("shipping_amount", "fees_amount"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0 or value != value.quantize(CENT)):
                raise ValueError(f"{name} must be a non-negative Decimal with at most two decimals")
        if self.condition is not None and self.condition not in CONDITIONS:
            raise ValueError(f"unknown condition {self.condition!r}")
        if self.published_at is not None and self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
