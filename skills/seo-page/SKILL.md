---
name: seo-page
description: Use when one URL needs a bounded mixed SEO review across reader task, content, metadata, links, technical delivery, accessibility, and structured data; produce an evidence map and route each fix to its real owner instead of a page score.
---

# One-page SEO Review

## Purpose

Assess a single page in its actual context and turn confirmed observations into specialist-owned next steps. This is a coordination/audit skill, not a generic rewrite, site crawl, implementation tool, or universal score.

Read `references/page-review-protocol.md` before a formal review.

## Input gate

Collect the canonical/requested URL, page role, reader task, locale/device, raw and rendered capture where possible, key headers, current metadata/structured data, internal destinations, and authorized performance/indexing evidence. If the page or context cannot be accessed, explain the limitation and list safe evidence to collect.

## Workflow

1. **Declare the page contract.** What audience, task, site role, locale, and intended canonical/indexability state does this URL serve?
2. **Inspect the rendered experience and delivery.** Separate visible content/links/media from raw response, directives, canonicalization, rendering, and structured data. Keep observations tied to a capture and time.
3. **Map observations by lane.** Route content usefulness and drafts to `$seo-content`; delivery/crawling/rendering to `$seo-technical`; structured data to `$seo-schema`; media to `$seo-images`; locale cluster issues to `$seo-hreflang`; and sitemap/inventory questions to `$seo-sitemap`.
4. **Distinguish defects from choices.** A mismatch with an explicit page contract may be a confirmed defect; an apparent opportunity without evidence is a hypothesis. Avoid arbitrary meta-length, heading-count, word-count, keyword-density, or internal-link quotas.
5. **Create a handoff.** Give each recommendation an evidence pointer, scope, owner, impact/risk statement, acceptance criterion, verification, and rollback if the change could harm users or discovery. Use `$seo-action-plan` for an approved cross-team implementation plan.

## Guardrails

- Do not infer indexation, rankings, citations, or traffic from a page capture.
- Do not change a page, deploy markup, submit URLs, or claim approval.
- No overall page score. Preserve conflicting evidence instead of averaging it.
- Treat content intent, technical eligibility, measurement, and platform-specific AI visibility as separate questions.

## Formal evidence handoff

When this work needs a cross-team, approval-ready plan, package evidence-bound findings as an immutable `seo-findings.json` bundle using the checked-out suite contract. Keep every referenced capture/source below `raw/`, retain declined claims and limitations, and run `python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>`. Send only a passing bundle to `$seo-action-plan`; otherwise label the handoff `provisional`.

## Output

Return the page contract, capture limitations, lane-by-lane evidence table, confirmed defects, provisional opportunities, routing/ownership, and a minimal next action list. For implementation, cite the required approved action-plan item.
