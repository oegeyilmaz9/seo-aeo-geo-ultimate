# Autonomous orchestration contract

Use this contract for every request entering through `seo`. The router is the user-facing owner of the complete task, not a menu or a dispatcher that asks the user to coordinate specialists.

## User contract

The user may describe the outcome in ordinary language. They do not need to know:

- whether the work is SEO, AEO, GEO, AI-search, technical, content, authority, or measurement;
- which specialist skill should run;
- which artifact, schema, validator, phase order, or handoff is required; or
- which specialist should receive the next intermediate result.

Translate plain-language goals into the internal task graph. Do not ask “Which skill should I use?”, “Do you want AEO or GEO?”, or “Which artifact should I create?”. Ask only for a non-discoverable product/business decision, inaccessible credential or dataset, material scope choice, cost-bearing action, or authorization that would change what may safely happen. Phrase those questions in product language rather than suite jargon.

## Coverage before execution

Create an internal coverage ledger for all 27 suite skills. Screening every capability is mandatory; executing every capability is not. Give each row one state:

- `required`: evidence indicates the lane is part of the requested outcome;
- `active`: the router is currently executing or delegating the lane;
- `completed`: the lane produced its required evidence, decision, change, or verified limitation;
- `not-applicable`: observed scope makes the lane irrelevant, with a short reason;
- `blocked`: a named external input, access grant, owner choice, or authorization is missing;
- `deferred-by-owner`: the user or accountable owner explicitly chose not to pursue it.

Never use `not-applicable` merely because a lane was forgotten, unfamiliar, difficult, or lacks easy tooling. Never use `blocked` while safe read-only work, a documented fallback, or another independent lane can still progress. For a narrow request, keep the ledger internal unless an excluded/blocked lane affects the answer. For a broad or end-to-end request, include a compact coverage summary in the final response.

When Python 3.11+ is available, broad and end-to-end work must use the manifest-derived initializer and validator documented in [Autonomous Orchestration](../../../docs/AUTONOMOUS-ORCHESTRATION.md). The generated draft is intentionally invalid until every current manifest skill is assessed. Validation is a closeout gate: it prevents a forgotten, duplicated, invented, still-active, or unsupported lane from being presented as complete. The ledger is orchestration evidence, not a ranking score or outcome guarantee.

## Complete 27-skill screen

| Group | Skill | Require when the observed request/scope includes |
| --- | --- | --- |
| Coordination | `seo` | Every suite request; owns intake, coverage, task graph, handoffs, synthesis, and completion |
| Conventional research | `seo-research` | Search intent, query families, demand, competitors, page ownership, gaps, or keyword ambition |
| AI-search research | `ai-search-research` | Engine/surface-specific AI evidence, prompts, sources, ground truth, or formal research provenance |
| Conventional measurement | `seo-performance` | Search Console/Bing/analytics/log/indexation/CWV baselines, comparisons, experiments, or authorized provider operations |
| AI visibility measurement | `ai-visibility-monitor` | Repeated AI answers, mentions, citations, consulted sources, referrals, uncertainty, or drift |
| Broad audit | `seo-audit` | Multi-lane site assessment or a request whose defects are not yet localized |
| Page review | `seo-page` | Page contract, on-page alignment, title/meta/H1, query fit, or mixed page concerns |
| Technical | `seo-technical` | Crawl, render, index, directives, canonical, headers, performance, migration/recovery, favicon, platform controls, or optional `llms.txt` |
| Content | `seo-content` | Helpful content, editorial depth, factual support, E-E-A-T, snippet copy, or remediation |
| Structured data | `seo-schema` | Entity/page facts need detection, validation, or truthful Schema.org output |
| Images | `seo-images` | Image accessibility, discovery, delivery, licensing, dimensions, formats, or CLS |
| Sitemaps | `seo-sitemap` | XML inventory, discovery surfaces, `lastmod`, segmentation, or sitemap generation |
| International | `seo-hreflang` | Multiple languages/regions, locale URLs, alternates, or international targeting |
| Architecture | `seo-architecture` | Navigation, hubs, crawl paths, internal links, taxonomy, facets, pagination, or orphan evidence |
| Authority | `seo-authority` | Backlinks, referring sources, citations, mentions, linkable evidence, digital PR, or link risk |
| Answer readiness | `seo-aeo` | Direct-answer clarity, completeness, intent coverage, extractability, or answer structure |
| Entity/citation readiness | `seo-geo` | Entity consistency, claim-source traceability, citation suitability, or documented engine controls |
| Commerce | `seo-commerce` | Products/categories, merchant feeds, availability/price parity, shopping discovery, or commerce protocols |
| Local | `seo-local` | Locations, profiles, NAP/hours/categories, service areas, reviews, or local intent |
| Video | `seo-video` | Watch pages, players, VideoObject, thumbnails, transcripts, Key Moments, or video indexing |
| News/Discover | `seo-news-discover` | Publisher policy, article provenance, dates/bylines/corrections, feeds, paywalls, or freshness |
| Agentic journeys | `seo-agentic` | Agent perception, accessibility/UI state, safe task completion, forms, consent, or documented agent protocols |
| Programmatic | `seo-programmatic` | Template/data-driven page systems, scaled quality, rollout, or index-state control |
| Competitor pages | `seo-competitor-pages` | Comparison, alternative, “vs”, or roundup pages and attributable competitor claims |
| Roadmap | `seo-plan` | Validated work needs sequencing across owners, dependencies, capacity, and review gates |
| Action planning | `seo-action-plan` | Findings need approval-ready scope, ownership, acceptance, risk, verification, and rollback |
| Implementation/release | `optimise-seo` | A bounded approved change, local acceptance, authorized release, or coordinated live closeout |

## Execution loop

1. **Normalize the outcome.** Infer the requested end state, audience, market/locale, site or repository scope, and whether the user asked for advice, diagnosis, planning, implementation, release, measurement, or an end-to-end result. Preserve explicit ambitions such as high-volume category leadership.
2. **Discover before asking.** Inspect the supplied site, repository, captures, configuration, and authorized data sources. Infer discoverable facts. Record missing optional evidence as a limitation and continue.
3. **Build the coverage ledger.** Screen all 27 rows and construct a dependency graph. A broad goal normally activates research, audit, conventional measurement when data exists, page/content/technical/architecture/authority review, applicable verticals, planning, and the authorized implementation chain. AEO/GEO/AI measurement activate from the requested discovery surfaces and available evidence, not from the user's knowledge of their names.
4. **Load specialist instructions internally.** Before executing a required lane, read that specialist's complete `SKILL.md` and only the references needed for the lane. In Codex the skills are sibling folders; in Claude Code they are below `${CLAUDE_PLUGIN_ROOT}/skills/`. The user must not be asked to invoke the next specialist manually.
5. **Execute and relay.** Run required lanes in dependency order and parallelize only independent work when the runtime permits it. Pass validated artifacts, raw evidence, scope, limitations, and owner decisions directly to the next lane. Do not make the user copy intermediate prompts or translate specialist terminology.
6. **Reconcile.** Resolve duplicate findings, preserve genuine disagreements, keep unlike metrics separate, and route each accepted issue to one canonical owner. A specialist's output is an input to the router, not a separate final answer the user must assemble.
7. **Continue to the authorized boundary.** Complete every safe read-only, local, and explicitly authorized action while useful work remains. Pause only for a material product choice, unavailable required access/data, cost-bearing/external coordination, or a separately required implementation, release, or provider-mutation authorization. State the exact boundary and keep independent lanes moving.
8. **Close as one system.** Verify the requested end state, validators, affected scope, and outstanding provider lag. Return one consolidated answer: outcome, important evidence, changes/plan, coverage summary for broad work, unresolved blockers, and the next externally owned decision. Do not dump 27 disconnected reports.

## Completion bar

The router is complete only when one of these is true:

- the user's requested outcome is delivered and verified to the authorized boundary;
- every applicable lane is completed and only separately owned provider outcomes remain pending; or
- a material blocker is named with its owner, required input/authorization, affected lanes, and all safe independent work already completed.

Routing to a specialist is not completion. Producing an audit when the user asked for an approved implementation is not completion. A partial lane result cannot silently narrow an explicit end-to-end request.
