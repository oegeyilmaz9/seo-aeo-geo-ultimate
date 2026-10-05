# Keyword research and Markdown ownership

Read alongside `query-opportunity-protocol.md`. Produce `keyword-research.md`, `keyword-map.md`, `content-gap.md`, and `keyword-decisions.md` as substantive, directly linked work documents. A small task may combine these in one note with stable section links. Freeze `query-corpus.json` when it drives formal work; keep its existing schema and validator. Link Markdown rows to query IDs and immutable raw captures rather than adding unsupported fields to that contract.

## Discover and qualify

1. Inspect product truth, audiences, markets, languages, actual conversions and current canonical URL inventory. Keep owner-named targets and the leadership track. Identify branded/non-branded, informational, commercial comparison, transactional, support and local tasks as applicable; document exclusions, rather than forcing every site into every bucket.
2. Gather seeds from site/product taxonomy, authorized GSC/Bing queries and landing pages, internal search/support questions, dated SERPs, and accessible competitor coverage. Expand synonyms, entities, use cases, problem/solution language, modifiers, question forms, alternatives and topic subneeds. Suggestions/PAA/related searches are discovery observations, not volume or actual AI fan-out evidence. AI-generated seeds are hypotheses until qualified.
3. Preserve locale, country/location, device, engine/surface, collection time, source, method, window and limitations per evidence family. Distinguish raw spelling from normalization. Deduplicate Unicode/case variants with locale-aware rules; do not collapse distinct intent, Turkish characters, locations or languages. Maintain aliases and provenance.
4. Obtain volume, trends, seasonality, CPC and vendor difficulty only from accessible authorized sources. Preserve provider definitions, match/aggregation rules, geographic scope and date. Search Console impressions are site exposure, not total demand; Google Trends is a relative index, not monthly searches; CPC is advertising data, not an SEO value proof. Missing values stay `unavailable`/null. Never invent numbers or label a head term highest-volume without comparative demand evidence; retain it as a required research dependency.
5. Inspect the actual current result set for decision-driving families. Record query, market/device, access/method and timestamp, representative URLs, dominant/mixed intent, format, features and freshness. Do not call a generic web-search result a precisely localized Google SERP. When location/device cannot be pinned, disclose it and keep exact rank claims unverified.

## Cluster and decide

- Group by the reader task and compatible result intent, with representative SERP overlap as evidence where accessible. Lexical or embedding similarity alone does not decide page ownership. Keep mixed intent explicitly split when one page cannot satisfy both.
- Map each family to one existing canonical owner, a justified proposed page, merge/update work, or a documented no-action decision. HTML and its Markdown mirror are one content owner. Resolve their links to the exact answer section and topic map.
- Cannibalization requires actual competing query/page evidence, content overlap, result intent and history; two pages sharing a word is insufficient. Record competing URLs and the consolidation decision with redirects/internal links/canonical implications and baseline safeguards.
- Compare qualified need/demand against all suitable current pages: missing task, weak answer, outdated facts, format mismatch, missing source support, locale gap and architecture gap. Absence in a tool export is not proof of absence on the site. Avoid thin per-keyword pages; one need cluster usually has one substantive owner.
- Prioritize using business fit, demand provenance, existing exposure, intent fit, answer/source quality, content/authority gap, effort, risk and dependencies as separate fields. Keep the required nearer-term and head-term leadership tracks. Do not convert advertising metrics or vendor scores into a universal opportunity score.

## Required map row

`family/query IDs | reader task + intent | locale/market/device | evidence dates and links | demand status/provider/metric window | current HTML owner | exact Markdown URL + answer section | topic map | supporting variants/questions | coverage/cannibalization state | action and owner | ambition track + priority | acceptance and refresh trigger | limitations`.

Proposed URLs are labelled `planned`; never claim they can be fetched. Every serious candidate has source provenance, an intent decision, a canonical ownership decision and an action/no-action explanation. Every eligible public inventory page is covered or explicitly outside the keyword scope; scoped research does not pretend to be a complete market census.

## Apply and verify

Write natural titles, headings, descriptive metadata and useful answers from the approved page intent. No keyword-density targets, hidden variant blocks or mass FAQ schema. Keep HTML and Markdown facts/locale/source revisions aligned. Route AEO answer audits and GEO claim/source audits separately; a keyword list does not substitute for a Research Pack. Maintain pin-linked question prompts as hypotheses or actual observations with their evidence classification.

Before handoff, validate the Query Corpus and relevant Findings bundle, render their Markdown companions, check ownership collisions, unresolved query IDs, demand provenance, missing SERP evidence and incomplete inventory coverage. A no-tool fallback delivers a qualitative shortlist with gaps and collection instructions; it does not declare keyword research quantitatively complete. Record baseline and comparison windows separately for conventional search and AI surfaces, with refresh on product, intent, SERP, competitor or demand changes.

When a public Markdown candidate exists, render the validated corpus and exact page destinations with `python "<suite-root>/scripts/render_keyword_map.py" --corpus <bundle/query-corpus.json> --bundle <bundle> --manifest <private/markdown-manifest.json> --public-root <public-candidate> --output <private/keyword-map.md>`. Missing destinations remain planned/unresolved; this helper preserves demand provenance and limitations, but does not choose keyword clusters, approve copy, invent SERP observations or establish live delivery.

Primary metric definitions, reviewed 2026-10-03: [Keyword Planner](https://support.google.com/google-ads/answer/3022575), [Google Trends](https://support.google.com/trends/answer/4365533?hl=en), [Search Console performance](https://support.google.com/webmasters/answer/7576553?hl=en). Recheck definitions and actual access when using a provider.
