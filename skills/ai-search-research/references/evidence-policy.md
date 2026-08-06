# Evidence and freshness policy

## Classification

- `confirmed`: use current first-party documentation, an applicable standard, or a reproducible direct observation for a narrowly scoped factual finding.
- `vendor-recommended`: attribute current first-party advice to the vendor; never call it a ranking factor or guarantee.
- `experimental`: state the method, date, limitations, and falsifiable hypothesis; never make it a mandatory gate.
- `speculative`: keep anecdotes, weak correlations, and working hypotheses in the research backlog only.

Create one record per externally testable claim. Include every contract field and classify its provenance with `source_kind`: `vendor_documentation`, `standard`, `direct_observation`, `original_research`, or `secondary_context`. Use `null` for an unknown source publication/update date; never infer it. Use explicit `engine`, `surface`, and `locale`, or `not_applicable` when genuinely outside those dimensions. Keep conflicting sources as separate records and prefer the current primary source only for present-tense guidance. Phrase every conclusion no more strongly than its weakest necessary premise.

Every claim must have one raw reference per claim in `raw_evidence_ref`, resolving to a regular file under `raw/`. Preserve the minimum excerpt needed for audit, comply with copyright limits, and redact secrets, personal data, account identifiers, and sensitive prompt content.

`related_claim_ids` must contain only `claim_id` values from existing `evidence[]` records. Use it to link a `stale_input` gap to the stale evidence record. For a missing or unsupported claim with no evidence record, leave `related_claim_ids` empty and describe the gap; never invent a claim ID.

`related_observation_ids` is optional and must contain only `observation_id` values from existing `competitor_observations[]` records. Use it to link a `stale_input` gap to a competitor observation older than 14 days; never invent an observation ID.

## Source order

Prefer current primary platform documentation and standards, then reproducible direct observations, then original research. Use secondary sources to locate primary material or as explicitly labeled context.

## Freshness

- Re-check `vendor_documentation` and `secondary_context` evidence after 30 days.
- Expire `direct_observation` evidence and competitor observations as current evidence after 14 days.
- Re-check `standard` evidence after 90 days or a version change.
- Re-check `original_research` evidence after 365 days for correction, retraction, or stronger replication before proposing a new experiment.
- Verify legal, policy, terms, and access constraints on the day an automated collection method is proposed.

Keep expired records as historical evidence, add a `stale_input` gap linked through `related_claim_ids` or `related_observation_ids`, and do not use them for a current factual claim until refreshed.
