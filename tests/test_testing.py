"""The contract checks catch the mistakes they exist for."""
import pytest

from pch_marketplace_kit import ListingCandidate, Page, Rejected
from pch_marketplace_kit.testing import FakeSession, FakeTime, assert_adapter_shape, assert_valid_page, response


def candidate(external_id="1", **overrides):
    return ListingCandidate(**{"external_id": external_id, "title": "t", "url": "https://x.test/1", "price_status": "free", "raw_payload": {"id": external_id}, **overrides})


class Shape:
    marketplace = "fake"
    capabilities = frozenset({"images"})

    def validate_params(self, raw):
        return raw

    def fetch_page(self, params, cursor):
        return Page(candidates=[])


def test_a_well_formed_adapter_passes():
    assert_adapter_shape(Shape())


def test_unknown_capabilities_are_refused():
    adapter = Shape()
    adapter.capabilities = frozenset({"images", "telepathy"})
    with pytest.raises(AssertionError, match="telepathy"):
        assert_adapter_shape(adapter)


def test_a_valid_page_passes():
    assert_valid_page(Page(candidates=[candidate("1"), candidate("2")], rejected=[Rejected("3", "no title")]), frozenset())


def test_repeated_ids_are_refused():
    with pytest.raises(AssertionError, match="repeat"):
        assert_valid_page(Page(candidates=[candidate("1"), candidate("1")]))


def test_a_field_outside_the_capabilities_is_refused():
    page = Page(candidates=[candidate("1", images=["https://x.test/a.jpg"])])
    assert_valid_page(page, frozenset({"images"}))
    with pytest.raises(AssertionError, match="images"):
        assert_valid_page(page, frozenset())


def test_fake_session_plays_back_and_records():
    time = FakeTime()
    session = FakeSession(time, [response(200, {"ok": True})])
    assert session.request("GET", "https://x.test", params={"q": 1}).json() == {"ok": True}
    assert session.calls[0]["params"] == {"q": 1}
    with pytest.raises(AssertionError, match="unexpected request"):
        session.request("GET", "https://x.test")
