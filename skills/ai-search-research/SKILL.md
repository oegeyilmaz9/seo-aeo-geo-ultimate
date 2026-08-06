---
name: ai-search-research
description: Use when a request concerns AEO/GEO demand research, AI-answer or generative-search query-corpus research, entity or source-landscape mapping, citation-source or competitor benchmarking, bilingual TR/EN research, missing-access planning, evidence freshness or classification, or pressure to treat unproven tactics as universal rules; do not use for page audits, content rewriting, technical SEO, schema, hreflang, implementation, or longitudinal visibility monitoring.
---

# AI Search Research

Produce `research-pack.json` before any human summary. Treat the JSON artifact as authoritative.

## Procedure

1. Define scope, native locales, entities, ambiguities, audiences, journey stages, engines, and distinct surfaces. Cover every declared locale with native query objects; never force an undeclared locale. Select audiences from the request scope; do not force unrelated audiences. Keep Google AI Overview and AI Mode separate.
2. Read [evidence-policy.md](references/evidence-policy.md). Record every externally testable claim as one evidence record with one resolving `raw_evidence_ref`; do not merge claims or omit explicit scope.
3. Read [capture-protocol.md](references/capture-protocol.md). Preserve raw observations inside the artifact bundle and use only bundle-relative references.
4. Write each query for every declared locale as an independent native object with locale, intent, request-derived audience, journey stage, target entities, and engine/surface applicability. Use native orthography and script. Reject ASCII transliteration presented as native when the locale requires its native script or diacritics. Do not infer locale from language, translate mechanically, or apply heuristic language validation in the validator.
5. Record a competitor observation only when a dated raw answer or result capture resolves locally and identifies engine, surface, locale, mentioned entities, and raw cited URLs. Treat source-landscape pages as evidence, not as competitor observations.
6. Record ground truth with stable fact IDs, immutable bundle-relative provenance, and validity windows.
7. Add one explicit gap for every inaccessible engine/surface/locale cell, ambiguity, missing evidence item, or stale input. Choose exactly one stable `gap_type` with the decision rules in the capture protocol; do not substitute prose synonyms. Use `null` only where the contract permits it and explain the limitation.
8. Reject guarantees, universal passage lengths, mandatory `llms.txt`, blanket crawler access, mass FAQ schema, and causal citation-lift claims unless current primary evidence supports that exact scoped statement. Retain an unproven tactic as `experimental` or `speculative` only when a valid evidence record supports that classification. When no evidence exists, do not retain a hypothesis; record only a `missing_evidence` gap with empty `related_claim_ids`.
9. Validate against `references/contracts/research-pack.schema.json` and the locked shared evidence contract. Stop on missing fields, absolute paths, unresolved raw references, stale current claims, or lock drift.
10. Hand direct-answer completeness, clarity, intent coverage, and extractability audits to `seo-aeo`; hand entity, evidence, source, citation, and documented engine-control audits to `seo-geo`. Route technical controls to `seo-technical`, content changes to `seo-content`, structured data to `seo-schema`, locale implementation to `seo-hreflang`, evidence-linked implementation planning to `seo-action-plan`, explicitly authorized implementation to `optimise-seo`, and trend measurement to `ai-visibility-monitor`.

Never invent sources, quotes, dates, model versions, observations, citations, rankings, referral data, metrics, or access. Never call an incomplete generic template complete or launch-ready.
