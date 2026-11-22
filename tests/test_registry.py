"""Adapter discovery through entry points, with fake entry points (no installed adapter needed)."""
from importlib.metadata import EntryPoint

import pytest

from pch_marketplace_kit import AdapterLoadError, Page, discover_adapters, settings_for


class Adapter:
    capabilities = frozenset()

    def __init__(self, marketplace: str, settings: dict):
        self.marketplace = marketplace
        self.settings = settings

    def validate_params(self, raw):
        return raw

    def fetch_page(self, params, cursor):
        return Page(candidates=[])


def make_fake(settings):
    return Adapter("fake", settings)


def make_liar(settings):
    return Adapter("someone_else", settings)


def explode(settings):
    raise ValueError("missing client_id")


def entry(name: str, func: str) -> EntryPoint:
    return EntryPoint(name=name, value=f"{__name__}:{func}", group="pch.marketplaces")


def test_settings_keep_only_the_marketplace_prefix():
    env = {"PCH_EBAY_CLIENT_ID": "id", "PCH_EBAY_CLIENT_SECRET": "s", "PCH_VINTED_X": "no", "EBAY_CLIENT_ID": "no"}
    assert settings_for("ebay", env) == {"client_id": "id", "client_secret": "s"}


def test_adapters_are_built_with_their_settings_and_keyed_by_name():
    adapters = discover_adapters({"PCH_FAKE_TOKEN": "t"}, [entry("fake", "make_fake")])
    assert list(adapters) == ["fake"]
    assert adapters["fake"].settings == {"token": "t"}


def test_an_adapter_reporting_another_marketplace_is_refused():
    with pytest.raises(AdapterLoadError, match="someone_else"):
        discover_adapters({}, [entry("fake", "make_liar")])


def test_a_failing_factory_names_the_adapter():
    with pytest.raises(AdapterLoadError, match="'fake'.*missing client_id"):
        discover_adapters({}, [entry("fake", "explode")])


def test_two_packages_for_one_marketplace_are_refused():
    with pytest.raises(AdapterLoadError, match="two installed packages"):
        discover_adapters({}, [entry("fake", "make_fake"), entry("fake", "make_fake")])
