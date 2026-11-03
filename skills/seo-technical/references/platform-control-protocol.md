# Platform control protocol

## Registry gate

Use the checked-out `manifests/platform-controls.json` only after its validator passes for the current date. Every feature row records status, surfaces, markets/locales, primary documentation, verification date, affected skills, evidence class, and limitations. Removed or deprecated features retain an effective date; do not silently delete history.

## Site-specific crawler decision

`robots_support: documented` means the provider documents its handling; read the actual policy and limitations before interpreting it as compliance. Perplexity-User generally ignores robots.txt for user-requested fetching. Google-Extended is a product control for specified training/grounding and has no separate HTTP user agent. Current Anthropic documentation publishes IP data. Use the active primary-source registry declared in `manifests/suite.json`; historical research files are not current verification.

Copy only the exact vendor, user agent, purpose, robots support, WAF/IP verification method, documentation, and verification date. Add the site owner, business/legal/privacy/security decision, exact scope, staged test, expected log evidence, and rollback. Training, search indexing, AI search, and user-initiated fetches remain separate.

## Search visibility controls beyond crawlers

Read the [Search generative AI control help](https://support.google.com/webmasters/answer/16908024) and [Google sharing guide](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share). Search Console supports include/exclude/parent inheritance for AI Overviews, AI Mode and generative AI in Discover; verify the actual property and any child override. This is a feature control, not a robots user agent. It does not affect training or act as a ranking signal for other Search areas. Preserve separate decisions for Googlebot crawling, page/text preview controls, `noindex`, and Google-Extended's documented training/grounding products.

Use the [OpenAI crawler overview](https://developers.openai.com/api/docs/bots) for independent OAI-SearchBot and GPTBot choices and their own current IP ranges. Search opt-out can leave navigational links; user-initiated ChatGPT-User access is separate. Check the final URL and source content, not merely HTTP success or a familiar article ID. Record publisher update, feature rollout/effective date, and suite verification time separately. Never renew a source review solely by extending its deadline.

## Change notification and protocols

For IndexNow, feeds, or sitemaps, name eligible change types, endpoint/key ownership, receipt/log evidence, retry/rate policy, and decommission path. For UCP/ACP/MCP/A2A or another capability, record version/status, discovery, operations, authentication, fallback, data owner, and consumer. Neither mechanism is a ranking, indexing, retrieval, citation, or conversion guarantee.
