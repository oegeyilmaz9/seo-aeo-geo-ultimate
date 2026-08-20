# Editorial readiness versus indexability

Model two independent axes for every scaled record or page family.

## Editorial readiness

Record whether the visible experience has the required facts, useful task completion, locale quality, media, review state, and data freshness. Values may be ready, needs-review, incomplete, or withheld.

## Search status

Separately record the product-owned search intent: indexable canonical owner, redirecting duplicate/source, intentionally noindex, unavailable, or undecided. Never derive this field from an editorial flag alone.

`noindex` remains valid when an explicit product policy or concrete risk evidence supports it. A sparse or unreviewed editorial state does not itself authorize `noindex`, and a “real record” label does not itself require indexing. For a unique canonical-owner page, follow the explicit indexing decision unless a canonical, duplicate, safety, legal, privacy, or access constraint contradicts it. Route an owner-linked duplicate source to its declared canonical owner with an approved redirect when that is the product contract.

A product owner may explicitly choose a whole-corpus end state. Apply that decision across the declared corpus while retaining the canonical-owner map, duplicate handling, safety constraints, and exceptions; do not shrink it merely because a staged rollout would normally be preferred.
