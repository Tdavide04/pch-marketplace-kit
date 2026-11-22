# pch-marketplace-kit

The contract between [Personal Collection Hub](https://github.com/Tdavide04/personal-collection-hub) (PCH) and its Marketplace adapters ([subito-scanner](https://github.com/Tdavide04/subito-scanner), [vinted-scanner](https://github.com/Tdavide04/vinted-scanner), [ebay-scanner](https://github.com/Tdavide04/ebay-scanner)).

It holds what both sides must agree on, and nothing that remembers anything:

| Module | Contents |
| --- | --- |
| `pch_marketplace_kit.domain` | `ListingCandidate`, the canonical form of a listing, and its types (`PriceStatus`, `Condition`, `ShippingStatus`) |
| `pch_marketplace_kit.adapter` | The `MarketplaceAdapter` port, `Page`, `Rejected`, `InvalidParams`, `TransientMarketplaceError`, `PermanentMarketplaceError`, `CAPABILITIES` |
| `pch_marketplace_kit.http` | `MarketplaceHttp`: rate limit, timeouts, retries with backoff and jitter, `Retry-After` |
| `pch_marketplace_kit.registry` | Adapter discovery through the `pch.marketplaces` entry point group |
| `pch_marketplace_kit.testing` | Fake HTTP session and clock, contract checks for adapter test suites |

## Writing an adapter

An adapter translates only: no persistence, deduplication or notifications, no state beyond its HTTP session.

1. Depend on the kit with a major-version bound, from git:

   ```toml
   [project]
   dependencies = ["pch-marketplace-kit>=0.1,<0.2"]

   [tool.uv.sources]
   pch-marketplace-kit = { git = "https://github.com/Tdavide04/pch-marketplace-kit", tag = "v0.1.0" }
   ```

2. Implement `marketplace`, `capabilities`, `validate_params(raw)` and `fetch_page(params, cursor)`. Raise only `InvalidParams` from validation and only the two Marketplace errors from fetching.
3. Register a factory that receives the settings for your Marketplace (environment variables `PCH_<MARKETPLACE>_*`, prefix removed, keys lower-cased):

   ```toml
   [project.entry-points."pch.marketplaces"]
   subito = "subito_scanner:create_adapter"
   ```

4. In tests, use `FakeSession`/`FakeTime` and run `assert_adapter_shape` and `assert_valid_page` on pages built from real, anonymised responses.

## Versioning

Semantic versioning on git tags (`vX.Y.Z`). Before 1.0 a minor release may break the contract; adapters pin `<next minor` until then.

## Development

```sh
uv sync
uv run pytest
```

Licensed under MIT.
