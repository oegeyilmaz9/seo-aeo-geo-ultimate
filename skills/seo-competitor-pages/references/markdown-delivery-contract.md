# Markdown delivery: seo-competitor-pages

Every material work step has a substantive Markdown document and a direct link in private `index.md`. Include outcome/status, scope, evidence dates/links, facts vs inferences, decisions, limitations, owner and next destination. Drafts remain draft/provisional until their owning semantic validator passes. Use the suite artifact renderer for validated formal bundles; do not replace immutable JSON, CSV, raw captures or schema.

Lane documents: `comparison-research.md; comparison-decisions.md`.

Keep comparison Markdown and HTML claims identical, source-dated, attributable and fair. Map comparison intent to a substantive owner; do not copy competitors or invent relative product capabilities.

## Public knowledge profile

For authorized public-site implementation, require lowercase `/llms.txt`, `/sitemap.md`, topic maps and substantive `.md` equivalents for every eligible canonical page in the declared scope. These are owner-defined delivery requirements, not universal SEO/AEO/GEO platform requirements. robots.txt, XML sitemaps, feeds, schema and protocol files keep their native formats. One-page or answer-only work stays bounded and records its work note without changing the whole site.

Use reviewed content from the same revision as HTML. Preserve facts, citations, dates, units, locale, media meaning and public access policy. Private reports, analytics, credentials, admin URLs, personalized content and paywalled material never become public mirrors. Every excluded/unknown inventory URL has a private disposition; unknown eligibility or a partial inventory prevents a whole-site-complete claim.

Direct destinations must actually resolve; planned URLs are labelled planned. Verify links, map coverage, source hashes, public output hashes, editorial parity, UTF-8 MIME delivery, cache/deletion refresh, maintenance owner and the chosen canonical/indexing policy. Public Markdown is a content representation, not a crawler permission, schema replacement or evidence that an engine retrieves/cites it.

Native entry points also carry concise navigation hints: robots `#` comments, XML sitemap/index comments, and two reader-facing sentences in llms.txt direct an interested LLM to the actual Markdown map and answer. Preserve all existing crawl rules and native sitemap elements; comments are discovery hints with no guaranteed consumer. The technical/sitemap owners verify protocol invariance, real destinations and delivered comment retention. Read the full contract's “Native entry-point navigation hints” section before editing those sources.

## Shared tools and full contract

Resolve `<suite-root>` from `.seo-suite-runtime.json` beside SKILL.md in Codex, `${CLAUDE_PLUGIN_ROOT}` in Claude Code, or the absolute suite checkout. Read `<suite-root>/docs/MARKDOWN-DISCOVERY.md` before corpus generation/publication. It owns the detailed inventory, routing, native-format exceptions, privacy, acceptance and source-review rules; do not improvise a conflicting contract.

- Public export: `python "<suite-root>/scripts/manage_markdown_site.py" build --inventory <private/inventory.json> --output <new-public-candidate>`.
- Local projection: `python "<suite-root>/scripts/manage_markdown_site.py" validate --manifest <private-manifest.json> --root <public-candidate>`.
- Full live delivery after authorized publication: same tool, `live --manifest ... --root ... --report <private/live-verification.md>`. A failed/rate-limited run is incomplete, never retried in a loop.
- Work index: `python "<suite-root>/scripts/manage_markdown_work.py" --root <private-work> init --title "Work title"`; use `add --id <step-id> --path <step.md> --title "Step title" --status <draft|provisional|completed|blocked|not-applicable> --owner "Owner" --outcome "Actual result"`, then `check --final` before complete closeout. Equivalent maintained tooling is acceptable when these invariants are verified.

The deterministic export verifies parity with supplied reviewed Markdown, not editorial truth or live HTML. Formal AEO/GEO claims still require the pinned Research Pack. Owner-required source navigation/parity work can proceed locally without inventing engine observations. Preserve separate local acceptance, live delivery and provider outcome states.
