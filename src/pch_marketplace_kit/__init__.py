"""Contract between Personal Collection Hub and its Marketplace adapters."""
from pch_marketplace_kit.adapter import (
    CAPABILITIES,
    InvalidParams,
    MarketplaceAdapter,
    Page,
    PermanentMarketplaceError,
    Rejected,
    TransientMarketplaceError,
)
from pch_marketplace_kit.domain import (
    CONDITIONS,
    PRICE_STATUSES,
    SHIPPING_STATUSES,
    Condition,
    ListingCandidate,
    PriceStatus,
    ShippingStatus,
    is_web_url,
)
from pch_marketplace_kit.http import HttpPolicy, MarketplaceHttp
from pch_marketplace_kit.registry import ENTRY_POINT_GROUP, AdapterFactory, AdapterLoadError, discover_adapters, settings_for

__version__ = "0.1.0"

__all__ = [
    "CAPABILITIES", "CONDITIONS", "ENTRY_POINT_GROUP", "PRICE_STATUSES", "SHIPPING_STATUSES",
    "AdapterFactory", "AdapterLoadError", "Condition", "HttpPolicy", "InvalidParams", "ListingCandidate", "MarketplaceAdapter",
    "MarketplaceHttp", "Page", "PermanentMarketplaceError", "PriceStatus", "Rejected", "ShippingStatus", "TransientMarketplaceError",
    "discover_adapters", "is_web_url", "settings_for",
]
