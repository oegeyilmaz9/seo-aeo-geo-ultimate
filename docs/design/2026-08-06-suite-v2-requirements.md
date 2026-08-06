# SEO / AEO / GEO suite — 2026-08-06 design record

> **Status:** retained design context, not a feature inventory. The public
> suite ships `research-pack.json`, `optimization-brief.json`,
> `seo-findings.json`, `visibility-run.json`, and `action-plan.json`.
> `measurement-plan.json` and `content-brief.json` below were explored as
> future concepts and are not shipped contracts or runtime capabilities.

## Product contract

The suite is an evidence-backed operating system for search, AI-search
readiness, content recommendations, implementation planning, and observational
measurement. It is not a collection of ranking hacks, a crawler bypass tool, or
a promise that a page will be cited.

Every user-facing conclusion must identify:

1. the decision or recommendation;
2. the precise engine, surface, locale, and target scope, if applicable;
3. its evidence classification and freshness;
4. the action owner and approval boundary;
5. an observable verification method;
6. the limitations and uncertainty that prevent a stronger claim.

## Required capability lanes

| Lane | Owns | Must not do |
|---|---|---|
| seo | Route the smallest valid workflow and reconcile artifacts. | Invent findings or merge unlike measurements. |
| ai-search-research | Research Pack, query corpus design, source/entity landscape, gaps. | Rewrite pages, edit code, or claim live visibility. |
| seo-aeo | Direct-answer completeness, intent coverage, clarity, visible-content support. | Research, implementation, or citation guarantees. |
| seo-geo | Entity consistency, evidence traceability, citation suitability, documented engine controls. | Predict citations or recommend a generic crawler policy. |
| ai-visibility-monitor | Frozen-corpus observations, first-party metric imports, comparability, uncertainty, drift. | Attribute a change to an intervention. |
| seo-action-plan | Evidence-linked content/technical/schema/locale/measurement action briefs. | Make unapproved changes or turn experimental evidence into a required change. |
| seo-content | Editorial audit, content brief, and approved rewrite options. | Create unsupported claims or formulaic filler. |
| seo-technical | Crawl/index/render/canonical/robot/headers/performance evidence and implementation advice. | Change production controls without an explicit owner and approval. |
| seo-schema | Visible-content-aligned structured-data validation and generation. | Promise rich results, ranking, or AI inclusion. |
| seo-hreflang | Locale URL maps and international annotation validation. | Translate or infer locale intent. |
| seo-sitemap | URL inventory and sitemap validation/generation. | Treat sitemap inclusion as indexing assurance. |
| seo-images | Image discoverability, accessibility, rendering, and performance recommendations. | Force keywords into alt text. |
| seo-page | A bounded mixed page assessment. | Calculate an overall score or replace a full audit. |
| seo-audit | Bounded multi-lane site audit with evidence collection plan. | Crawl beyond authorization or claim unavailable measurements. |
| seo-plan | Sequenced strategy and backlog. | Substitute a plan for validated findings. |
| seo-programmatic | Data/template quality gates and index-bloat safeguards. | Approve scaled generation without unique user value. |
| seo-competitor-pages | Fair, sourced comparison-page briefs. | Invent competitor facts, ratings, or pricing. |
| seo-research | Conventional SEO/SERP research and intent mapping. | Pretend paid data or live SERP access exists when it does not. |
| optimise-seo | Approved implementation for supported application scopes. | Make unrelated visual or legal changes. |

## Artifact contract direction

The shipped immutable artifacts are:

- research-pack.json
- optimization-brief.json with an aeo or geo domain
- seo-findings.json for conventional SEO handoffs
- visibility-run.json
- action-plan.json

The following concepts were retained as design inputs only; they are **not**
part of the public artifact registry:

- measurement-plan.json: frozen corpus, collection profiles, replicate policy,
  metrics, report imports, comparability and uncertainty settings.
- action-plan.json: recommendations created from validated findings, each with
  owner, evidence, risk, approval, verification, rollback, and optional content
  brief reference.
- content-brief.json: an editorial plan with audience/job, evidence and
  claim ledger, answer structure, differentiation, locale, media and
  accessibility requirements, CTA constraints, and review gates.

Schemas must reject unknown authority references, absolute artifact paths,
unresolved hashes, stale mandatory evidence, duplicate IDs, and an
implementation recommendation without one approved owner.

## Measurement architecture

Research Pack plus frozen corpus flows to:

1. observed answer captures, with optional repeated samples, yielding mentions,
   visible citations, and answer accuracy;
2. potential verified Google Search Console imports, if a user authorizes a
   future connector and the relevant report is available;
3. potential verified Bing or Clarity imports, if a user authorizes a future
   connector and the platform provides the data;
4. verified server/CDN bot-log evidence, yielding requests only and never inferred
   citations.

All metric families remain separate and are compared only like-for-like.

## Recommendation quality bar

A recommendation may say:

Add a visible, dated definition for the product term and link it to the
verified specification. This addresses an AEO finding for an English buyer-intent
query family. Seo-content owns the editorial change; an editor must approve it.
Recheck target capture, schema/visible-content alignment, and the next
comparable visibility run. The expected outcome is clearer answer support;
citation uplift is not promised.

It may not say:

Add 800 words, an FAQ schema block, and allow all AI bots to get cited by
ChatGPT.

## Source and release governance

- Registry entries expire according to their source class.
- Vendor documentation and policy changes are rechecked before a relevant
  implementation or release.
- Every engine-control rule records a source URL, verification date, exact bot,
  purpose, security owner, and approved change record.
- Tests include normal, missing evidence, ambiguous scope, stale source,
  platform policy, and shortcut-pressure cases.
- CI validates generated contract copies, suite structure, source freshness,
  and isolated regression tests. It does not collect live platform data or run
  authenticated integrations.
