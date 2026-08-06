# AI visibility measurement protocol

## Measurement unit

A cell is one frozen `query_id` executed on one declared engine, surface, and locale, with a non-empty frozen set of Research Pack `fact_ids`. The corpus carries timezone-aware `frozen_at` no later than any observation. Attempt every cell exactly once per run; do not select the most favorable answer.

An observation is valid only when its query, engine, surface, and locale match the frozen corpus. Its timestamp must be timezone-aware and no later than the Visibility Run creation time. The run also pins the exact Research Pack path and SHA-256; an ID alone is insufficient.

## Access states

Use `observed` only when a raw answer was captured. Use `inaccessible`, `blocked`, `unavailable`, or `error` for every other outcome. Non-observed cells carry no answer hash, mentioned entity, or cited URL, but must carry a hash-pinned access-attempt receipt whose query, engine, surface, locale, time, status, method, and non-empty reason match the observation. Explain access gaps in limitations.

Never simulate access, reuse an older answer as a current observation, bypass controls, or convert an access failure into a zero mention/citation result.

## Raw evidence and URL handling

Store each observed answer as an immutable JSON envelope with exactly `query_id`, `engine`, `surface`, `locale`, `observed_at`, `access_status`, `disclosed_model`, `collection_method`, `answer`, and `citations`. Hash the file and preserve citation URLs exactly. Canonicalization may lowercase scheme/host, remove fragments, trim a non-root trailing slash, sort query parameters, and remove `utm_*`, `gclid`, `fbclid`, and `msclkid`. Do not discard raw URLs.

Entity mentions require a literal Research Pack name or alias in the captured answer. Citations do not prove that an entity was mentioned, that a claim is correct, or that a source influenced generation.

## Denominators

Every score exposes numerator, denominator, excluded observation IDs, result, canonical versioned `definition_id`, exact metric definition, and uncertainty note. A zero denominator produces a null result. Post-collection exclusions are forbidden; cohort eligibility is frozen in the query corpus.

- Mention and citation rates use eligible `observed` cells, not attempted cells, unless a separately named availability metric is introduced in a later contract.
- Cited-source share uses distinct canonical sources per observed answer; it is not a share of answers.
- Answer accuracy covers every declared fact for every observed cell. Exact normalized accepted-value matches may be `correct`; every other verdict requires a hash-pinned review envelope. `Partial` and `unverifiable` remain in the denominator.
- Referral rate requires an external hash-pinned referral envelope plus a supported hash-pinned raw event export. Both bind exact source, non-empty `measurement_method`, and window metadata; events contain `event_id`, `occurred_at`, `source_category` (`ai` or `non_ai`), and `eligible`. Recompute numerator and denominator from eligible in-window events; never trust envelope totals alone. An answer citation is not a referral visit.

Do not average unlike rates or publish a composite visibility score.

## Comparison and drift

A comparison requires a prior hash-pinned Visibility Run. Verify prior identity, schema version, chronology, Research Pack hash, corpus hash, metric definition, score target, locale, engine/surface cohort, exclusions, query-level access-status profile, and referral source/method/window duration when applicable.

If any material comparison input changed, either value is null, or access status changed, set `comparable` to false and state the difference. Arithmetic delta is `current_value - prior_value`; it is descriptive drift only. Avoid causal language such as "the optimization caused," "led to," "enhanced visibility," or "produced uplift."

## Accuracy review

Bind each accuracy check to one observed answer and one corpus-declared Research Pack ground-truth fact. Extract the specific observed claim, record the review method, preserve the exact `research_ref#fact_id` pointer, and choose `correct`, `incorrect`, `partial`, or `unverifiable`. Automatic `correct` requires both the extracted claim and the complete normalized raw answer to equal the accepted value; this prevents a true phrase inside negation or quotation from becoming automatic proof. Every other verdict requires an immutable review envelope matching the check, accepted value, rationale, reviewer, and a review time no earlier than the observation and no later than run creation. A missing declared pair, fact, raw answer, or required review invalidates the run.

## Handoff

The monitor may report measurement gaps and validated drift. It does not recommend copy, schema, technical, entity, source, or crawler changes. Send research gaps to `ai-search-research`, AEO audit questions to `seo-aeo`, and GEO audit questions to `seo-geo`.
