# Platform Controls

`manifests/platform-controls.json` is the suite's dated control registry for platform features, crawler purposes, change-notification mechanisms, and agentic commerce protocols. It keeps fast-changing platform facts separate from evergreen SEO advice.

## What it tracks

- feature lifecycle: `current`, `preview`, `deprecated`, or `removed`;
- optional publisher-guide proposals such as `llms.txt`, with adoption and platform limitations kept explicit;
- crawler identity and documented purpose, without guessing from a user agent name;
- per-crawler business decisions: `allow`, `block`, `conditional`, or deliberately `undecided`;
- IndexNow, feeds, news/video sitemap notification paths, and receipt/log evidence;
- protocol capabilities such as UCP and ACP, including verification state and limitations.

The shipped registry is a reviewed reference, not a universal robots policy. Business decisions remain `undecided` until the site owner chooses them. A platform entry must be refreshed when its review window expires or its primary documentation changes.

## Current source verification

The [2026-11-03 review](research/2026-11-03-source-review.md) records the redirect correction and the primary-source checks. A validator pass checks structure and dated metadata; it does not fetch sources or prove that their claims are supported. Re-read the destination and its contents before renewing verification dates. Extending `review_due_at` alone is not a source review; per-entry age limits still apply.

OpenAI's [crawler overview](https://developers.openai.com/api/docs/bots) documents independent OAI-SearchBot search and GPTBot training controls, with separate IP endpoints. Search opt-out can leave navigational links. ChatGPT-User is a separate user-initiated fetcher, not the search control. The former help article ID 12627856 now resolves to unrelated Atlas retirement guidance and is retained only in historical evidence.

Google's [Search generative AI control](https://support.google.com/webmasters/answer/16908024) is a Search Console property setting for AI Overviews, AI Mode, and generative AI features in Discover. It supports inclusion, exclusion, and parent inheritance with child-property overrides. It is recorded under `features`, since it is not a crawler user agent. Check the actual property's setting and inheritance before proposing a change; documentation is not evidence of that property's configuration.

Keep this visibility setting separate from Googlebot crawling, page/text preview controls, `noindex`, and Google-Extended. The Search Console control does not affect training or act as a ranking/inclusion signal for other Search areas. Google-Extended has no separate HTTP user agent and does not control Search inclusion or ranking; its [crawler documentation](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers) specifies the training and grounding products it covers. Do not infer a broader product scope than the current sources establish.

`effective_at` records the help page's worldwide rollout day, 2026-08-31, with no exact-time or first-launch claim. The [sharing guide](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share) was updated 2026-10-21 to list existing controls; that is a source modification date in the source registry. `last_verified_at` is this suite's inspection time. These three dates have different meanings. Exclusion can be delayed by propagation and caching; confirm the eventual result rather than promising an exact deadline.

## Validate

```powershell
python scripts/validate_platform_controls.py validate-registry manifests/platform-controls.json --bundle manifests --as-of <YYYY-MM-DDT23:59:59Z>
```

Use `seo-technical` to review crawler and notification controls and to generate/validate a maintained `/llms.txt`; use `seo-schema` to check feature eligibility and lifecycle, and the relevant commerce, video, news, or agentic specialist for implementation-specific evidence.
