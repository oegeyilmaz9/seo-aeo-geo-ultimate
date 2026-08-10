# SEO Findings Protocol

`seo-findings.json` is the formal evidence handoff for conventional and specialist SEO work. Version `1.1.0` adds commerce, local, video, news/Discover, agentic, architecture, authority, entity, freshness, expanded target types, and their owners while keeping version `1.0.0` readable. It carries bounded evidence into `seo-action-plan` without treating a recommendation as an approved change.

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

Each evidence record points to a file below `raw/`. Version `1.1.0` also requires `raw_evidence_sha256`, so an upstream capture cannot change without invalidating the finding set and every downstream Action Plan that revalidates it. The validator rejects path traversal, symlinks/reparse points, missing or hash-drifted raw evidence, unresolved IDs, stale chronology within the bundle, inflated classifications, and finding sets that lack a target-tied direct observation.

## Required logic

- Name the specialist that produced the set and state the decision objective.
- Give every target a stable ID, target type, locale, and HTTPS source URL when one exists.
- Link every finding to one or more evidence records and give it a bounded category, severity, candidate owner, desired outcome, verification method, and limitations. In `1.1.0`, every evidence record also names its exact scope `target_id`; direct observations must match the target locale and URL. URL-less graph, flow, protocol, and profile targets use a hash-pinned JSON target envelope that binds the target ID/type/locale to a second hash-pinned capture, so they cannot borrow an unrelated file.
- Keep the finding classification no stronger than its weakest linked evidence record.
- Treat policy findings as critical and route them through an appropriate high-risk action-plan item.
- Include declined claims and limitations. An empty finding set is valid only when it records why no finding was asserted.

## Validation and handoff

From a suite checkout:

```powershell
python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>
```

Put the immutable bundle under an action-plan bundle's `inputs/` folder. SEO Findings `1.1.0` requires Action Plan `1.2.0`; legacy Findings `1.0.0` remains compatible with Action Plan `1.1.0`. The action-plan validator reruns the SEO Findings validator and verifies artifact hashes before allowing the handoff.

Passing validation proves the declared artifact and raw-evidence bindings are internally consistent. It does not approve a change or guarantee crawl, indexing, ranking, retrieval, citation, traffic, revenue, or conversion outcomes.
