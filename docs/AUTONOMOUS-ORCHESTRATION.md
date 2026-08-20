# Autonomous orchestration

`seo` is the single user-facing entry point for the suite. A user can describe the outcome in ordinary language; the router determines which SEO, AEO, GEO, AI-search, measurement, planning, implementation, release, and provider-operation capabilities apply.

The router screens every skill but loads and executes only the applicable specialist workflows. This keeps the coverage complete without forcing all 27 full instruction sets into context at once. Direct specialist invocation remains available for expert users.

## Coverage ledger

For broad or end-to-end work, the router can create a machine-checkable ledger from the installed manifest:

```powershell
python "<suite-root>/scripts/manage_orchestration_ledger.py" init `
  --output work/seo/orchestration-ledger.json `
  --request "Improve organic and AI-search visibility end to end" `
  --mode end-to-end `
  --authorized-boundary "Research, audit, plan, and local implementation"
```

The generated file is deliberately unassessed. The router must inspect the real request and scope, then classify every current suite skill as `required`, `active`, `completed`, `not-applicable`, `blocked`, or `deferred-by-owner`. Every row needs a reason; completed work needs an evidence or output reference; blockers and owner deferrals need their own records.

Validate the completed ledger before broad closeout:

```powershell
python "<suite-root>/scripts/manage_orchestration_ledger.py" validate work/seo/orchestration-ledger.json
```

The validator derives the required skill inventory from `manifests/suite.json`. It rejects missing, duplicate, invented, or unfinished lanes; stale suite versions; unsupported terminal states; ungrounded completion; unsafe references; and broad closeouts without a coverage summary. It proves workflow coverage and record consistency, not that search engines will rank, index, retrieve, cite, or convert.

## Runtime path

Let `<suite-root>` mean `${CLAUDE_PLUGIN_ROOT}` in Claude Code. In Codex, read `.seo-suite-runtime.json` beside the installed `seo/SKILL.md` when present and use its `suite_root`; from a source checkout, use the repository root.

Python 3.11 or later is required for the executable ledger check. If Python is unavailable, the router still performs the screen internally and labels a broad coverage handoff provisional until validation can run.
