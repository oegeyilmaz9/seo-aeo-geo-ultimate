# Provider operations

Provider operations are explicit, authenticated mutations such as submitting a sitemap or a bounded changed-URL set. They are not ordinary performance measurement and they are never implied by local implementation or deployment authorization.

## Required sequence

1. Re-verify the current provider capability in official documentation.
2. Verify the exact signed-in property or credential no more than one hour before mutation.
3. Preserve the authorization evidence, permitted operation type, and exact target IDs.
4. Capture pre-state, perform only the authorized operation, preserve the raw provider response, and capture post-state.
5. Write `provider-operation-receipt.json` and hash-bind every evidence file.
6. Validate it:

```powershell
python scripts/init_artifact.py bundle provider-operation --out work/provider-operation --seed example-operation --created-at 2026-08-20T10:00:00Z
python scripts/validate_provider_operation.py validate-receipt work/provider-operation/provider-operation-receipt.json --bundle work/provider-operation
```

The validator checks chronology, property/target scope, authorization coverage, result partitioning, evidence hashes, current provider capability boundaries, and separate outcome evidence. It performs no provider mutation itself.

## Capability boundaries

- Google Search Console supports sitemap submission through its API. The URL Inspection API is an inspection surface, not a general indexing mutation endpoint.
- Search Console request-indexing and issue-validation flows may require the provider UI; discover the actual current surface before acting.
- Google's Indexing API is limited to eligible `JobPosting` and livestream `BroadcastEvent` pages.
- Bing supports sitemap and URL submission; IndexNow is a separate changed-URL notification protocol.

Re-verify these boundaries at mutation time. A provider can change or retire a capability after this release.

## Result boundary

An `accepted` receipt means the provider accepted the declared operation. Discovery, crawl, indexing, serving, citation, referral, traffic, and conversion remain separate states. Keep them pending until a later, timestamped observation supports `observed` or `not-observed`; provider processing and dashboard reporting can lag.
