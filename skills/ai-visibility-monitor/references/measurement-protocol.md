# AI visibility measurement protocol

## Measurement unit

A cell is one frozen `query_id` executed on one declared engine, surface, locale, and `repeat_index`, with a non-empty frozen set of Research Pack `fact_ids`. The formal Query Corpus carries the matching Research Pack hash and a timezone-aware `frozen_at` no later than any observation. Attempt every declared repeat; do not select the most favorable answer.

An observation is valid only when its query, engine, surface, locale, device, location, and declared conversation/turn context match the frozen corpus. Formal `executed_subquery` rows resolve through their parent chain to one measurement root; any disclosed `executed_queries` must match that lineage. Fresh-session repeats require distinct conversation IDs. Its timestamp must be timezone-aware and no later than the Visibility Run creation time. The run also pins the exact Research Pack path and SHA-256; an ID alone is insufficient.

## Access states

Use `observed` only when a raw answer was captured. Use `inaccessible`, `blocked`, `unavailable`, or `error` for every other outcome. Non-observed cells carry no answer hash, mentioned entity, or cited URL, but must carry a hash-pinned access-attempt receipt whose query, engine, surface, locale, time, status, method, and non-empty reason match the observation. Explain access gaps in limitations.

Never simulate access, reuse an older answer as a current observation, bypass controls, or convert an access failure into a zero mention/citation result.

## Raw evidence and URL handling

Store each schema `2.0.0` answer as an immutable envelope containing the observation metadata plus answer, citations, executed queries, consulted sources, and citation claims. Preserve only queries and sources exposed by the collection surface; empty is more truthful than reconstructed fan-out. Hash the file and preserve citation URLs exactly. Canonicalization may lowercase scheme/host, remove fragments, trim a non-root trailing slash, sort query parameters, and remove recognized tracking parameters. Do not discard raw URLs.

Consulted sources are the disclosed retrieval/source set; citations are the subset visibly attributed in the answer. For every citation claim, preserve the answer claim, cited text, URL, support verdict, reviewer, rationale, and review time in a hash-pinned review envelope. A citation URL alone never proves that the source supports the answer.

Entity mentions require a literal Research Pack name or alias in the captured answer. Citations do not prove that an entity was mentioned, that a claim is correct, or that a source influenced generation.

## Denominators

Every score exposes numerator, denominator, sample size, repeat count, excluded observation IDs, result, canonical definition, confidence interval or `not-estimated`, and uncertainty note. A zero denominator produces a null result. Post-collection exclusions are forbidden; cohort eligibility is frozen in the Query Corpus.

- Mention and citation rates use eligible `observed` cells, not attempted cells, unless a separately named availability metric is introduced in a later contract.
- Cited-source share uses distinct canonical sources per observed answer; it is not a share of answers.
- Answer accuracy covers every declared fact for every observed cell. Exact normalized accepted-value matches may be `correct`; every other verdict requires a hash-pinned review envelope. `Partial` and `unverifiable` remain in the denominator.
- Referral rate requires an external hash-pinned referral envelope plus a supported hash-pinned raw event export. Both bind exact source, non-empty `measurement_method`, and window metadata; events contain `event_id`, `occurred_at`, `source_category` (`ai` or `non_ai`), and `eligible`. Recompute numerator and denominator from eligible in-window events; never trust envelope totals alone. An answer citation is not a referral visit.

Use repeated observations and the declared Wilson method when estimating uncertainty. The validator recomputes the interval from numerator, denominator, and confidence level; analyst-supplied or mislabeled bounds are rejected. If no interval is calculated, write `not-estimated` with null bounds. Do not average unlike rates or publish a composite visibility score.

## Comparison and drift

A comparison requires a prior hash-pinned Visibility Run of the same schema version. Verify prior identity, chronology, Research Pack hash, corpus hash, repeat/confidence profile, metric definition, score target, locale, engine/surface/repeat cohort, exclusions, access status, user location, device, authentication, personalization, retrieval mode, disclosed model, collection method, turn context, and referral source/method/window duration when applicable.

If any material comparison input changed, either value is null, or access status changed, set `comparable` to false and state the difference. Arithmetic delta is `current_value - prior_value`; it is descriptive drift only. Avoid causal language such as "the optimization caused," "led to," "enhanced visibility," or "produced uplift."

## Accuracy review

Bind each accuracy check to one observed answer and one corpus-declared Research Pack ground-truth fact. Extract the specific observed claim, record the review method, preserve the exact `research_ref#fact_id` pointer, and choose `correct`, `incorrect`, `partial`, or `unverifiable`. Automatic `correct` requires both the extracted claim and the complete normalized raw answer to equal the accepted value; this prevents a true phrase inside negation or quotation from becoming automatic proof. Every other verdict requires an immutable review envelope matching the check, accepted value, rationale, reviewer, and a review time no earlier than the observation and no later than run creation. A missing declared pair, fact, raw answer, or required review invalidates the run.

## Handoff

The monitor may report measurement gaps and validated drift. It does not recommend copy, schema, technical, entity, source, or crawler changes. Send research gaps to `ai-search-research`, AEO audit questions to `seo-aeo`, and GEO audit questions to `seo-geo`.
