# Favicon search protocol

Use this protocol for a missing/wrong search-result icon or when hostname identity is part of a broad SEO release.

## Implementation contract

- Identify the exact hostname and its crawlable home page. Google supports one favicon per hostname, not a separate favicon per subdirectory.
- Use an owned, visually representative brand asset. Reuse an approved source asset or request one; do not invent or silently redesign the brand mark.
- Add a home-page `<link rel="icon" href="...">` or another currently documented supported icon relation. Resolve the exact final URL instead of assuming `/favicon.ico` is discovered.
- Deliver a stable, successful image URL. Keep the home page crawlable by Googlebot and the icon crawlable by Googlebot-Image; verify relevant robots/WAF/CDN behavior rather than inferring it from browser display.
- Use a square image. Google documents 8x8 as the minimum and recommends an image larger than 48x48 for quality across surfaces. For a newly owned implementation, target a square source above that recommendation unless product constraints require a documented exception.
- Preserve browser/application icon variants when needed, but do not claim that multiple declarations create multiple Google Search favicons for one hostname.

## Verification

Capture the home-page link relation and resolved icon URL, raw and rendered head where JavaScript is involved, final response/status/content type, image format and dimensions, cache/CDN result, crawl-control evidence, and whether the observed asset matches the approved brand source. Use the live-release verifier's `site_identity` contract for exact-candidate delivery.

Meeting the technical guidance makes the site eligible; it does not guarantee when or whether a search engine will display the favicon. Record recrawl/provider lag separately from implementation success.
