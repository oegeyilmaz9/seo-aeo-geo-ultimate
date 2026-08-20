# Decision and release contract

Use this contract when evidence has identified a real choice and the work may continue beyond a local patch. It keeps product intent, implementation, delivery, provider operations, and delayed search outcomes from collapsing into one status.

## Minimum decision record

Record the decision owner, target and bounded scope, current evidence, desired end state, affected surfaces, acceptance criteria, rollback, and the current authorization state for implementation, deployment, and provider mutation. Reuse a goal, issue, or approved Action Plan when it already contains those fields. Otherwise create a short `decision-record.md`; do not require a redundant immutable bundle merely to repeat a complete decision.

An explicit product-owner end state is a constraint. A preference for the smallest reversible change controls implementation breadth inside that end state; it must not silently replace the approved end state with a smaller one. For a whole-corpus decision, state the corpus identity and the canonical/duplicate/safety constraints that still apply.

## Independent authorization phases

Treat these as separate grants:

1. **Implementation:** change the named local files, content, or configuration.
2. **Release:** deploy the identified candidate or publish the approved content.
3. **Provider operation:** mutate a named external search or discovery property, such as submitting a sitemap or changed URL set.

Authorization for one phase does not imply either later phase. When a later authorization arrives, resume the same decision chain and candidate identity instead of restarting the audit or substituting a new candidate. Record the exact blocker when a phase is not authorized.

## Status model

Always keep these states distinct:

- `implemented-locally`: the candidate passed its declared local acceptance gate;
- `delivered-and-verified`: the exact candidate was released and its affected live universe passed scope-matched verification;
- `provider-outcome-pending` or `provider-outcome-observed`: a crawl, index, serving, citation, referral, or other provider result remains pending until separately observed.

A deployment receipt proves delivery, not indexing. A successful sitemap or URL-submission receipt proves the provider accepted a request, not that it crawled, indexed, ranked, retrieved, cited, or referred the target.

## Required closeout links

Link the decision record to the implementation receipt, candidate manifest, deployment/live-verification report when present, provider-operation receipt when present, and the scheduled comparison or follow-up owner. Preserve failures and pending outcomes; do not rewrite them as success.
