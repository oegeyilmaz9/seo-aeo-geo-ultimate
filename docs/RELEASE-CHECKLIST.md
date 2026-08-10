# Release checklist

## Source and behavior

- [ ] Refresh the source registry against the release date and resolve every stale entry.
- [ ] Re-read all platform-specific statements changed in this release against primary sources.
- [ ] Confirm no new universal score, forced `llms.txt`, blanket crawler instruction, or outcome guarantee was introduced.
- [ ] Confirm content/implementation proposals remain evidence-, owner-, approval-, verification-, and rollback-aware.
- [ ] Validate any changed `seo-findings.json` and `action-plan.json` fixtures; confirm conventional findings retain raw evidence and AEO/GEO brief-only plans remain compatible.
- [ ] Review `manifests/platform-controls.json` against current primary documentation and resolve expired review windows, changed feature states, and undocumented crawler assumptions.
- [ ] Confirm Query Corpus demand values have dated provenance and that executed subqueries are observations, not inferred engine behavior.

## Validation

- [ ] Run `python scripts/sync_contracts.py --check` and resolve all generated-contract drift.
- [ ] Run `python scripts/validate_suite.py --as-of YYYY-MM-DD`.
- [ ] Run `python scripts/validate_llms_txt.py validate-file llms.txt`; after publication, also run it with `--check-live` and confirm every linked public resource still exists and remains appropriate.
- [ ] Run `python scripts/validate_claude_plugin.py`; when Claude Code is available, also run `claude plugin validate .`.
- [ ] Run all relevant artifact validators.
- [ ] Validate representative `query-corpus.json`, `seo-performance-run.json`, `visibility-run.json`, `site-graph.json`, and `platform-controls.json` fixtures when their contracts change.
- [ ] Run `python scripts/run_tests.py` (the suite intentionally isolates same-named test modules).
- [ ] Run artifact scaffold, migration, renderer, data-import, and sanitized example tests.
- [ ] Run installer tests, a non-production `--dry-run`, a temporary install, and `python scripts/install_runtime.py --verify` against that temporary state.
- [ ] Review a clean source tree for unexpected artifacts, secrets, personal data, or copyrighted captures.

## Publication gate

- [ ] Confirm the Apache-2.0 `LICENSE` and `NOTICE` are accurate for the release.
- [ ] Confirm repository name, visibility, GitHub owner/organization, default branch, and issue/security contact.
- [ ] Confirm the README clone URL, workflow badge, and public schema namespace match the intended repository.
- [ ] Confirm the Claude plugin manifest, developer marketplace catalog, version, repository URL, and submission copy match the intended public release.
- [ ] Commit the audited candidate, add the annotated version tag, and prepare release notes from `CHANGELOG.md`.
- [ ] Push the release commit and tag only after the preceding items are complete; wait for the matching GitHub Actions run to pass.
- [ ] Run the live `llms.txt` link check against the published commit, verify the GitHub release/tag SHA, then install and `--verify` the local Codex runtime package.
