# llms.txt publisher-guide protocol

Use `/llms.txt` as a concise map of trustworthy public resources for clients that choose to consume it. Treat it as a community proposal and a low-cost future-readiness layer, not as robots policy, access authorization, special AI markup, or a visibility requirement.

## Recommendation

Recommend publication when all of these are true:

- the site has canonical public documentation, product, policy, or reference pages worth curating;
- the file can be generated or reviewed whenever those sources change;
- a named content or technical owner accepts the maintenance responsibility;
- the file exposes no private, authenticated, staging, personalized, or security-sensitive URL;
- the team understands that publication does not guarantee crawling, retrieval, citation, ranking, traffic, or conversion.

A documented consumer strengthens the case but is not mandatory. When the file is cheap to keep correct, it is reasonable to publish it as a monitored future-readiness measure. If the content is likely to drift or has no owner, do not publish a misleading file merely to check a box.

## Build profile

Start from [the bundled template](../assets/llms.txt.template) and produce UTF-8 Markdown at the intended site's `/llms.txt` path:

1. Add one H1 with the exact public project or site name.
2. Add a short blockquote summary grounded in the public source of truth.
3. Add only necessary interpretation, version, locale, or scope notes.
4. Organize absolute HTTPS links under H2 headings. Prefer canonical Markdown alternatives when the site genuinely publishes them; otherwise link the canonical human-readable page.
5. Use the special `## Optional` section for secondary material a client may omit.
6. Add concise descriptions that explain what each resource contains.

Do not copy the whole site into the file, invent facts, add AI-only claims, list every sitemap URL, include ephemeral query URLs, or expose internal/admin endpoints. Do not use `llms.txt` to allow or block crawlers; keep those decisions in `robots.txt`, platform controls, and security policy.

## Validate and release

Let `<suite-root>` mean `${CLAUDE_PLUGIN_ROOT}` in Claude Code. In Codex, read `suite_root` from the installed skill's `.seo-suite-runtime.json` locator. A repository checkout is also a valid development fallback. Run:

```powershell
python "<suite-root>/scripts/validate_llms_txt.py" validate-file <site-root>/llms.txt
```

The default check is deterministic and offline. After deployment, optionally verify the linked resources with bounded network checks:

```powershell
python "<suite-root>/scripts/validate_llms_txt.py" validate-file <site-root>/llms.txt --check-live
```

The live option accepts only public HTTPS targets, follows at most five redirects, checks at most 25 links, uses a five-second timeout per request, and requires a successful response with a text, JSON, XML, or PDF content type. Use `--timeout`, `--max-links`, and `--max-redirects` only to lower or deliberately adjust those bounded defaults within the validator's hard limits. Live availability is a release check, not proof that any AI system consumes the file.

Then verify the deployed URL returns the reviewed UTF-8 content at `/llms.txt` and matches the current canonical sources. Add the file to the same review/release path as those sources, assign an owner, and revalidate it after content, URL, locale, version, product, price, or policy changes.

Google currently documents that it ignores `llms.txt` for Search visibility and that publishing one neither helps nor harms Google rankings. Other clients may choose to use the community proposal. Measure any downstream behavior separately; never infer it from the file's existence.
