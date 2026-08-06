# Action-plan protocol

## Intended use

`action-plan.json` is an approval and handoff artifact. It converts a validated AEO/GEO optimization brief or conventional `seo-findings.json` bundle into discrete actions without changing the source site. It is deliberately not a backlog export, a universal SEO score, or proof that a platform will retrieve, cite, rank, or recommend a page.

The artifact is valid only with immutable upstream input bundles under `inputs/`. An AEO/GEO input bundle contains the original `optimization-brief.json`, `research-pack.json`, captures, metadata, and raw evidence required by its producer’s validator. A conventional SEO input bundle contains the original `seo-findings.json` and every `raw_evidence_ref` named by it.

## Bundle shape

```text
action-plan-bundle/
  action-plan.json
  inputs/
    aeo-homepage/
      optimization-brief.json
      research-pack.json
      raw/...
    technical-homepage/
      seo-findings.json
      raw/...
```

`input_briefs[].bundle_ref`, `input_findings[].bundle_ref`, and their `artifact_ref` values are relative to the action-plan bundle. They cannot escape it or traverse a symbolic link/reparse point. The validator hashes each artifact, resolves its input bundle, and reruns its declared upstream validator. A plan using `input_findings` must use schema version `1.1.0`; a brief-only `1.0.0` plan remains supported.

## Required action logic

Every action must carry all of the following.

| Field | Requirement |
| --- | --- |
| `finding_refs` | At least one finding from one input brief or SEO finding set. |
| `evidence_refs` | At least one resolving evidence record; it must overlap a linked finding’s evidence. |
| `owner` | A real responsible team/role and a distinct approval role. The planner cannot own implementation. |
| `execution_outline` | Concrete, bounded steps. State what will not be changed where ambiguity matters. |
| `acceptance_criteria` | Reviewable conditions, not uplift or citation promises. |
| `verification` | A method, source-specific metric type, success condition, and guardrail. |
| `rollback` | A required/reversible path for potentially harmful change. |
| `claim_boundary` | A scope note plus `no_guarantee: true`. |

Use `confidence: high` only when all linked finding and evidence classifications are `confirmed`. `medium` is allowed only with `confirmed` or `vendor-recommended` support. `low` is limited to an explicitly monitored experiment and stays pending approval. No action can be based on a speculative finding or evidence item.

## Priority and risk

`now` means an approved, evidence-backed action with an owner, acceptance criteria, and rollback. `next` is similarly actionable but sequenced behind `now`. `later` is valid but should name the dependency or missing decision. `do-not-do` belongs in `declined_actions`, not `actions`.

Risk is operational risk, not a prediction of search impact. Set `high` for crawler policy, indexing, legal, privacy, accessibility, experiment-wide, or irreversible changes. A high-risk action needs an explicit rollback method and an appropriate approval role.

## Measurement rules

Choose the metric that actually observes the proposed outcome:

- `recrawl` for rendered/discovery verification;
- `manual-review` for factual, editorial, or accessibility acceptance;
- `search-console` for Google Search reporting;
- `analytics` for referral or conversion events;
- `visibility-run` for a frozen prompt/corpus observation run;
- `log-review` for crawler requests only.

Keep these measures separate. For example, a bot request can support `log-review`, but it cannot establish a citation or referral result. A visibility run is observational and needs comparable repeated samples before describing drift.

## Declining a request

Add a `declined_actions` entry when a requested change would make an unsupported platform claim, rely on stale/absent evidence, create policy/legal/accessibility risk, or confound measurement. Explain the reason and name what evidence or approval would be necessary to revisit it.

## Review gate

The generated plan always starts `approval.status: pending`. A human reviewer can approve implementation outside this skill. Rerun validation after any plan or input-bundle change; validation confirms artifact integrity and traceability, not business approval or platform behavior.
