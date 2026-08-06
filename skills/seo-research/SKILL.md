---
name: seo-research
description: Use when researching conventional search intent, audience questions, content gaps, site coverage, or competitor/page evidence for a bounded SEO decision; retain source dates and uncertainty, and route formal multi-engine AI-search provenance to ai-search-research.
---

# SEO Research

## Purpose

Build a decision-ready research note for traditional/web-search content and site decisions. This skill is for scoped discovery, not for a fabricated keyword spreadsheet, mass scraping, or a substitute for the immutable multi-engine `$ai-search-research` Research Pack.

Read `references/research-evidence-protocol.md` before presenting research conclusions.

## Input gate

Clarify audience, market/locale, decision to be made, known site/entity URLs, time horizon, access/permissions, and available first-party data. Decide whether the question is conventional search research or AI-search research:

- Use `$ai-search-research` for engine/surface-specific AI evidence, ground truth, citations, or formal Research Pack provenance.
- Use this skill for content/search intent, page inventory, query language, competitor/page observations, and source-backed opportunity framing without that formal contract.

## Workflow

1. **Define the decision.** State the audience task, market/locale, entity/page scope, non-goals, and evidence required to decide.
2. **Build a query/question corpus.** Group language by reader task and stage, not just lexical similarity. Preserve query source, date, locale/device/context, and limitations. Treat volume/difficulty/vendor metrics as dated third-party estimates, never ground truth.
3. **Inspect existing coverage.** Map actual pages/assets to the questions they serve, cite rendered/captured evidence, and identify gaps, cannibalization risk, stale claims, or unclear ownership without assuming a missing keyword requires a new page.
4. **Research external evidence responsibly.** Use primary docs, authoritative sources, and accessible pages. Capture title, URL, access date, source type, claim, and limitations. Respect robots, terms, rate limits, paywalls, authentication, and copyright.
5. **Synthesize choices.** Recommend research-backed content, technical, measurement, or no-action paths. Separate observed facts, inferred opportunities, experiments, and unknowns.
6. **Hand off.** Send content work to `$seo-content`, competitor pages to `$seo-competitor-pages`, implementation sequencing to `$seo-action-plan`, and AI-specific formal work to `$ai-search-research`.

## Guardrails

- Do not present a snapshot of results, snippets, third-party tool data, or AI answers as stable truth.
- Do not scrape protected sources, bypass controls, or reproduce copyrighted source text beyond what is needed to substantiate a finding.
- Do not promise rankings, traffic, citations, or business outcomes.
- Do not convert keyword volume, page count, or competitor activity into a universal opportunity score.

## Formal evidence handoff

When this work needs a cross-team, approval-ready plan, package evidence-bound findings as an immutable `seo-findings.json` bundle using the checked-out suite contract. Keep every referenced capture/source below `raw/`, retain declined claims and limitations, and run `python scripts/validate_seo_findings.py validate-findings <bundle>/seo-findings.json --bundle <bundle>`. Send only a passing bundle to `$seo-action-plan`; otherwise label the handoff `provisional`.

## Output

Return a decision statement, query/question corpus, source register, existing-coverage map, observation/inference split, opportunities or declined ideas, owners, and evidence gaps. Include collection dates and a refresh trigger for volatile sources.
