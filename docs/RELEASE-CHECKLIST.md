# Release checklist

## Source and behavior

- [ ] Refresh the source registry against the release date and resolve every stale entry.
- [ ] Re-read all platform-specific statements changed in this release against primary sources.
- [ ] Confirm no new universal score, forced `llms.txt`, blanket crawler instruction, or outcome guarantee was introduced.
- [ ] Confirm content/implementation proposals remain evidence-, owner-, approval-, verification-, and rollback-aware.
- [ ] Validate any changed `seo-findings.json` and `action-plan.json` fixtures; confirm conventional findings retain raw evidence and AEO/GEO brief-only plans remain compatible.

## Validation

- [ ] Run `python scripts/sync_contracts.py --check` and resolve all generated-contract drift.
- [ ] Run `python scripts/validate_suite.py --as-of YYYY-MM-DD`.
- [ ] Run all relevant artifact validators.
- [ ] Run `python scripts/run_tests.py` (the suite intentionally isolates same-named test modules).
- [ ] Run installer tests and a non-production `--dry-run`.
- [ ] Review a clean source tree for unexpected artifacts, secrets, personal data, or copyrighted captures.

## Publication gate

- [ ] Confirm the Apache-2.0 `LICENSE` and `NOTICE` are accurate for the release.
- [ ] Confirm repository name, visibility, GitHub owner/organization, default branch, and issue/security contact.
- [ ] Confirm the README clone URL, workflow badge, and public schema namespace match the intended repository.
- [ ] Add release notes and version tag.
- [ ] Create the remote repository only after the preceding items are complete.
