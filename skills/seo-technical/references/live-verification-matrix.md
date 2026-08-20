# Live verification matrix

Match verification scope to the implementation's change universe and record each layer independently.

| Change type | Minimum universe | Required layers |
|---|---|---|
| One page or asset | Named target plus declared dependents | Raw response; rendered UI when client rendering matters; hosting/CDN response |
| Shared template, renderer, or resolver | Entire affected route class or a justified closed population | Raw response, hydrated UI, hosting/CDN, build/runtime errors |
| Canonical, redirect, sitemap, hreflang, or indexability contract | Full declared URL corpus, including redirect sources and exceptions | Raw HTTP/HTML, sitemap equality, live alias/deployment identity, provider observation when authorized |

For an indexable HTML document verify its expected status, robots/indexability state, canonical, title, description, H1, and declared hreflang relationships. For a redirect verify status, `Location`, sitemap exclusion, and the target's expected document state. Do not require document-only title, canonical, robots-meta, description, or H1 fields from a bodyless redirect unless a provider contract explicitly requires them.

A live-delivery receipt records the candidate/build identity, deployment ID, production alias, expected and live sitemap set/hash, expected/passed/failed counts, failed targets, transient retries, and build/runtime errors. A recovered transient request remains visible but is not a permanent defect. A release passes only when the final report exits successfully and every required layer in scope passes.

Use `python "<suite-root>/scripts/verify_live_release.py" verify --plan <release-plan.json> --output <live-release-report.json>` for the portable raw-response/sitemap layer. The tool does not render JavaScript or mutate a provider; add a separate isolated-browser capture when hydrated state is in scope.
