# Verification modes

Choose the least expensive mode that still covers the approved acceptance criteria. The mode changes execution timing, not the required evidence.

## Per-action

Run the narrow relevant check after each action when failures would contaminate later work, the change is high risk, or the actions affect independent systems. Record each attempt and result.

## Batch-final

Use for a coherent batch whose intermediate states do not need independent acceptance. Accumulate every action's acceptance criteria, then run one complete final gate over the candidate: applicable lint, tests, build, raw/rendered checks, search/static checks, corpus checks, and goal-specific assertions. If the gate fails, fix the candidate and rerun the complete gate. Report every attempt honestly; a later pass does not erase earlier failures.

## Production comparison

Use only after separately authorized release. Verify the exact deployed candidate, alias or deployment ID, and the full affected live universe. Keep delivery verification separate from provider outcomes and delayed performance/visibility comparisons.

The approved scope controls the verification universe. A single-page edit can use a targeted check. A shared template or resolver requires the affected route class. A sitemap, canonical policy, redirect map, or corpus-wide indexability change requires the full declared corpus or a justified closed population.
