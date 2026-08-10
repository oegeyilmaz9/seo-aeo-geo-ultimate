# Validated artifact examples

These bundles use only sanitized `example.com` data and are exercised by the isolated artifact-tooling evaluation suite.

- [`conventional-seo-handoff`](conventional-seo-handoff/README.md) shows capture-bound SEO Findings and a Search Console performance baseline.
- [`ai-search-handoff`](ai-search-handoff/README.md) shows Research Pack, Query Corpus, AEO, GEO, and Visibility Run handoffs.

The committed JSON files are validator-passing examples. Files produced by `scripts/init_artifact.py` are deliberately named `*.draft.json` and must not be treated as validated until their placeholders are replaced and the owning validator passes.

Create deterministic drafts:

```bash
python scripts/init_artifact.py bundle conventional --out work/example-conventional --seed example-project --created-at 2026-08-10T00:00:00Z
python scripts/init_artifact.py bundle ai-search --out work/example-ai-search --seed example-project --created-at 2026-08-10T00:00:00Z
```

Inspect safe migration support:

```bash
python scripts/migrate_artifact.py paths
```

Each example directory documents its exact validation and Markdown-rendering commands.
