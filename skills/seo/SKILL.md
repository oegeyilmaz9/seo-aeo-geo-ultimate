---
name: seo
description: The default entry point for any SEO, AEO, GEO, or AI-search request. Route and coordinate research, audits, measurement, action planning, and approved implementation to the smallest correct specialist workflow; direct specialist invocation remains available for users who deliberately need one lane. Do not create a universal score, unsupported AI-search control, causal uplift claim, or placement guarantee.
---

# SEO Router

Use `seo` as the default front door for every request in this suite: a narrow technical question, a content review, an AI-search investigation, a multi-team plan, or a scoped authorized change. Select the smallest specialist set, preserve artifact boundaries, and reconcile the final handoff. This router does not invent findings, implement specialist work itself, or merge unlike metrics into one score.

Read [routing-matrix.md](references/routing-matrix.md) before routing a request through the suite.

## Routing procedure

1. Identify the requested outcome: research, audit, implementation, strategy, or measurement.
2. Identify the surface and scope: site, page, content set, locale, engine/surface, technical system, or recurring run.
3. Route a single-lane request directly to one specialist. Do not launch a full audit when a narrow skill owns the work; the caller can still begin with `seo` rather than choosing that specialist themselves.
4. For compound optimize-and-track work, use this phase order: `research -> audit -> baseline measurement -> action planning -> approved implementation -> comparison measurement`.
5. Require each phase's real artifact or explicit limitation before starting a dependent phase. AEO/GEO work hands off a validated `optimization-brief.json`; conventional SEO lanes hand off a validated `seo-findings.json` bundle. Do not let a downstream specialist silently repair missing upstream evidence or self-approve a change.
6. Parallelize only independent lanes. Keep the final synthesis with the orchestrator and preserve disagreements instead of averaging them away.
7. Close critical and important findings before release; record minor findings in backlog. Review one candidate hash at most twice.

## AI-search routes

- Missing queries, sources, observations, ground truth, or engine/surface evidence -> `ai-search-research`.
- Direct-answer completeness, clarity, extractability, intent coverage, or answer structure -> `seo-aeo`.
- Entity consistency, evidence traceability, citation suitability, cited-source alignment, or documented engine controls -> `seo-geo`.
- Repeatable mention, citation, accuracy, referral, retrieval trace, consulted-source, citation-claim, access, uncertainty, baseline, comparison, or drift measurement -> `ai-visibility-monitor`.
- Approval-ready sequencing, ownership, risk, rollback, verification, or a cross-team implementation handoff -> `seo-action-plan`.

Do not treat AEO and GEO as synonyms. Do not send live research to an audit skill, implementation to the monitor, or measurement to an optimization audit.

## Existing SEO routes

- Full multi-lane site assessment -> `seo-audit`.
- One page with mixed on-page concerns -> `seo-page`.
- Crawlability, indexability, rendering, robots, canonicalization, performance, headers, or directives -> `seo-technical`.
- Content quality, helpfulness, E-E-A-T, topical coverage, or editorial remediation -> `seo-content`.
- Structured data detection, validation, or generation -> `seo-schema`.
- Image discovery, formats, dimensions, alt text, or media performance -> `seo-images`.
- XML sitemap analysis or generation -> `seo-sitemap`.
- International targeting and language-region annotations -> `seo-hreflang`.
- Strategic roadmap and prioritization -> `seo-plan`.
- Template-driven or large-scale landing-page systems -> `seo-programmatic`.
- Competitor comparison or alternative pages -> `seo-competitor-pages`.
- Long-form query and evidence discovery -> `seo-research` when AI-search Research Pack provenance is not required.
- Search Console, Bing Webmaster Tools, analytics, indexation, Core Web Vitals/RUM, conventional baseline, or comparison measurement -> `seo-performance`.
- Import or normalize an authorized Search Console, Bing, organic GA4, crawler CSV, or server log -> the matching `seo-performance`, `seo-architecture`, or `seo-technical` owner using the suite data-import adapter; import is evidence preparation, not a validated finding or outcome.
- Product/category pages, Product/MerchantListing data, merchant feeds, price/availability parity, shopping discovery, commerce protocols, or IndexNow catalog freshness -> `seo-commerce`.
- Business profiles, NAP/hours/categories, service areas, location pages, local schema, reviews, or location-aware queries -> `seo-local`.
- Watch pages, video players, VideoObject, video sitemaps, thumbnails, transcripts/captions, Key Moments, livestreams, or video indexing -> `seo-video`.
- News/Discover publisher policy, articles, dates/bylines/corrections, NewsArticle, news sitemaps/feeds, large images, paywalls, or freshness reporting -> `seo-news-discover`.
- Agent perception and task completion through DOM/accessibility/UI state, safe forms, auth/consent, or documented UCP/ACP/MCP/A2A capabilities -> `seo-agentic`.
- Site graphs, navigation, hubs, crawl paths, orphan evidence, facets, taxonomy, pagination, internal links, or query-to-page architecture -> `seo-architecture`.
- Backlinks, referring domains, source citations, brand/unlinked mentions, linkable evidence, digital PR, or link-scheme risk -> `seo-authority`.
- Optional `llms.txt` suitability, generation, validation, publishing, or maintenance -> `seo-technical`; offer it as a low-cost maintained publisher guide when public sources and a refresh owner exist, not as a universal crawler or visibility control.
- Site migration/replatforming, sudden traffic/indexation incident, manual action, or hacked-site search recovery -> `seo-technical`; involve the security incident owner for any suspected compromise.
- Controlled SEO experiment design, baseline, or evaluation -> `seo-performance`; require `seo-action-plan` before exposure and `seo-technical` when variant delivery, redirects, canonicals, or directives are involved.
- Broad implementation optimization after a validated, approved action plan -> `optimise-seo`.

## Compound-work rules

- If the request lacks current evidence, run `ai-search-research` before `seo-aeo`, `seo-geo`, or `ai-visibility-monitor`.
- AEO and GEO may run in parallel only after both receive the same validated Research Pack and immutable target captures.
- Convert validated findings into an action plan before implementation. Use a validated `optimization-brief.json` for AEO/GEO findings or a validated `seo-findings.json` bundle for conventional SEO findings. Run implementation only from an approved action with an explicit owner, acceptance criteria, verification, and rollback. Keep experiments separate from required changes.
- Establish a formal Query Corpus and the correct baseline before implementation when the user wants change tracking. Use `seo-performance` for conventional first-party search/site metrics and `ai-visibility-monitor` for observed AI answers; never merge them into one score. A later comparison is observational drift, not causal proof.
- Use the current validated platform-controls registry before feature, crawler, change-notification, or protocol recommendations. Route expired or unknown controls back to research instead of copying a stale rule.
- If access is blocked or unavailable, record the gap; never bypass authentication, paywalls, bot controls, or rate limits.

## Guardrails

Do not create a universal SEO score or blend technical, content, AEO, GEO, and visibility metrics into a false precision number. Decline mandatory `llms.txt`, fixed passage or word-count formulas, blanket crawler instructions, invented ranking factors, unsupported source percentages, guaranteed rankings, guaranteed mentions, guaranteed citations, or any guarantee of AI placement. Offer `llms.txt` as an optional, evidence-scoped publisher guide when trustworthy public sources, a defined scope, and a maintenance owner make it cheap to keep correct; a documented consumer is useful but not required. A bot request is not evidence of retrieval, citation, referral, or conversion.

When an existing specialist owns the next step, route to it without duplicating its instructions. Directly invoking that specialist remains available, but `seo` is the recommended entry point when the user wants the suite to choose the right path.
