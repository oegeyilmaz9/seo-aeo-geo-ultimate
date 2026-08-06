# Technical evidence protocol

## Capture set

For a URL-level finding, retain the requested URL, final URL, time, HTTP status, relevant headers, raw body or immutable capture reference, rendered capture when relevant, canonical/robots values, sitemap/internal-link evidence, device/locale, and collection limitations.

## Recommendation format

Write: observation; expected state; affected scope; evidence; risk; owner; exact target state; validation capture; rollback; and any approval/dependency. A recommendation is incomplete when it cannot distinguish a confirmed implementation defect from an untested hypothesis.

## Cautions

Do not derive an issue from arbitrary thresholds such as click depth, URL length, or word count. Use current primary documentation for Google/Bing/platform behavior. State when a security or accessibility improvement is independently valuable rather than presenting it as a ranking signal.
