---
name: seo
description: Route and coordinate SEO, AEO, GEO, AI-search research, visibility measurement, action planning, technical SEO, content, schema, sitemap, image, hreflang, page, audit, strategy, and programmatic requests to the smallest correct specialist workflow. Use when a request says SEO broadly, spans multiple disciplines, needs sequencing, or is ambiguous about audit, approved implementation, or measurement. Do not use as a substitute for a named specialist or to create a universal score, unsupported AI-search control, causal uplift claim, or placement guarantee.
---

# SEO Router

Select the smallest specialist set, preserve artifact boundaries, and reconcile the final handoff. This router does not invent findings, implement specialist work itself, or merge unlike metrics into one score.

Read [routing-matrix.md](references/routing-matrix.md) before routing a broad or mixed request.

## Routing procedure

1. Identify the requested outcome: research, audit, implementation, strategy, or measurement.
2. Identify the surface and scope: site, page, content set, locale, engine/surface, technical system, or recurring run.
3. Route a single-lane request directly to one specialist. Do not launch a full audit when a narrow skill owns the work.
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
- Broad implementation optimization after a validated, approved action plan -> `optimise-seo`.

## Compound-work rules

- If the request lacks current evidence, run `ai-search-research` before `seo-aeo`, `seo-geo`, or `ai-visibility-monitor`.
- AEO and GEO may run in parallel only after both receive the same validated Research Pack and immutable target captures.
- Convert validated findings into an action plan before implementation. Use a validated `optimization-brief.json` for AEO/GEO findings or a validated `seo-findings.json` bundle for conventional SEO findings. Run implementation only from an approved action with an explicit owner, acceptance criteria, verification, and rollback. Keep experiments separate from required changes.
- Establish a baseline before implementation when the user wants change tracking. A later comparison is observational drift, not causal proof.
- If access is blocked or unavailable, record the gap; never bypass authentication, paywalls, bot controls, or rate limits.

## Guardrails

Do not create a universal SEO score or blend technical, content, AEO, GEO, and visibility metrics into a false precision number. Decline mandatory `llms.txt`, fixed passage or word-count formulas, blanket crawler instructions, invented ranking factors, unsupported source percentages, guaranteed rankings, guaranteed mentions, guaranteed citations, or any guarantee of AI placement. A bot request is not evidence of retrieval, citation, referral, or conversion.

When an existing specialist already owns the request, route to it without duplicating its instructions.
