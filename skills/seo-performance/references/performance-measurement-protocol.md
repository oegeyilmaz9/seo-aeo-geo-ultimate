# SEO performance measurement protocol

## Source contract

Record the platform/export name, exact property, search type, filters, export method, UTC-bounded window, reporting timezone, requested dimensions, collection time, and normalized source-envelope hash. The envelope is JSON schema version `1.0.0` and repeats the run's source type, property, search type, filters, export method, window, dimensions, rows, indexation observations, and Web Vitals exactly; retain the original provider export alongside it when permitted. When a formal Query Corpus defines the query cohort, bind it by ID, reference, and SHA-256 hash; every exposed query row must resolve to an `observed_search_query` in that corpus. Authorized first-party exports are preferred. A third-party estimate belongs in research evidence, not a first-party performance run.

Google Search Console can omit anonymized queries, truncate exports, and aggregate page data to canonical URLs. Bing and analytics products have their own definitions and limits. Preserve the source's definition; do not silently make cross-platform rows equivalent.

## Metric families

- Search demand and result interaction: impressions, clicks, CTR, and average position.
- Discovery/index state: reported indexed, excluded, not-indexed, or unknown URLs.
- Field experience: LCP, INP, and CLS from a named field/RUM source and form factor.
- Site outcomes: organic sessions, conversions, and revenue from a named analytics method.

Do not average or weight these into a universal SEO score. Report a metric only when its denominator, scope, and source are known.

## Query and page privacy

Retain only the query text the authorized export exposes and the project is permitted to store. Never infer anonymized queries. Record whether query rows are excluded or unknown. Preserve canonical aggregation and property scope so query-to-page mappings are not overstated.

## Comparisons

Compare the same property, source, search type, filters, export method, dimensions, metric definition, and window duration. Every drift row binds explicit prior/current record IDs. Search-row sums, impression-weighted CTR/average position, indexed-URL counts, and mean Web Vital values are recomputed from those records; free-written drift values are invalid. Selected prior/current cohorts must have the same declared dimension projection, with dates aligned by offset inside equal-duration windows; URL and Web Vital keys must match exactly. A null-derived value is never comparable. Treat changes in sampling, anonymization, aggregation, tracking, consent, locale, device, seasonality, demand, or site scope as comparability risks. A delta is descriptive; it does not attribute causation.

## Handoff

A valid performance run can establish baseline or comparison evidence. It does not approve implementation. Send a confirmed issue to its specialist, create an evidence-linked `seo-findings.json`, and use `seo-action-plan` before a production change.
