---
name: ai-visibility-monitor
description: Measure repeatable AI-search mention, citation, answer-accuracy, cited-source-share, referral, and non-causal drift from a frozen, hash-pinned query corpus and a contract-valid Research Pack. Use for AI visibility baselines, recurring engine/surface observations, citation monitoring, answer accuracy checks, access-gap reporting, or comparison runs. Do not use for live research, query discovery, content optimization, rewriting, schema or technical SEO implementation, access-control bypass, rankings or citation guarantees, or causal attribution.
---

# AI Visibility Monitor

Produce a hash-pinned Visibility Run from immutable research, a frozen query corpus, and raw answer captures. This skill measures what was observed; it does not prescribe changes or claim why a metric moved.

## Required inputs

- Require a contract-valid Research Pack produced by `ai-search-research`; bind its bundle-relative path and SHA-256 into every run.
- Require a non-empty frozen query corpus whose `frozen_at` precedes every observation and whose query text, locale, engine, surface, and declared `fact_ids` resolve to that Research Pack.
- Require dated raw answer captures for observed cells. Preserve inaccessible, blocked, unavailable, and error states as explicit null-answer observations.
- For a comparison, require the prior Visibility Run as an immutable hash-pinned artifact.
- Read [measurement-protocol.md](references/measurement-protocol.md) before collecting, scoring, or comparing observations.

## Procedure

1. Validate the complete Research Pack and its semantic provenance before measurement.
2. Freeze the query corpus before collection. Record timezone-aware `frozen_at`, hash it, and require `frozen_at <= observed_at` for every cell; never add, remove, reword, translate, or silently substitute a query during a run.
3. Collect one observation per attempted query/engine/surface/locale cell. Record `observed_at`, access state, disclosed model when available, collection method, and either a hash-pinned raw answer envelope or, for non-observed access, a hash-pinned access-attempt receipt.
4. Preserve every cited URL exactly as observed, then derive the canonical URL by removing fragments and recognized tracking parameters. Never overwrite the raw URL.
5. Resolve mentioned entities only when a supplied Research Pack name or alias appears in the raw answer. Do not infer mentions from citations alone.
6. Score only explicit metrics using the canonical versioned `definition_id` and exact definition for that metric, with visible numerators, denominators, exclusions, results, and uncertainty notes. Missing access is not a negative result and is not hidden from the denominator story.
7. Check every fact declared for every observed corpus cell against Research Pack ground truth. Automatic `correct` requires both the extracted claim and the complete normalized answer to equal the accepted value; bind every other verdict to a hash-pinned review artifact. Use the actual `research_ref#fact_id` pointer. Preserve `partial` and `unverifiable` in the denominator rather than hiding them.
8. For comparisons, verify the prior-run hash, identity, chronology, Research Pack hash, corpus hash, metric definition, score target, access-status profile, and referral source/method/window duration. Mark changed research, access, referral methodology, null-valued, or mismatched cohorts non-comparable and explain the warning.
9. Describe movement as observational drift. Scan only monitor-authored limitations, uncertainty notes, and drift commentary for causal assertions; preserve quoted engine or review evidence as evidence. Never state or imply that an optimization, publication, schema change, crawler setting, or other intervention caused movement.
10. Create `visibility-run.json` with stable unique IDs, hash-pinned external artifacts, explicit limitations, and no optimization recommendations.
11. From a checked-out suite repository, run `python scripts/validate_ai_visibility_monitor.py validate-run <artifact> --bundle <bundle>` and close all critical or important findings. Put minor findings in backlog. Runtime skill installation intentionally keeps validation tooling in the versioned suite checkout.

## Metric boundaries

- `mention_rate`: share of eligible observed answers that explicitly mention one Research Pack entity.
- `citation_rate`: share of eligible observed answers containing at least one citation.
- `cited_source_share`: share of distinct canonical sources per observed answer matching one declared canonical source URL.
- `answer_accuracy`: share of all declared fact-to-observation checks assessed `correct`; `partial` and `unverifiable` remain in the denominator.
- `referral_rate`: use only when a hash-pinned referral envelope binds a supported raw event export. Recompute the numerator and denominator from eligible `ai`/`non_ai` events inside the declared window. Otherwise omit it.

Do not combine these metrics into a universal visibility score. Do not compare percentages whose corpora, access states, time windows, locales, or metric definitions are not comparable.

## Ownership boundaries

- Route new query discovery, source collection, or Research Pack repair to `ai-search-research`.
- Route direct-answer and extractability audits to `seo-aeo`.
- Route entity, evidence, citation-suitability, and documented engine-control audits to `seo-geo`.
- Route a validated audit and any needed baseline evidence to `seo-action-plan` before implementation; this monitor does not rewrite, optimize, or approve a change.

Never bypass authentication, bot controls, rate limits, paywalls, or unavailable product access. Record the access state and continue with the observable cohort.

## Severity and review rule

- `critical`: the run would be materially false, fabricated, unsafe, or unusable.
- `important`: provenance, denominator, raw-evidence binding, comparison integrity, or ownership is materially incomplete or misleading.
- `minor`: a non-blocking clarity or maintainability improvement.

Close critical and important findings. Backlog minor findings. Review each candidate hash at most twice.
