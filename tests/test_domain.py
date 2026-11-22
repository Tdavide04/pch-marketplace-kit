from decimal import Decimal

import pytest

from pch_marketplace_kit.domain import ListingCandidate


def candidate(**overrides):
    return ListingCandidate(**{"external_id": "1", "title": "t", "url": "https://x.test/1", "price_status": "free", "raw_payload": {}, **overrides})


@pytest.mark.parametrize("url", ["javascript:alert(1)", "JAVASCRIPT:alert(1)", "data:text/html,<script>", "ftp://x.test/1", "//x.test/1", "x.test/1"])
def test_listing_url_must_be_http_or_https(url):
    with pytest.raises(ValueError, match="http"):
        candidate(url=url)


@pytest.mark.parametrize("images", [["javascript:alert(1)"], ["https://x.test/a.jpg", "data:image/png;base64,AAAA"]])
def test_image_urls_must_be_http_or_https(images):
    with pytest.raises(ValueError, match="http"):
        candidate(images=images)


def test_http_and_https_urls_are_accepted():
    assert candidate(url="http://x.test/1", images=["https://x.test/a.jpg"]).url == "http://x.test/1"


@pytest.mark.parametrize(
    ("fields", "ok"),
    [
        ({}, True),  # unknown shipping by default
        ({"shipping_status": "known", "shipping_amount": Decimal("4.90")}, True),
        ({"shipping_status": "known"}, False),  # known needs an amount
        ({"shipping_status": "unknown", "shipping_amount": Decimal("4.90")}, False),
        ({"shipping_status": "pickup_only", "shipping_amount": Decimal("1")}, False),
        ({"shipping_status": "teleport"}, False),
        ({"fees_amount": Decimal("-1")}, False),
        ({"fees_amount": Decimal("2.30")}, True),
    ],
)
def test_shipping_and_fees_invariants(fields, ok):
    if ok:
        candidate(**fields)
    else:
        with pytest.raises(ValueError):
            candidate(**fields)
