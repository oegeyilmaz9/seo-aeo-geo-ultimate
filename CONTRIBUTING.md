# Contributing

## Ground rules

1. Preserve the distinction between observation, vendor guidance, experiment, and speculation.
2. Do not add a platform-specific rule without a current primary source or a clearly labelled evidence gap.
3. Do not add ranking, citation, retrieval, traffic, revenue, or conversion guarantees.
4. Do not introduce universal scores, fixed word/keyword/passage formulas, blanket crawler rules, or required `llms.txt` behavior.
5. Keep implementation separate from approval and measurement separate from causal attribution.

## Skill changes

- Keep `SKILL.md` below 500 lines, with correct frontmatter and no scaffold text.
- Add a narrow reference document only when it materially improves execution; do not add copied vendor documentation.
- Preserve local links and the `agents/openai.yaml` invocation for the skill.
- Update `manifests/suite.json` when adding/removing a skill or formal contract.
- Use `$seo-action-plan` for evidence-linked multi-owner execution handoffs and `$optimise-seo` only for explicitly authorized implementation.
- Conventional SEO handoffs use a validated `seo-findings.json` bundle with immutable raw evidence; AEO/GEO handoffs use their validated `optimization-brief.json` bundles. Do not substitute one artifact for the other.

## Evidence and source changes

- Add/update entries in `docs/research/*-source-registry.json` with source type, URL, observed date, scope, and design effect.
- Refresh sources according to the registry policy before a release. Never update `observed_at` without re-checking the source.
- Prefer official documentation, standards, first-party reporting, and original research. Mark market/vendor method references as secondary context.

## Validation

Run the generated-contract check, suite validator, relevant artifact validators, and the full test suite. Add a failing/abuse case whenever a new guardrail or artifact invariant is introduced.

```powershell
python scripts/sync_contracts.py --check
python scripts/validate_suite.py --as-of YYYY-MM-DD
python scripts/run_tests.py
```

When a canonical schema changes, regenerate every checked-in contract copy with:

```powershell
python scripts/sync_contracts.py
```

## Pull requests

Explain the user-facing behavior, evidence basis, compatibility impact, validation run, and any source refresh. Keep unrelated changes out of the same pull request.
