# Commerce evidence protocol

## Required capture

For each sampled product or variant retain: canonical URL, locale/market, visible name and offer facts, raw/rendered structured data, stable identifiers, feed destination and row, feed fetch/update time, platform diagnostics, availability/price source of truth, and collection limitations.

## Parity rules

Compare page, markup, feed, and checkout-visible facts. A feed may improve platform data freshness but cannot replace a usable crawlable page. JavaScript-generated markup needs rendered evidence and freshness verification. Mark unavailable property access as a gap rather than assuming acceptance.

## Capability and freshness

Treat Merchant Center, Bing feeds, OpenAI product data, ACP, UCP, and IndexNow as separate documented capabilities. Record vendor, status, market, last verified date, owner, authentication/security boundary, supported operations, fallback, and proof of receipt. Capability support never proves ranking, recommendation, citation, checkout completion, or sales.

## Formal handoff

Use SEO Findings `1.1.0`. Commerce policy violations are critical. Price, inventory, checkout, robots, canonical, feed publication, and protocol changes require approval, verification, and rollback through `seo-action-plan`.
