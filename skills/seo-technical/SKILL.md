---
name: seo-technical
description: Use when investigating crawlability, indexability, canonicalization, rendering, performance, redirects, directives, sitemaps, crawler controls, or an evidence-scoped llms.txt decision from supplied technical evidence; return safe, testable implementation recommendations rather than a generic technical score.
---

# Technical SEO

## Purpose

Diagnose concrete technical behavior from headers, raw and rendered pages, robots files, sitemap inventories, application configuration, field data, logs, and platform documentation. Create scoped implementation recommendations; do not deploy code, alter production directives, or claim an indexing/ranking outcome.

For an optional `llms.txt` request, evaluate it as a maintained publisher guide—not as a crawler directive or a promised visibility control. Require a documented consuming system, a truthful source of content, a defined scope, and an owner who can keep it current before recommending publication.

Read `references/technical-evidence-protocol.md` before a formal technical audit.

## Evidence before recommendations

Collect the affected URLs, expected state, locale/device where relevant, timestamp, HTTP response/headers, raw HTML, rendered output when JavaScript is involved, canonicals/robots directives, sitemap membership, redirects, and any authorized first-party reporting. For performance, distinguish lab diagnostics from field/user data. For crawler behavior, distinguish a request in logs from a search/index/AI-answer outcome.

If evidence is unavailable, give a safe collection plan—not a guessed fix. Never bypass authentication, rate limits, paywalls, WAF controls, or robots rules to create evidence.

## Workflow

1. **State the expected behavior.** Is the URL intended to be indexable, canonical, localized, discoverable, rendered, fast enough for users, or excluded? Identify the owner/system that can change it.
2. **Capture the actual behavior.** Record raw response, directives, canonical, rendered content, redirect chain, linked/sitemap evidence, and relevant device/locale. Keep transient tool errors separate from confirmed defects.
3. **Find the smallest cause.** Test conflict pairs such as `noindex` vs canonical, raw vs JavaScript-injected metadata, redirect target vs sitemap URL, or locale target vs hreflang cluster. Do not infer a cause from a single score or generic audit rule.
4. **Classify the change.** Mark each item as confirmed issue, supported implementation opportunity, monitored experiment, or unresolved. Link platform-specific controls to current primary documentation.
5. **Plan the implementation.** For every recommendation state the affected URLs/templates, owner, precondition, exact desired state, verification capture, risk, approval, and rollback. Route cross-team work through `$seo-action-plan`.
6. **Verify after change.** Re-capture the relevant response/render, test the intended state, and use the appropriate reporting surface. Discovery, crawling, indexing, performance, and AI visibility are separate outcomes.

## Technical domains

- **Crawl/discovery:** robots handling, internal discovery, server health, sitemap inclusion, redirects, and crawl-access failures.
- **Index/canonical:** canonical/noindex conflicts, duplicate URL handling, status codes, redirects, and content availability.
- **Rendering:** raw versus rendered title, robots, canonical, meaningful content, and structured data; use actual captures rather than framework assumptions.
- **Experience:** responsive layout, interaction and rendering diagnostics, and field data where available. Core Web Vitals and tests guide improvement; they do not guarantee a ranking result.
- **International:** send locale clusters and annotations to `$seo-hreflang`; do not repair language targeting from a single URL.
- **Structured data:** send truthful markup changes to `$seo-schema`; validate the visible page and eligible documentation first.
- **Optional machine-readable guide:** for `llms.txt`, assess the documented target consumer, source-of-truth coverage, inclusion/exclusion policy, freshness, owner, and release path. Keep it separate from robots, access controls, and promises of ranking, retrieval, or citation. If that evidence is absent, record the gap rather than creating the file by default.

## Crawler-control policy

Treat crawler controls as an explicit business, legal, privacy, and technical decision. Identify the exact current documented user-agent and its declared purpose before proposing a rule. Training, search indexing, user-initiated fetches, and product-specific controls can be different agents. The Robots Exclusion Protocol is crawler guidance, not authorization or proof of downstream behavior.

Do not copy a blanket AI-bot block/allow template, assume a bot token is stable, or claim that blocking/allowing a bot changes citations. Crawler-control, `noindex`, canonical, robots, and WAF changes are high-risk and require an approved action plan, test URL, rollout/rollback, and current vendor documentation.

## Formal evidence handoff

When this work needs a cross-team, approval-ready plan, package evidence-bound findings as an immutable `seo-findings.json` bundle using the checked-out suite contract. Keep every referenced capture/source below `raw/`, retain declined claims and limitations, and run `python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>`. Send only a passing bundle to `$seo-action-plan`; otherwise label the handoff `provisional`.

## Output

For each finding provide: observed evidence and timestamp; expected state; scope; confidence/limitation; proposed owner/action; verification; risk; and rollback. Group only by priority/owner, never a blended technical score. Route broader page/editorial questions to `$seo-page` or `$seo-content`.
