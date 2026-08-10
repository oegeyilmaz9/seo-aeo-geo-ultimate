# SEO routing matrix

## Universal entry point

Use `seo` as the recommended first call for any SEO, AEO, GEO, or AI-search request. It accepts a narrow task as well as a cross-functional brief, then selects the smallest correct specialist lane and preserves the handoff. A user may still call a known specialist directly, but they never need to know the internal map to get started.

| User intent | Primary owner | Required upstream | Downstream |
|---|---|---|---|
| Build current AI-search evidence | `ai-search-research` | Authorized inputs | AEO, GEO, monitor |
| Audit answer readiness | `seo-aeo` | Research Pack + captures | Validated AEO finding |
| Turn validated findings into an execution plan | `seo-action-plan` | Validated Optimization Brief + preserved input bundle | Approval-ready Action Plan |
| Rewrite or implement an answer change | Exact approved action owner | Validated Action Plan item | QA + comparison measurement |
| Audit entity/source/citation readiness | `seo-geo` | Research Pack + captures/observations | Content/schema/technical implementation |
| Measure mentions, citations, accuracy, referrals, drift | `ai-visibility-monitor` | Research Pack + frozen corpus | Later audit or strategy |
| Measure GSC/Bing/analytics/indexation/CWV performance | `seo-performance` | Authorized first-party export + optional Query Corpus | Later audit or strategy |
| Normalize an authorized GSC, Bing, organic GA4, crawler CSV, or server log | `seo-performance`, `seo-architecture`, or `seo-technical` by evidence type | Original export/log + declared property/window/privacy scope | Evidence input; then the owning formal validator |
| Audit ecommerce pages, feeds, parity, freshness, or commerce protocols | `seo-commerce` | Product/feed captures + current platform controls | Schema/technical/content/action plan |
| Audit locations, profiles, NAP, local pages, reviews, or local query intent | `seo-local` | Authorized profile/location facts + Query Corpus | Schema/content/technical/action plan |
| Audit video pages, players, metadata, sitemaps, captions, or indexing | `seo-video` | Video/page/report captures | Schema/media/technical/action plan |
| Audit publisher policy, articles, news/Discover freshness, or feeds | `seo-news-discover` | Publisher/article/report evidence | Content/schema/media/technical/action plan |
| Audit safe agent perception, state, task completion, or capabilities | `seo-agentic` | Authorized task + DOM/accessibility/render evidence | Accessibility/technical/commerce action |
| Build/audit site graph, navigation, taxonomy, facets, or internal links | `seo-architecture` | Bounded graph captures + optional Query Corpus | Technical/content/programmatic action |
| Audit backlinks, mentions, source landscape, or link risk | `seo-authority` | Authorized/public link and mention evidence | GEO/content/architecture/action plan |
| Full site audit | `seo-audit` | Crawl/site scope | Specialist remediation |
| One-page mixed audit | `seo-page` | Page capture | Specialist remediation |
| Crawl/index/render/performance | `seo-technical` | Technical evidence | Implementation |
| Site migration or replatforming | `seo-technical` | Old/new inventory, URL map, baselines, launch and rollback owners | `seo-action-plan`, then `seo-performance` follow-up |
| Sudden traffic/indexation incident | `seo-technical` | Last-known-good state, affected segments, change timeline, reporting checks | Exact remediation owner and comparable measurement |
| Manual action or hacked-site recovery | `seo-technical` with security/legal owner as applicable | Authorized report, affected scope, incident evidence | Verified remediation, review request, monitoring |
| Controlled SEO experiment | `seo-performance` | Predeclared hypothesis/cohort/outcome/guardrails and baseline | `seo-action-plan`, exposure QA, comparable result |
| Editorial/content quality | `seo-content` | Content set | Content implementation |
| Structured data | `seo-schema` | Page/entity facts | Schema implementation |
| Sitemaps | `seo-sitemap` | URL inventory | Technical implementation |
| Images | `seo-images` | Media inventory | Media implementation |
| International SEO | `seo-hreflang` | Locale/URL map | Technical implementation |
| Strategy/roadmap | `seo-plan` | Validated findings | Sequenced execution |
| Large-scale page systems | `seo-programmatic` | Template/data rules | Implementation + QA |
| Optional `llms.txt` suitability, generation, validation, publishing, or maintenance | `seo-technical` | Canonical public sources, content scope, refresh path, and maintenance owner | Validated `/llms.txt` or a documented decision not to publish |

## Ambiguity resolution

- "Make us show up in ChatGPT" is not an implementation order. Route first to research, then GEO/AEO audit, baseline measurement where tracking is requested, action planning, and only then approved implementation.
- "Audit this answer" routes to `seo-aeo` when the supplied target is a direct-answer surface.
- "Optimize this answer" is ambiguous: audit with `seo-aeo` if no validated AEO finding exists; otherwise create an `seo-action-plan` and route rewrite or implementation to its exact approved owner. Canonical owners are `seo-content`, `seo-schema`, `seo-technical`, `seo-hreflang`, `seo-commerce`, `seo-local`, `seo-video`, `seo-news-discover`, `seo-agentic`, `seo-architecture`, `seo-authority`, `seo-performance`, and `optimise-seo`. `seo-aeo` does not rewrite or approve implementation.
- "Track whether it worked" routes to the monitor and must not imply causation.
- "Track whether organic search changed" routes to `seo-performance`; "track whether AI answers changed" routes to `ai-visibility-monitor`. A compound report preserves both metric families instead of creating a blended score.
- "Should we publish an llms.txt?" routes to `seo-technical`. Recommend and generate it when truthful public sources and an owner make upkeep reliable, even if adoption is still a future-readiness bet. It is never a universal visibility prescription.
- "Fix everything" begins with scope and evidence, then bounded specialist lanes; it is not permission for unrelated changes.

## Artifact discipline

Research Pack provenance remains immutable. Query Corpora preserve user needs, observed queries, prompts, disclosed subqueries, demand provenance, and page coverage. AEO/GEO Optimization Briefs and SEO Findings record audit findings and candidate owners. Site Graphs preserve captured architecture. SEO Performance Runs and Visibility Runs preserve unlike observational metric families. Platform Controls preserve dated feature/crawler/protocol state. Action Plans record evidence-linked ownership, approval, verification, and rollback. The router references these artifacts but does not rewrite or merge them.
