# Data Import Adapter Protocol

`scripts/import_seo_exports.py` converts user-supplied exports into deterministic,
credential-free JSON. It uses only the Python standard library, performs no
network request, and never fetches or mutates a provider account.

The adapters cover:

- Google Search Console CSV;
- Bing Webmaster Tools CSV;
- GA4 landing-page CSV scoped to Organic Search;
- crawler CSV;
- Apache/Nginx Common or Combined access logs.

## Shared integrity rules

- The raw input is not changed. Every result records its byte-for-byte SHA-256,
  size, encoding, and portable raw-source reference.
- UTF-8 with an optional BOM and BOM-marked UTF-16 are supported. Other
  encodings are rejected rather than guessed.
- CSV delimiter detection is limited to comma, tab, and semicolon. If more than
  one interpretation is valid, the import fails and requires `--delimiter`.
- Empty, duplicate, missing, or multiply mapped headers fail the import.
  Unknown columns are not metrics: they are listed under `ignored_headers`.
- Integer fields reject grouping separators and decimals. Decimal fields use a
  period. Negative values are rejected.
- Output has no current-clock timestamp. Identical source bytes and options
  produce identical normalized observations and row IDs.
- The inclusive `--window-start` and exclusive `--window-end` are explicit
  timestamps with offsets. A date-only source value is interpreted in the
  declared reporting timezone.
- Output files never overwrite the input. Existing outputs require
  `--overwrite`.

`--raw-source-ref` is an optional, forward-slash relative reference used in
provenance. It defaults to the source filename. Keep the original export at that
reference when assembling an evidence bundle; the recorded hash is authoritative.

## Search-performance adapters

The `gsc-csv`, `bing-csv`, and `ga4-csv` commands write two files:

1. `--output`: the exact version `1.0.0` normalized source-envelope shape
   consumed by `scripts/validate_seo_performance.py`;
2. `<output>.provenance.json`: the raw-export hash, original/header mapping,
   ignored columns, declared scope, transformations, row counts, and the hash of
   the normalized output.

The source envelope contains exactly:

```text
schema_version, source_type, property, search_type, filters, export_method,
window, dimensions, rows, indexation, web_vitals
```

Each row contains every SEO Performance row field. A field is `null` when the
source did not measure it. The adapters never turn clicks into sessions, key
events into conversions, crawler requests into visits, or one provider's metric
into another provider's metric.

To build `seo-performance-run.json`, copy the normalized source fields and rows
without modification, use the normalized JSON as `raw_source_ref`, and set
`raw_source_sha256` to its recorded normalized-output hash. The run must still
declare its own data-quality status and limitations; the CSV adapter cannot know
sampling, privacy thresholds, canonical aggregation, attribution, consent, or
provider row limits unless another artifact establishes them.

### Google Search Console CSV

```powershell
python scripts/import_seo_exports.py gsc-csv exports/gsc.csv `
  --output raw/gsc.normalized.json `
  --property sc-domain:example.com `
  --window-start 2026-08-01T00:00:00Z `
  --window-end 2026-08-08T00:00:00Z `
  --timezone UTC
```

Required headers are `Clicks` and `Impressions`, plus at least one recognized
dimension. Recognized dimensions are `Date`, `Query`/`Queries`/`Top queries`,
`Page`/`Pages`/`Top pages`/`URL`, `Country`, `Device`, and `Search appearance`.
Optional metrics are `CTR` and `Position`/`Average position`.

CTR in the normalized row is always the exact `clicks / impressions` result.
An exported CTR is retained only as a rounding-aware consistency check; a
conflicting value fails. Zero impressions produce `null` CTR. Country values
must already be two-letter ISO codes, and relative page values require an
explicit HTTPS `--origin`.

### Bing Webmaster Tools CSV

```powershell
python scripts/import_seo_exports.py bing-csv exports/bing.csv `
  --output raw/bing.normalized.json `
  --property https://example.com/ `
  --window-start 2026-08-01T00:00:00Z `
  --window-end 2026-08-08T00:00:00Z
```

The same strict search-performance fields apply. `Keyword`/`Keywords` are also
accepted as the `query` dimension. Provider identity remains
`bing-webmaster-tools`; Bing rows are not relabeled as Search Console rows.

### GA4 landing-page CSV

```powershell
python scripts/import_seo_exports.py ga4-csv exports/ga4-landing-pages.csv `
  --output raw/ga4.normalized.json `
  --property properties/123456 `
  --window-start 2026-08-01T00:00:00Z `
  --window-end 2026-08-08T00:00:00Z `
  --origin https://example.com
```

Required headers are `Landing page` (or `Landing page + query string`) and
`Sessions`. If `Session default channel group` is present, only rows whose
value is exactly `Organic Search` are emitted and the skipped count is recorded.
If the channel header is absent, the command fails unless the operator supplies
`--organic-filter-asserted`, explicitly confirming that the export was filtered
upstream.

Optional `Conversions` and `Total revenue` are preserved. `Key events` is not
silently mapped to conversions because the definitions are not universally
equivalent. Relative landing pages require `--origin`. The resulting source type
is `analytics` and search type is `not-applicable`.

All three performance commands accept repeatable `--filter DIMENSION=VALUE` to
record upstream equality filters. These entries describe the supplied export;
the importer does not apply arbitrary provider queries.

## Crawler CSV adapter

```powershell
python scripts/import_seo_exports.py crawler-csv exports/crawl.csv `
  --output raw/crawl.observations.json
```

Required headers are `URL`/`Address` and `Status code`/`HTTP status`. Optional
recognized fields are content type, title, canonical URL, the crawler's exact
indexability/indexability-status labels, crawl depth, inlinks, outlinks, and
redirect URL. Duplicate URLs, invalid HTTP status values, relative URLs, and
ambiguous aliases fail.

The output is a `seo-data-import` observation envelope with:

- `provenance`: raw hash, byte size, encoding, delimiter, headers, row count;
- `records`: stable IDs and only observed crawler values;
- `workflow_compatibility.site_graph`: HTTPS candidate IDs and compatible
  observed fields;
- explicit transformations and limitations.

It deliberately does not emit `site-graph.json`. A valid Site Graph additionally
requires raw HTML captures, metadata envelopes, locale/business-role/target-type
decisions, index intent, and captured anchor evidence. Crawler labels are kept as
labels; they are not promoted to indexation facts or index intent.

## Server access-log adapter

```powershell
python scripts/import_seo_exports.py server-log logs/access.log `
  --output raw/access-log.observations.json `
  --origin https://example.com
```

The input must contain one uniform Apache/Nginx Common Log Format or Combined
Log Format. Mixed formats and any malformed non-empty line fail; split mixed
files before import.

Each request record preserves the timestamp, method, query-redacted path,
protocol, HTTP status, response bytes, query presence, query-redacted referrer,
user agent, optional target URL, and hashes of the exact request target and the
decoded source line. The whole raw file remains bound by its byte-level SHA-256.

Privacy and claim controls are part of the format:

- client addresses are replaced with deterministic SHA-256 values;
- request and referrer query strings are removed while exact values remain
  hash-bound;
- a user-agent string is never labeled a verified crawler;
- requests are not aggregated into sessions, visits, conversions, rankings,
  retrievals, citations, or referrals.

Paths and user-agent strings can still contain personal or sensitive data.
Hashing is pseudonymization rather than anonymization, so retention and access
remain subject to the project's privacy policy.

The output is suitable as direct-observation input for a bounded log review. It
does not emit an SEO Performance source envelope or Site Graph because request
rows do not contain those artifacts' required definitions and captures.

## Failure and review boundary

The command exits nonzero and writes no output when parsing, header mapping,
scope, numeric, URL, timestamp, or ambiguity checks fail. A successful import
proves deterministic normalization and provenance binding only. It does not
prove that the provider export is complete, correctly filtered, legally
retained, comparable to another window, or sufficient to support a claim.
