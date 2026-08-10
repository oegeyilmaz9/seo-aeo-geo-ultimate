# SEO Performance protocol

`seo-performance-run.json` measures conventional search outcomes without mixing them with AI-answer observations. It links an analysis window to hash-pinned raw exports and, when used, a formal Query Corpus.

## What a run records

- property, search type, dates, filters, dimensions, timezone, and data source;
- a hash-pinned normalized source envelope whose rows/indexation/Web Vitals exactly match the run, with the original provider export retained when permitted;
- clicks, impressions, CTR, and optional average position with arithmetic checks;
- query privacy, anonymization, sampling, and aggregation limitations;
- baseline or comparison linkage, explicit prior/current record IDs, matching cohort dimensions, validator-derived metric values, and whether the two windows are genuinely comparable;
- observations and hypotheses without causal or guaranteed-outcome language.

The validator rejects negative metrics, inconsistent CTR, missing raw-export hashes, free-written drift values that do not derive from their declared records, invalid comparison links, and causal claims that the measurement cannot establish.

## Validate

```powershell
python scripts/validate_seo_performance.py validate-run seo-performance-run.json --bundle <artifact-directory>
```

Use `seo-performance` for Search Console-style clicks, impressions, CTR, and query/page analysis. Use `ai-visibility-monitor` for repeated AI-surface answers, mentions, sources, citations, referrals, and answer drift.
