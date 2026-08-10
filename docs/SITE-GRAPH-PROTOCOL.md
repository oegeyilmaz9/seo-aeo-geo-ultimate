# Site Graph protocol

`site-graph.json` is a bounded, evidence-backed representation of site architecture. It supports navigation, internal-link, orphan-page, depth, template, and crawl-path analysis without pretending that a partial crawl is complete.

## Required context

The artifact declares allowed domains, seed URLs, crawl limits, capture time, one evidence mode (`raw` or `rendered`), nodes, edges, and completeness limitations. Every node and edge points to a SHA-256-pinned capture. Each node also points to a hash-pinned metadata envelope that binds its URL, target type, locale, HTTP status, index intent, canonical, title, capture time, and body capture. Each edge has its own hash-pinned metadata envelope binding source, destination, raw href, parsed location, accessible name, follow state, discovery mode, classification, capture time, and source capture. To compare raw and rendered discovery, produce two separately validated graphs; a single capture can never stand in for both evidence modes.

The validator checks unique IDs, declared-domain scope, node and edge metadata integrity, resolvable edge endpoints, capture hashes, chronology, actual parsed anchor relationships, `rel=nofollow`, link location/classification, accessible link names, discovery mode, and completeness claims against the stated URL limit.

## Validate

```powershell
python scripts/validate_site_graph.py validate-graph site-graph.json --bundle <artifact-directory>
```

Generate the graph through `seo-architecture`, then hand material findings to `seo-action-plan` with the affected templates, owners, verification method, and rollback path.
