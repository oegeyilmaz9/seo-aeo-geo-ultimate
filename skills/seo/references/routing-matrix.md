# SEO routing matrix

## Universal entry point

Use `seo` as the recommended first call and user-facing owner for any SEO, AEO, GEO, or AI-search request. It accepts a plain-language narrow task or cross-functional outcome, screens all 27 suite skills, executes every applicable specialist lane, preserves the handoffs internally, and returns one consolidated result. A user may still call a known specialist directly, but they never need to know or coordinate the internal map.

| User intent | Primary owner | Required upstream | Downstream |
|---|---|---|---|
| Build current AI-search evidence | `ai-search-research` | Authorized inputs | AEO, GEO, monitor |
| Audit answer readiness | `seo-aeo` | Research Pack + captures | Validated AEO finding |
| Turn validated findings into an execution plan | `seo-action-plan` | Validated Optimization Brief + preserved input bundle | Approval-ready Action Plan |
| Rewrite or implement an answer change | Exact approved action owner | Validated Action Plan item | QA + comparison measurement |
| Release an identified candidate and verify it live | `optimise-seo` + `seo-technical` | Local acceptance receipt + separate release authorization + candidate identity | Live-delivery receipt; provider outcome still pending |
| Submit a sitemap/URL set or run another provider mutation | `seo-performance` | Exact verified property + current capability evidence + mutation-time authorization | Provider-operation receipt + delayed outcome follow-up |
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
| Broad rank-higher or organic-growth request | `seo-research` + `seo-page`; add `seo-technical` for hostname identity and `seo-authority`/`seo-architecture` when the leadership gap requires them | Desired market/query families, page/site scope, current captures, authorized GSC/Bing data when available | Two-track slate: nearer-term gains plus mandatory high-volume head-term/category leadership, complete search-result presentation, then owned implementation |
| Missing, generic, duplicated, or under-informative search snippet | `seo-page` + `seo-content` | Page purpose, target query family, visible content, current title/meta | Page-specific title/meta draft and rendered acceptance check |
| Missing or incorrect favicon in search presentation | `seo-technical` | Hostname home page, owned brand asset, favicon response/crawl evidence | Favicon implementation and live site-identity verification |
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
- "Ship it and close SEO" requires three independent questions: is the exact candidate accepted locally, is release authorized and verified over the affected universe, and is any provider mutation separately authorized? An accepted submission is not an indexing result.
- "Should we publish an llms.txt?" routes to `seo-technical`. Recommend and generate it when truthful public sources and an owner make upkeep reliable, even if adoption is still a future-readiness bet. It is never a universal visibility prescription.
- "Fix everything" begins with scope and evidence, then bounded specialist lanes; it is not permission for unrelated changes.
- "Get us higher for these keywords" preserves the owner's named queries, adds observed near-win and coverage-gap candidates, and selects one primary query family per target page from first-party performance, dated SERP intent, business fit, page ownership, and realistic evidence. Every relevant owner-named high-volume family remains in a mandatory head-term leadership track. Difficulty, weak current visibility, or an authority gap can change milestones and required investment but cannot silently move that family to `Defer`; only an owner decision, genuine intent/product mismatch, or prohibited/misleading target can do that. The plan does not reduce the task to volume or keyword density, and it does not sacrifice category ambition to quick wins.

## Artifact discipline

Research Pack provenance remains immutable. Query Corpora preserve user needs, observed queries, prompts, disclosed subqueries, demand provenance, and page coverage. AEO/GEO Optimization Briefs and SEO Findings record audit findings and candidate owners. Site Graphs preserve captured architecture. SEO Performance Runs and Visibility Runs preserve unlike observational metric families. Platform Controls preserve dated feature/crawler/protocol state. Action Plans record evidence-linked ownership, approval, verification, and rollback. Decision records preserve product intent and independent authorization states; live-release reports prove delivery checks; provider-operation receipts prove only the exact provider action and response. The router references these artifacts but does not rewrite or merge them.
