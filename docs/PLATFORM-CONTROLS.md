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

## Validate

```powershell
python scripts/validate_platform_controls.py validate-registry manifests/platform-controls.json --bundle manifests --as-of <YYYY-MM-DDT23:59:59Z>
```

Use `seo-technical` to review crawler and notification controls and to generate/validate a maintained `/llms.txt`; use `seo-schema` to check feature eligibility and lifecycle, and the relevant commerce, video, news, or agentic specialist for implementation-specific evidence.
