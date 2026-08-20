# Provider operations protocol

Use this protocol only for an explicitly authorized operation against the exact verified property. Provider access and implementation authorization do not imply mutation authorization.

## Capability check

Discover the current official API, CLI, MCP connector, or provider UI before acting. Record the documented capability, authentication boundary, property identity, supported target type, and limitations. Prefer a credential-scoped API or CLI when it supports the exact operation. If a browser is required, use an isolated product browser unless the user explicitly names another session; never silently take over an unrelated active browser.

Current Google boundaries matter: the Search Console API can submit a sitemap; the URL Inspection API reports inspection state and is not a general indexing-mutation endpoint; individual recrawl requests and validation flows can require the Search Console UI; the Google Indexing API is limited to eligible `JobPosting` and livestream `BroadcastEvent` pages. Bing supports sitemap and URL submission and recommends IndexNow for eligible changed-URL notification. Re-verify these facts against the dated source registry immediately before use.

## Mutation gate and receipt

Immediately before the operation:

1. verify the signed-in account or credential and exact property;
2. capture pre-state;
3. restate the authorized action, targets, limit, and rollback or stop condition;
4. execute only the authorized target set;
5. record the provider response, receipt identifier, time, status, partial failures, and post-state;
6. write and validate a separate `provider-operation-receipt.json`.

Run `python "<suite-root>/scripts/validate_provider_operation.py" validate-receipt <bundle>/provider-operation-receipt.json --bundle <bundle>`. Keep this receipt separate from `seo-performance-run.json`: one proves an operation was attempted/accepted, while the other measures later provider-reported observations.

## Outcome boundary

`accepted` or a successful HTTP response means only that the provider received or accepted the operation. Discovery, crawl, indexing, serving, citation, referral, traffic, and conversion remain separate `pending`, `observed`, `not-observed`, `not-applicable`, or `unknown` states with their own evidence and follow-up time. Old dashboard counts can coexist with a newer accepted operation because of provider processing and reporting lag; report that lag instead of overwriting either observation.
