# Capture protocol

Treat engine, surface, locale, and access state as separate dimensions. Examples include `google` + `ai-overview`, `google` + `ai-mode`, `microsoft` + `copilot-search`, `openai` + `chatgpt-search`, and `anthropic` + `claude-web-search`. Record explicit locale cells such as `tr-TR` and `en-US`; prompt language alone is not locale.

Map each request-derived audience to a lowercase kebab-case identifier, such as `brand`, `creator`, `buyer`, `procurement-team`, or `general`. Preserve the request wording in the query intent when the normalized identifier could be ambiguous; never force a fixed audience list.

Non-engine channels such as analytics, logs, or cross-engine entity resolution are not engine surfaces. Encode all three gap dimensions (`engine`, `surface`, and `locale`) as `not_applicable`, and name the channel in `description`. When access to analytics, logs, or cross-engine entity resolution is known to be blocked, unavailable, or not permitted, use `missing_evidence` with all three dimensions set to `not_applicable`.

For each query run, preserve a raw answer or result capture inside the bundle. Record observed UTC time, engine, surface, locale, access/authentication state, collection method, visible citations, and limitations. Use a new conversation/search for each prompt when the surface supports it. Do not bypass authentication, access controls, robots, rate limits, or terms.

For evidence claims, store one raw reference per claim in `raw_evidence_ref`, always under `raw/`. Preserve only the minimum excerpt needed to support the claim, respect copyright limits, and redact secrets, account IDs, personal data, and sensitive prompt content before saving the raw file.

Treat `gap_type` values as stable identifiers, not prose labels. Choose the first matching state:

- `inaccessible_surface`: collection for a declared engine/surface/locale cell was blocked, unavailable, or not permitted; the access state is known.
- `no_web`: access succeeded but live web retrieval was not active.
- `no_answer`: access and retrieval succeeded but no answer was returned.
- `no_citation`: an answer was returned without visible citations.
- `missing_evidence`: exact support is absent after permitted collection, or the access state was not established.
- `unresolved_ambiguity`: the request or entity meaning remains ambiguous after permitted clarification or research.
- `stale_input`: the only relevant evidence or observation is outside its freshness window.

`inaccessible_surface` remains reserved for declared engine/surface/locale cells. Never use `missing_evidence` for a declared engine/surface/locale cell when collection is known to be blocked, unavailable, or not permitted. If an answer was returned but a feature or entity did not appear, describe that observation without converting it to `inaccessible_surface` or inventing a synonym.

Create a competitor observation only from a resolving raw capture. Include raw cited URLs exactly as shown; do not replace them with canonicalized URLs in this research artifact. A crawlable competitor page without an answer-engine capture belongs in `evidence[]`, not `competitor_observations[]`.

A competitor observation is current through the exact 14-day boundary. After that boundary, preserve it as historical and add a `stale_input` gap whose optional `related_observation_ids` contains the existing `observation_id`; do not use prose as linkage.

Redact secrets, account IDs, personal data, and sensitive prompt content. Preserve only the minimum source excerpt needed for audit. Use forward slashes and bundle-relative paths; never write an absolute workspace path into an artifact.
