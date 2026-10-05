# Markdown workflow: runnable start to verified delivery

Conventional HTML SEO, XML sitemaps, robots policy, structured data, internal links, performance and keyword research continue. The public Markdown representation uses the same approved content revision. Private work notes record what was researched, decided, changed and verified. Start with [the full contract](MARKDOWN-DISCOVERY.md) and [the Turkish guide](REHBER-TR.md).

## 1. Create the private work index

Run from the source checkout, or substitute absolute script paths from the installed skill's `.seo-suite-runtime.json` `suite_root`:

```powershell
python scripts/manage_markdown_work.py --root work/seo-project init --title "Site SEO and Markdown delivery"
```

Write a real work note using [the work-note template](WORK-NOTE-TEMPLATE.md). Each material step gets its own substantive document, or a clearly linked section when several small changes are one step. Register after writing:

```powershell
python scripts/manage_markdown_work.py --root work/seo-project add --id inventory --path inventory.md --title "Eligible content inventory" --status completed --owner "Content owner" --outcome "Every discovered URL has a recorded disposition and source"
```

`completed` describes this step only; it does not imply release, search indexing or AI use. Keep notes, analytics, private URL dispositions and raw evidence outside the public output root. After all steps resolve, run `check --final`; broken destinations, stale hashes and unresolved states fail.

## 2. Review the complete URL inventory and content source

Reconcile CMS/build routes, XML, internal discovery and locales. Record each URL as publish/exclude with evidence. Unknown eligibility or missing source is a gap. Extract HTML-only bodies from the actual source/rendered capture, review facts, media, visibility and revision parity, then save the approved substantive `.md` bodies. A converter's output is not approval.

[inventory.json](../examples/markdown-discovery/inventory.json) explains the executable input shape through a **fictional fixture**. It includes two public pages and one privately recorded excluded page. Inventory fields declare origin, complete/partial scope, source evidence, owner, refresh trigger and canonical/noindex policy. Native images/PDFs/videos need an exact reviewed `public_assets` entry. Do not use sample facts as your business data.

## 3. Build and check an offline demonstration

Use a new output directory. Build refuses an existing one, and keeps its inventory/source manifest outside the public tree:

```powershell
python scripts/manage_markdown_site.py build --inventory examples/markdown-discovery/inventory.json --output build/markdown-demo --manifest work/markdown-demo-manifest.json
python scripts/manage_markdown_site.py validate --manifest work/markdown-demo-manifest.json --root build/markdown-demo
python scripts/validate_llms_txt.py validate-file build/markdown-demo/llms.txt
```

The output is `llms.txt`, `sitemap.md`, a topic map and two substantive page documents. Validation checks the entire declared population, exact source projection, metadata, destinations, anchors and hashes. Actual full-site inventory completeness, editorial truth and live HTML parity need the separate source-owner review.

To refresh a site, create a new reviewed candidate from its updated inventory, compare it to the accepted manifest, propagate changed/deleted URLs to all topic/locale maps, run the same checks and replace the published candidate through the site's normal release pipeline. Do not overwrite source evidence or retain deleted facts in stale maps.

## 4. Connect native entry points

```powershell
python scripts/manage_markdown_site.py hints --manifest work/markdown-demo-manifest.json --root build/markdown-demo --output work/native-discovery.md
```

This creates a private `.md` note with exact robots `#` and XML-comment snippets. It leaves the real native sources intact. In an authorized site implementation, patch the existing robots and sitemap generators with those short hints. Preserve robots active records and XML elements/attributes/meaningful text; validate the original sitemap schema and inspect delivered raw comment bytes. Never put `sitemap.md` or `llms.txt` in a native `Sitemap:` record or add invented prompt tags.

The fixture origin is `example.com`: these commands prove local behavior, not public delivery there. For a real site, both hinted destinations must resolve before publishing the native patch. A parser may ignore comments; a generator/CDN may strip them. Do not change rules or widen access just to make navigation succeed.

## 5. Research and own keyword answers

Follow [keyword-research-protocol.md](../skills/seo-research/references/keyword-research-protocol.md). Gather actual query sources, market/language/device scope, demand provenance and dated SERPs; decide task-compatible clusters and one canonical page owner. Retain near-term and high-volume leadership tracks. Render an already validated Query Corpus against the actual Markdown inventory:

```powershell
python scripts/render_keyword_map.py --corpus examples/ai-search-handoff/query-corpus.json --bundle examples/ai-search-handoff --manifest work/markdown-demo-manifest.json --public-root build/markdown-demo --output work/keyword-map.md
```

These independent fixtures may have different owners, so absent owners are correctly labelled planned/unresolved. The helper does not invent keywords, demand, intent decisions or fetchable destinations. Complete [keyword-decisions.md](KEYWORD-DECISION-TEMPLATE.md) with query IDs, SERP evidence, primary/supporting intent, exact answer section, action/no-action, cannibalization, owners, priority and refresh trigger.

## 6. Publish and verify a real accepted candidate

Release through the site's authorized deployment workflow. Apply the chosen HTTP canonical/noindex policy for mirrors. Using the real accepted manifest and output directory, run:

```powershell
python scripts/manage_markdown_site.py live --manifest work/accepted-site-manifest.json --root build/accepted-site --report work/live-verification.md
```

This reads every generated public resource, validates UTF-8/MIME, exact body hash and declared mirror header policy, and stops on rate/access/provider failures without a retry loop. Do not run this against demonstration fixtures expecting success. Verify native robots/sitemap policy and raw hint retention separately. Keep deployment, provider acceptance, indexing, retrieval, citation and outcomes as separate observations.

## 7. Verify this repository's own discovery

The project itself exposes [llms.txt](../llms.txt) → [sitemap.md](../sitemap.md) → [topic maps](maps/protocols.md) → existing documents/native sources. Maps enumerate all published source roots, not a selected sample:

```powershell
python scripts/manage_repository_map.py --write
python scripts/manage_repository_map.py --check
python scripts/sync_contracts.py --check
python scripts/validate_suite.py
python scripts/validate_claude_plugin.py
python scripts/run_tests.py
```

CI repeats generation, schema, freshness and behavior gates. Repository navigation is not a robots policy for `github.com`: site-owned native directives are applied only during an actual authorized site job.
