# Migration, incident, and recovery protocol

Use this protocol for high-risk technical changes and sudden search/indexing failures. Keep availability, crawlability, indexability, reporting, ranking, and traffic as separate states. Route security containment to the security owner; SEO evidence does not replace incident response.

## Site migration or replatforming

### Preflight

1. Name the migration owner, technical owner, analytics owner, release authority, rollback authority, launch window, and explicit non-goals.
2. Freeze a dated old-state inventory: canonical/indexable URLs, representative templates, status/directives, canonicals, hreflang, structured data, internal links, sitemaps, robots files, hosted media/downloads, analytics tags, Search Console/Bing properties, and relevant performance/log baselines.
3. Build an explicit old-to-new URL map. Every old URL must resolve to one intended new URL, a deliberate `404`/`410`, or a documented unresolved decision. Reject chains, loops, blanket homepage redirects, and mappings based only on string similarity.
4. Test the new environment without exposing staging to indexing. Prepare the production robots and `noindex` state separately so temporary staging controls cannot ship accidentally.
5. Define launch acceptance and rollback thresholds before release. Avoid bundling unrelated content, navigation, tracking, domain, and platform changes when separation is practical; record unavoidable confounders.

### Launch gate

- Verify DNS/TLS/host behavior, server capacity, old-to-new redirects, final status, canonical targets, index directives, rendered content parity, links, hreflang, structured data, sitemaps, robots files, analytics/RUM, and ownership of old and new reporting properties.
- Sample high-value, long-tail, media, locale, parameter, removed, and edge URLs. A successful homepage test is not a migration test.
- Capture the release identifier and exact launch time. Preserve the last known-good configuration and the tested rollback procedure.

### Follow-up

- Monitor server errors, redirect failures, crawl requests, sitemap processing, representative URL inspection, indexed-state reporting, performance, and like-for-like search metrics on a declared cadence.
- Compare by page family, locale, device, and query cohort where data permits. Do not call expected recrawl volatility a defect or call traffic recovery proof that every URL migrated correctly.
- Keep redirects and old-host ownership for the documented migration lifecycle. Close only after the mapped inventory and declared acceptance checks pass; unresolved URLs remain visible.

## Traffic or indexation incident

1. Open an incident record with first observed time, last known-good time, affected properties/segments, reporter, severity, and current user/business impact. Preserve raw exports and timestamps.
2. Confirm that the signal is real. Check reporting delay, property/filter/window changes, consent or analytics changes, seasonality, demand, manual actions, security issues, and platform status before diagnosing a site defect.
3. Segment the change by URL/template, directory, locale, device, query, search appearance, status, canonical, and deployment cohort. Aggregate loss alone does not identify a cause.
4. Build a change timeline from deploys, CMS/data releases, DNS/CDN/WAF changes, robots/directive/canonical changes, sitemap changes, migrations, outages, and reporting configuration.
5. Test the smallest causal candidate against HTTP/rendered captures, logs, URL inspection, sitemap/index reporting, and comparable first-party performance evidence. Record competing hypotheses and disconfirming evidence.
6. Stabilize user and crawler access first. Roll back only against a predeclared condition and known-good state; do not stack speculative SEO changes during diagnosis.
7. After recovery, retain root cause, affected scope, corrective action, verification, monitoring, rollback outcome, evidence gaps, and prevention owner. Describe recovery as observed state change, not guaranteed future performance.

## Manual action or hacked-site recovery

1. Distinguish a Search Console Manual Actions report, Security Issues report, Safe Browsing/browser warning, legal removal, and ordinary technical indexation loss. Use the exact authorized property and report; do not infer one from traffic loss.
2. For a compromise, activate the security/incident owner, preserve forensic evidence, restrict unsafe access, rotate compromised credentials, identify the entry point and persistence mechanism, remove malicious content/code, patch the root cause, and inspect backups, plugins, accounts, templates, databases, redirects, and all affected host/protocol variants. Do not open suspected malware pages in an ordinary browser merely to inspect SEO.
3. For a manual action, inventory the exact reported type and affected patterns, correct the underlying policy violation across the full affected scope, and preserve a claim-to-evidence log. Cosmetic edits to example URLs are not remediation.
4. Re-crawl and inspect clean representative and edge URLs, verify user and crawler access, confirm no malicious or violating behavior remains, and document prevention controls plus owners.
5. Request the matching security review or reconsideration only after the remediation evidence is complete. State what happened, what was corrected, how the correction was verified, and how recurrence is reduced. Do not submit repeated requests while a decision is pending or promise reinstatement, ranking, or timing.

## Handoff

Package confirmed technical findings for `seo-action-plan` with owner, scope, approval, acceptance, verification, rollback, and security/legal dependencies. Use `seo-performance` for a hash-pinned baseline or comparison; measurements do not self-approve a migration or establish causation.

## Primary execution references

- [Google Search Central: Site Moves and Migrations](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)
- [Search Console Help: Manual Actions report](https://support.google.com/webmasters/answer/9044175?hl=en)
- [Search Console Help: Security Issues report](https://support.google.com/webmasters/answer/9044101?hl=en)
- [Search Console Help: Reconsideration requests](https://support.google.com/webmasters/answer/35843?hl=en)
