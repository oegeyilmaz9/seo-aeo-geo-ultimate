# SEO Findings Protocol

`seo-findings.json` is the formal evidence handoff for conventional SEO work. It carries a bounded set of technical, content, structured-data, international, sitemap, media, programmatic, comparison, accessibility, measurement, or policy findings into `$seo-action-plan` without treating a recommendation as an approved change.

## When to use it

Use this artifact only when a conventional specialist has a captured, reviewable observation and a cross-team or production decision needs a formal action plan. Use `optimization-brief.json` instead for AEO/GEO work and `research-pack.json` for multi-engine AI-search research provenance.

If the source capture, page access, factual source, or owner scope is missing, keep the output provisional. Do not create a formal finding merely to make a handoff look complete.

## Bundle shape

```text
seo-findings-bundle/
  seo-findings.json
  raw/
    rendered-page.html
    response-headers.txt
    source-note.md
```

Each evidence record points to a file below `raw/`. The validator rejects path traversal, symlinks/reparse points, missing raw evidence, unresolved IDs, stale chronology within the bundle, inflated classifications, and finding sets that lack a target-tied direct observation.

## Required logic

- Name the specialist that produced the set and state the decision objective.
- Give every target a stable ID, target type, locale, and HTTPS source URL when one exists.
- Link every finding to one or more evidence records and give it a bounded category, severity, candidate owner, desired outcome, verification method, and limitations.
- Keep the finding classification no stronger than its weakest linked evidence record.
- Treat policy findings as critical and route them through an appropriate high-risk action-plan item.
- Include declined claims and limitations. An empty finding set is valid only when it records why no finding was asserted.

## Validation and handoff

From a suite checkout:

```powershell
python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>
```

Put the immutable bundle under an action-plan bundle's `inputs/` folder. An `action-plan.json` that uses `input_findings` must use schema version `1.1.0`; the action-plan validator reruns the SEO Findings validator and verifies artifact hashes before allowing the handoff.

Passing validation proves artifact integrity and evidence traceability. It does not approve a change or guarantee crawl, indexing, ranking, retrieval, citation, traffic, revenue, or conversion outcomes.
