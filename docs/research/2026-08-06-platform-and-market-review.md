# 2026-08-06 primary-source review: SEO, AEO, GEO, and AI visibility

## Scope and evidence standard

This review supports changes to the public skill suite. It is not a claim that all
web documentation has been read. The suite uses a continuously refreshed registry
of authoritative search-engine, AI-platform, standards, and clearly labeled
market-pattern sources in the adjacent source registry JSON file.

Platform or standards guidance is only treated as current inside its freshness
window. Vendor product pages inform usability and product patterns; they do not
become facts about how an engine ranks, retrieves, cites, or trains.

## Confirmed design implications

### 1. Google AI Search is not a separate hack surface

Google's current documentation treats AI Overviews and AI Mode as separate
surfaces, but says standard SEO foundations, an indexable and snippet-eligible
page, original people-first content, crawlability, and page experience remain
the relevant prerequisites. It explicitly rejects a requirement for llms.txt,
special AI markup, fixed chunking, and a special schema type for Google AI
visibility.

Suite effect:

- Keep google / ai-overview and google / ai-mode as distinct observation cells.
- Add Google Search Console's Generative AI performance report as an optional,
  first-party measurement source where a verified property has access.
- Do not output an AI-ready score, a Google citation promise, a mandatory
  llms.txt, or a word-count/chunking prescription.

### 2. Engine controls are purpose-specific and approval-sensitive

Google, OpenAI, Anthropic, and Perplexity distinguish search indexing, user
initiated fetches, advertising, and model-training-related crawlers differently.
robots.txt is a crawler guidance protocol, not authorization. WAF or allowlisting
changes can create availability and security consequences.

Suite effect:

- Crawler recommendations must name the exact bot, purpose, evidence source,
  current verification date, and decision owner.
- Never generate a blanket allow-all-AI-bots rule.
- Never recommend IP allowlisting from memory or user-agent matching alone.
- Treat training, search discovery, user-directed fetches, and agentic browser
  access as separate policy decisions.

### 3. Measured visibility has multiple incompatible kinds of evidence

The available first-party reports and market products use different definitions:
Google offers property/page/country/device generative-search impressions where
available; Microsoft exposes verified-domain citation, referral, and bot-activity
data; answer-surface observation records mentions and visible citations. A bot
request does not prove retrieval, grounding, citation, referral, or conversion.

Suite effect:

- Report all measures in source-specific metric families.
- Do not average Google impressions, observed citation rate, Clarity citation
  counts, or referral sessions into one score.
- Preserve explicit unavailable, blocked, no-answer, no-citation, and
  non-comparable states.

### 4. Repeated measurements and uncertainty are not optional polish

Current research and leading tools recognize that generative answers vary with
time, session, model, locale, surface, and hidden platform conditions. A single
answer is an observation, not a stable ranking.

Suite effect:

- Add a measurement plan with optional replicated samples per frozen corpus cell.
- Require a confidence or uncertainty method when reporting replicated rates.
- Treat a single sample as descriptive only, never as a definitive rank or
  causal impact claim.
- Mark a comparison non-comparable when corpus, locale, surface, access profile,
  model disclosure, definition, or reporting window changes.

### 5. Useful recommendations require a bridge from audit to action

The previous suite correctly separated research, AEO/GEO audit, and measurement,
but its implementation handoff could stop at an owner label. Teams need a
concrete, evidence-linked recommendation such as:

- add an independently sourced definition and a decision table to answer an
  unresolved buyer question;
- replace an ambiguous entity alias with the verified canonical name plus
  supporting evidence;
- expose a required fact in visible text before mirroring it in structured data;
- repair a blocked canonical URL or rendered-content gap;
- design a controlled content experiment with a rollback and a later,
  non-causal comparison.

Suite effect:

- Add a separate action-planning skill that consumes validated findings and
  emits actionable content, technical, schema, locale, and measurement briefs.
- Its recommendations remain scoped to evidence, required approval, expected
  outcome, verification, risk, and rollback. It does not silently write,
  deploy, or claim that an action will earn citations.

### 6. Content guidance must improve utility, not optimize formulas

Google's people-first guidance and Bing's current webmaster guidance converge on
original, focused, clearly structured, independently verifiable content. They do
not establish universal word counts, exact keyword density, fixed heading
patterns, or a single content score.

Suite effect:

- Rewrite the legacy seo-content flow around an editorial evidence brief:
  user/job, claim ledger, source and SME requirements, primary answer,
  differentiating experience, caveats, visual/structured support, internal
  links, locale review, CTA integrity, and verification.
- Make examples and alternative recommendations optional and factual, not
  generic filler.

## Market patterns worth adopting, with safeguards

| Pattern observed | Product examples | Suite adoption |
|---|---|---|
| Frozen prompt libraries with engine, country, and cadence | Ahrefs, OtterlyAI | Retain query provenance, locale, surface, and corpus hash. |
| Raw response and cited-source drill-down | OtterlyAI, Scrunch | Preserve raw captures, raw cited URLs, canonical derivation, and access state. |
| Prompt intent and topic clusters used to prioritize action | Peec AI, Ahrefs | Add content/action briefs, but no opaque recommendation score. |
| Mentions, citations, referral, and source analysis reported separately | Ahrefs, Scrunch, Microsoft Clarity | Keep metric definitions, denominators, exclusions, and source systems separate. |
| Platform and response variance acknowledged | Ahrefs, academic work | Support repeat sampling and uncertainty; no single-run placement claim. |

## Explicitly rejected patterns

- A universal SEO, AEO, GEO, or AI visibility score.
- Guaranteed rankings, citations, mentions, inclusion, traffic, or causal uplift.
- A mandatory llms.txt, fixed passage size, fixed word count, keyword density,
  FAQ-schema, or crawler policy.
- Generic allow-every-AI-crawler configuration.
- Browser/UI automation that bypasses a platform's authentication, terms,
  robots, rate limits, paywall, or bot defenses.
- Attribution claims based only on before/after observational movement.
