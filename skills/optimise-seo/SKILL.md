---
name: optimise-seo
description: Use when explicitly authorized to implement a bounded, approved SEO action in a codebase or content system, verify the exact change, and report its limitations; do not use for broad audits, self-approved production changes, or outcome guarantees.
---

# SEO Implementation Coordinator

## Purpose

Apply or prepare a specific, user-authorized SEO change after its evidence, owner, scope, acceptance criteria, verification, and rollback are known. This skill is the bridge from an approved `$seo-action-plan` item to a verifiable local implementation; it is not an audit, an auto-publisher, or a deployment authority.

Read `references/implementation-gate.md` before modifying a workspace.

## Authorization gate

Require all of the following before changing files or systems:

- explicit user/authorized-owner request to implement the named action;
- validated upstream finding/action plan or equivalent evidence record;
- exact target repository/content system and permitted scope;
- owner, acceptance criteria, verification plan, risk, and rollback;
- facts/copy/schema/data approved for the target locale.

If any is missing, prepare an implementation plan or patch proposal only. Do not infer approval from an audit result, a pending action-plan artifact, a backlog item, or the desire to “improve SEO.”

## Implementation workflow

1. **Reconfirm scope.** Quote the action ID/objective, target files/URLs, intended behavior, non-goals, and success/guardrail conditions. Inspect the current state; preserve unrelated work.
2. **Choose the owning lane.** Content edits follow `$seo-content`; technical changes follow `$seo-technical`; markup follows `$seo-schema`; locale annotations follow `$seo-hreflang`; sitemap changes follow `$seo-sitemap`. Do not silently substitute a different change.
3. **Make the smallest reversible change.** Modify only the approved files/data. Preserve facts, locale, consent/accessibility, analytics, and security behavior. Do not add `llms.txt`, crawler directives, schema, pages, links, or copy merely because they sound SEO-related.
4. **Verify the implementation.** Run relevant local tests/builds and inspect the rendered/delivered outcome where possible. Check the declared acceptance criteria and guardrail; record what was not verified locally.
5. **Prepare handoff.** Report changed files, exact behavior, tests/evidence, remaining external checks, rollback, and comparison-measurement prerequisites. Do not deploy, submit URLs, change third-party settings, or claim production success unless separately authorized and actually completed.

## Guardrails

- Never promise crawl, index, rank, citation, traffic, revenue, or conversion results.
- Do not expand the task from one approved action into a broad “fix everything” change.
- Do not overwrite unrelated user work, secrets, configurations, or analytics data.
- Treat crawler policies, canonicals, robots/noindex, redirects, privacy/security, pricing, health/legal/financial claims, and localization as high-risk changes needing explicit review and rollback.

## Output

Return an implementation receipt: action/evidence reference, files/systems changed, acceptance verification, test results, external/production checks still required, known limitations, and rollback. If no implementation was authorized, return a reviewable plan rather than making changes.
