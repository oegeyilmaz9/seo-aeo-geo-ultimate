# Technical evidence protocol

## Capture set

For a URL-level finding, retain the requested URL, final URL, time, HTTP status, relevant headers, raw body or immutable capture reference, rendered capture when relevant, hosting/CDN identity, canonical/robots values, sitemap/internal-link evidence, device/locale, and collection limitations. For hostname identity, also retain the home-page icon declaration, resolved favicon response/content type/dimensions, approved asset identity, and crawl-control evidence. Name the layer each observation proves.

## Recommendation format

Write: observation; expected state; affected scope and verification universe; evidence and layer; adjudication status; risk; owner; exact target state; validation capture; rollback; and any approval/dependency. A recommendation is incomplete when it cannot distinguish a confirmed implementation defect from a layer mismatch, supported opportunity, false positive, or untested hypothesis.

## Cautions

Do not derive an issue from arbitrary thresholds such as click depth, URL length, or word count. Use current primary documentation for Google/Bing/platform behavior. State when a security or accessibility improvement is independently valuable rather than presenting it as a ranking signal.
