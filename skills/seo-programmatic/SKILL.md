---
name: seo-programmatic
description: Use when designing, auditing, or improving scaled/template-driven SEO pages, data-backed landing-page systems, or large URL inventories; require source data, usefulness, variation, indexing controls, and rollout safeguards rather than scale or keyword coverage targets.
---

# Programmatic SEO

## Purpose

Assess or plan scalable page systems without creating index bloat, misleading content, or unmaintainable templates. The unit of review is the page system: input data, template logic, user task, content differentiation, URL/canonical rules, quality controls, and rollout behavior.

Read `references/scaled-page-protocol.md` before approving a template or rollout.

## Input gate

Require the page-system purpose, target reader/task, data dictionary and provenance, source update cadence, template/rendered examples, locale/market rules, canonical/indexability policy, internal linking logic, quality owner, and proposed rollout. Do not infer product facts, locations, prices, availability, comparisons, or user demand from keyword lists alone.

## Workflow

1. **Model the user value.** Explain what distinct decision/task each page can satisfy and what evidence or data makes it different from nearby variants.
2. **Inspect inputs and template.** Verify data ownership, freshness, null/error handling, sourced claims, locale logic, entity identity, URLs, canonical behavior, structured data eligibility, and rendering.
3. **Sample for failure modes.** Review representative normal, sparse-data, conflicting-data, locale, outlier, and deprecation cases. Look for thin duplication, made-up combinations, contradictory claims, inaccessible values, or non-functional internal paths.
4. **Define publication gates.** State required fields, minimum useful differentiation, source freshness policy, human/editorial exceptions, noindex/withhold conditions, QA sample, monitoring, and removal/rollback behavior. Do not use word counts or static “unique-content percentages” as the gate.
5. **Stage rollout.** Begin with an owned, reversible cohort; verify rendered pages, links, canonicals, analytics/monitoring, and user feedback. Expand only after the declared acceptance criteria pass. Route production implementation through `$seo-action-plan`.

## Guardrails

- Do not publish pages for entities/locations/products that the source data cannot support.
- Do not mass-generate text, images, reviews, comparisons, schema, or local facts to simulate usefulness.
- Do not treat index coverage, crawl hits, or URL count as proof of user value or search performance.
- Keep data privacy, licensing, local/regulatory requirements, and deletion/update pathways in the design.

## Formal evidence handoff

When this work needs a cross-team, approval-ready plan, package evidence-bound findings as an immutable `seo-findings.json` bundle using the checked-out suite contract. Keep every referenced capture/source below `raw/`, retain declined claims and limitations, and run `python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>`. Send only a passing bundle to `$seo-action-plan`; otherwise label the handoff `provisional`.

## Output

Return a system map, data/provenance gaps, template findings, representative QA matrix, publication gates, rollout/rollback plan, owners, and source-appropriate verification. Do not emit a programmatic SEO score or a blanket publish recommendation.
