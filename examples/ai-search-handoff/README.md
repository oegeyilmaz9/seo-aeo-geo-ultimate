# AEO, GEO, and AI-visibility handoff example

This sanitized bundle demonstrates one evidence chain without promising an outcome:

1. `research-pack.json` pins the source, observation, fact, locale, engine, and surface.
2. `query-corpus.json` freezes the exact prompt and collection context.
3. `optimization-brief-aeo.json` audits direct-answer completeness.
4. `optimization-brief-geo.json` audits evidence traceability.
5. `visibility-run.json` records a Visibility Run `2.0.0` observation, retrieval context, consulted source, and citation-claim review.

From the repository root, validate every handoff:

```bash
python scripts/validate_ai_search_research.py validate-pack examples/ai-search-handoff/research-pack.json --bundle examples/ai-search-handoff --now 2026-08-10T00:00:00Z
python scripts/validate_query_corpus.py validate-corpus examples/ai-search-handoff/query-corpus.json --bundle examples/ai-search-handoff
python scripts/validate_seo_aeo.py validate-brief examples/ai-search-handoff/optimization-brief-aeo.json --bundle examples/ai-search-handoff
python scripts/validate_seo_geo.py validate-brief examples/ai-search-handoff/optimization-brief-geo.json --bundle examples/ai-search-handoff
python scripts/validate_ai_visibility_monitor.py validate-run examples/ai-search-handoff/visibility-run.json --bundle examples/ai-search-handoff
```

Render a bounded, human-readable report after validation:

```bash
python scripts/render_artifact_report.py examples/ai-search-handoff/research-pack.json --bundle examples/ai-search-handoff --as-of 2026-08-10T00:00:00Z --out examples/ai-search-handoff/reports/research-pack.md
python scripts/render_artifact_report.py examples/ai-search-handoff/optimization-brief-aeo.json --bundle examples/ai-search-handoff --out examples/ai-search-handoff/reports/aeo-brief.md
python scripts/render_artifact_report.py examples/ai-search-handoff/optimization-brief-geo.json --bundle examples/ai-search-handoff --out examples/ai-search-handoff/reports/geo-brief.md
python scripts/render_artifact_report.py examples/ai-search-handoff/visibility-run.json --bundle examples/ai-search-handoff --out examples/ai-search-handoff/reports/visibility-run.md
```

All URLs use `example.com`; the data contains no credentials, accounts, customer payloads, or personal information. The bundle proves artifact integrity and declared observations only. It does not guarantee retrieval, citation, ranking, traffic, revenue, or conversion.
