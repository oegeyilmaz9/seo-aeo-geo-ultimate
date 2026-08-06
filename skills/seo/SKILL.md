---
name: seo
description: The default entry point for any SEO, AEO, GEO, or AI-search request. Route and coordinate research, audits, measurement, action planning, and approved implementation to the smallest correct specialist workflow; direct specialist invocation remains available for users who deliberately need one lane. Do not create a universal score, unsupported AI-search control, causal uplift claim, or placement guarantee.
---

# SEO Router

Use `$seo` as the default front door for every request in this suite: a narrow technical question, a content review, an AI-search investigation, a multi-team plan, or a scoped authorized change. Select the smallest specialist set, preserve artifact boundaries, and reconcile the final handoff. This router does not invent findings, implement specialist work itself, or merge unlike metrics into one score.

Read [routing-matrix.md](references/routing-matrix.md) before routing a request through the suite.

## Routing procedure

1. Identify the requested outcome: research, audit, implementation, strategy, or measurement.
2. Identify the surface and scope: site, page, content set, locale, engine/surface, technical system, or recurring run.
3. Route a single-lane request directly to one specialist. Do not launch a full audit when a narrow skill owns the work; the caller can still begin with `$seo` rather than choosing that specialist themselves.
4. For compound optimize-and-track work, use this phase order: `research -> audit -> baseline measurement -> action planning -> approved implementation -> comparison measurement`.
5. Require each phase's real artifact or explicit limitation before starting a dependent phase. AEO/GEO work hands off a validated `optimization-brief.json`; conventional SEO lanes hand off a validated `seo-findings.json` bundle. Do not let a downstream specialist silently repair missing upstream evidence or self-approve a change.
6. Parallelize only independent lanes. Keep the final synthesis with the orchestrator and preserve disagreements instead of averaging them away.
7. Close critical and important findings before release; record minor findings in backlog. Review one candidate hash at most twice.

## AI-search routes

- Missing queries, sources, observations, ground truth, or engine/surface evidence -> `ai-search-research`.
- Direct-answer completeness, clarity, extractability, intent coverage, or answer structure -> `seo-aeo`.
- Entity consistency, evidence traceability, citation suitability, cited-source alignment, or documented engine controls -> `seo-geo`.
- Repeatable mention, citation, accuracy, referral, access, baseline, comparison, or drift measurement -> `ai-visibility-monitor`.
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
- Optional `llms.txt` suitability, source ownership, publishing, or maintenance -> `seo-technical`; treat it as a maintained publisher guide, not a universal crawler or visibility control.
- Broad implementation optimization after a validated, approved action plan -> `optimise-seo`.

## Compound-work rules

- If the request lacks current evidence, run `ai-search-research` before `seo-aeo`, `seo-geo`, or `ai-visibility-monitor`.
- AEO and GEO may run in parallel only after both receive the same validated Research Pack and immutable target captures.
- Convert validated findings into an action plan before implementation. Use a validated `optimization-brief.json` for AEO/GEO findings or a validated `seo-findings.json` bundle for conventional SEO findings. Run implementation only from an approved action with an explicit owner, acceptance criteria, verification, and rollback. Keep experiments separate from required changes.
- Establish a baseline before implementation when the user wants change tracking. A later comparison is observational drift, not causal proof.
- If access is blocked or unavailable, record the gap; never bypass authentication, paywalls, bot controls, or rate limits.

## Guardrails

Do not create a universal SEO score or blend technical, content, AEO, GEO, and visibility metrics into a false precision number. Decline mandatory `llms.txt`, fixed passage or word-count formulas, blanket crawler instructions, invented ranking factors, unsupported source percentages, guaranteed rankings, guaranteed mentions, guaranteed citations, or any guarantee of AI placement. Treat `llms.txt` as an optional, evidence-scoped technical decision only when there is a documented consuming system, a trustworthy source of truth, a defined content scope, and a maintenance owner. A bot request is not evidence of retrieval, citation, referral, or conversion.

When an existing specialist owns the next step, route to it without duplicating its instructions. Directly invoking that specialist remains available, but `$seo` is the recommended entry point when the user wants the suite to choose the right path.
