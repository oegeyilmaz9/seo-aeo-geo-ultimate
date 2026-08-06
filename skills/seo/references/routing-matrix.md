# SEO routing matrix

| User intent | Primary owner | Required upstream | Downstream |
|---|---|---|---|
| Build current AI-search evidence | `ai-search-research` | Authorized inputs | AEO, GEO, monitor |
| Audit answer readiness | `seo-aeo` | Research Pack + captures | Validated AEO finding |
| Turn validated findings into an execution plan | `seo-action-plan` | Validated Optimization Brief + preserved input bundle | Approval-ready Action Plan |
| Rewrite or implement an answer change | Exact approved action owner | Validated Action Plan item | QA + comparison measurement |
| Audit entity/source/citation readiness | `seo-geo` | Research Pack + captures/observations | Content/schema/technical implementation |
| Measure mentions, citations, accuracy, referrals, drift | `ai-visibility-monitor` | Research Pack + frozen corpus | Later audit or strategy |
| Full site audit | `seo-audit` | Crawl/site scope | Specialist remediation |
| One-page mixed audit | `seo-page` | Page capture | Specialist remediation |
| Crawl/index/render/performance | `seo-technical` | Technical evidence | Implementation |
| Editorial/content quality | `seo-content` | Content set | Content implementation |
| Structured data | `seo-schema` | Page/entity facts | Schema implementation |
| Sitemaps | `seo-sitemap` | URL inventory | Technical implementation |
| Images | `seo-images` | Media inventory | Media implementation |
| International SEO | `seo-hreflang` | Locale/URL map | Technical implementation |
| Strategy/roadmap | `seo-plan` | Validated findings | Sequenced execution |
| Large-scale page systems | `seo-programmatic` | Template/data rules | Implementation + QA |

## Ambiguity resolution

- "Make us show up in ChatGPT" is not an implementation order. Route first to research, then GEO/AEO audit, baseline measurement where tracking is requested, action planning, and only then approved implementation.
- "Audit this answer" routes to `seo-aeo` when the supplied target is a direct-answer surface.
- "Optimize this answer" is ambiguous: audit with `seo-aeo` if no validated AEO finding exists; otherwise create an `seo-action-plan` and route rewrite or implementation to its exact approved owner. Canonical owners are `seo-content`, `seo-schema`, `seo-technical`, `seo-hreflang`, and `optimise-seo`. `seo-aeo` does not rewrite or approve implementation.
- "Track whether it worked" routes to the monitor and must not imply causation.
- "Fix everything" begins with scope and evidence, then bounded specialist lanes; it is not permission for unrelated changes.

## Artifact discipline

Research Pack provenance remains immutable. AEO/GEO Optimization Briefs record audit findings and candidate owners. Action Plans record evidence-linked ownership, approval state, verification, and rollback. Visibility Runs record observed measurement only. The router references these artifacts but does not rewrite or merge them.
