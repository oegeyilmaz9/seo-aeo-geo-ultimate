# Conventional SEO handoff example

This sanitized bundle shows two independent, validated handoffs:

- `seo-findings.json` carries one capture-bound technical observation to planning.
- `seo-performance-run.json` records a first-party observational baseline without claiming causation.

From the repository root, validate both artifacts:

```bash
python scripts/validate_seo_findings.py validate-findings examples/conventional-seo-handoff/seo-findings.json --bundle examples/conventional-seo-handoff
python scripts/validate_seo_performance.py validate-run examples/conventional-seo-handoff/seo-performance-run.json --bundle examples/conventional-seo-handoff
```

Render human-readable reports only after validation:

```bash
python scripts/render_artifact_report.py examples/conventional-seo-handoff/seo-findings.json --bundle examples/conventional-seo-handoff --out examples/conventional-seo-handoff/reports/seo-findings.md
python scripts/render_artifact_report.py examples/conventional-seo-handoff/seo-performance-run.json --bundle examples/conventional-seo-handoff --out examples/conventional-seo-handoff/reports/seo-performance-run.md
```

The files use `example.com`, contain no credentials or customer data, and do not claim ranking, indexing, traffic, revenue, or conversion uplift.
