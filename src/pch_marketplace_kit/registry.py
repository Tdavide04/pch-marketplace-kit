"""Adapter discovery through Python entry points.

An adapter package declares a factory in the `pch.marketplaces` group, for example in its pyproject:

    [project.entry-points."pch.marketplaces"]
    subito = "subito_scanner:create_adapter"

The factory receives the settings meant for that Marketplace (the hub passes the environment variables
named `PCH_<MARKETPLACE>_*`, prefix removed, keys lower-cased) and returns a MarketplaceAdapter.
Factories open no connection: an adapter does network work only when it is used.
"""
from collections.abc import Callable, Mapping
from importlib.metadata import EntryPoint, entry_points

from pch_marketplace_kit.adapter import MarketplaceAdapter

ENTRY_POINT_GROUP = "pch.marketplaces"

AdapterFactory = Callable[[Mapping[str, str]], MarketplaceAdapter]


class AdapterLoadError(RuntimeError):
    """An installed adapter package could not be loaded or does not honour the contract."""


def settings_for(marketplace: str, environ: Mapping[str, str]) -> dict[str, str]:
    """`PCH_EBAY_CLIENT_ID=x` becomes `{"client_id": "x"}` for the Marketplace `ebay`."""
    prefix = f"PCH_{marketplace.upper()}_"
    return {key[len(prefix):].lower(): value for key, value in environ.items() if key.startswith(prefix)}


def discover_adapters(environ: Mapping[str, str], entries: list[EntryPoint] | None = None) -> dict[str, MarketplaceAdapter]:
    """Build every installed adapter, keyed by its Marketplace name (the entry point name)."""
    found = entries if entries is not None else list(entry_points(group=ENTRY_POINT_GROUP))
    adapters: dict[str, MarketplaceAdapter] = {}
    for entry in sorted(found, key=lambda e: e.name):
        if entry.name in adapters:
            raise AdapterLoadError(f"two installed packages provide the Marketplace {entry.name!r}")
        try:
            factory = entry.load()
            adapter = factory(settings_for(entry.name, environ))
        except Exception as exc:  # a broken package must name itself, not crash with a bare traceback
            raise AdapterLoadError(f"adapter {entry.name!r} ({entry.value}) failed to load: {exc}") from exc
        if getattr(adapter, "marketplace", None) != entry.name:
            raise AdapterLoadError(f"adapter {entry.name!r} reports marketplace {getattr(adapter, 'marketplace', None)!r}")
        adapters[entry.name] = adapter
    return adapters
