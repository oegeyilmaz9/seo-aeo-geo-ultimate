# Live release verification

`verify_live_release.py` compares an exact released candidate with a local expected URL inventory and the declared live HTTP contract. It is read-only and uses the Python standard library.

## What it checks

- exact full-corpus or scoped sitemap checks, including sitemap indexes and explicit nonindex exclusion;
- every expected indexable or nonindex document's status, robots state, canonical, title, description, H1, and declared hreflang mappings;
- redirect source status, first `Location`, sitemap exclusion, and target membership;
- shared surfaces such as `robots.txt`, favicon, or optional `llms.txt`;
- optional hostname identity: home-page favicon declaration, exact icon URL/status/content type, square dimensions, and an owned quality floor;
- transient retries versus permanent failures;
- distinct expected, passed, and failed counts.

The tool intentionally does not follow redirects when checking their first response. It does not require document-only metadata from a bodyless redirect. It does not render JavaScript: when hydrated verification is required, the plan fails closed and a separate isolated-browser capture must complete that layer.

## Plan

The expected inventory can be a newline-delimited URL file, a JSON URL array/object, or one XML `urlset`. It represents the affected document universe, including any explicitly nonindex documents. Every URL and live endpoint must belong to the declared origin. Production targets require HTTPS; `--allow-private-targets` exists only for controlled local testing.

Use `sitemap_mode: "exact"` when the inventory is the full expected sitemap corpus. Use `"scoped"` for a page, template, or closed route-class change: declared indexable URLs must be present, declared nonindex URLs and redirect sources must be absent, and unrelated sitemap URLs are left outside the claim.

First preserve the exact local candidate in `candidate-manifest.json`. Include the relevant source and generated-output hashes even when the worktree is dirty. `corpus.sha256` is the SHA-256 of the normalized, sorted expected URL set joined with `\n` and terminated by a final `\n`.

```json
{
  "schema_version": "1.0.0",
  "candidate_id": "build-8f31c2",
  "candidate_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "git_dirty": false,
  "source_files": [
    {
      "path": "src/routes.ts",
      "sha256": "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0"
    }
  ],
  "generated_files": [
    {
      "path": "dist/routes.json",
      "sha256": "23456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef01"
    }
  ],
  "build_identity": "production-build-2026-08-20T10:00:00Z",
  "corpus": {
    "kind": "url-set",
    "expected_count": 1,
    "sha256": "3456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef012"
  }
}
```

Then hash that manifest byte-for-byte and bind it to the release plan. `deployment_id` must identify the actual deployment being checked, while `production_alias` must equal `origin`.

```json
{
  "schema_version": "1.0.0",
  "release_id": "docs-release-2026-08-20",
  "candidate": {
    "candidate_id": "build-8f31c2",
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "git_dirty": false,
    "manifest_ref": "candidate-manifest.json",
    "manifest_sha256": "456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123",
    "deployment_id": "deployment-01k2abc3",
    "production_alias": "https://example.com"
  },
  "origin": "https://example.com",
  "expected_inventory_ref": "expected-urls.txt",
  "live_sitemap_url": "https://example.com/sitemap.xml",
  "sitemap_mode": "exact",
  "document_defaults": {
    "allowed_status": [200],
    "indexable": true,
    "canonical": "self",
    "require_title": true,
    "require_description": true,
    "require_h1": true
  },
  "document_overrides": [
    {
      "url": "https://example.com/new-page",
      "expected_title": "Approved search title",
      "expected_description": "The complete, page-specific description approved for this release.",
      "expected_h1": "Approved page heading"
    }
  ],
  "redirects": [
    {
      "source": "https://example.com/old-page",
      "target": "https://example.com/new-page",
      "allowed_status": [301, 308]
    }
  ],
  "surfaces": [
    {
      "surface_id": "robots",
      "url": "https://example.com/robots.txt",
      "allowed_status": [200],
      "content_type_prefix": "text/plain",
      "required_text": "User-agent:"
    }
  ],
  "network": {"concurrency": 8, "retries": 2, "timeout_seconds": 5},
  "rendered_required": false,
  "site_identity": {
    "homepage_url": "https://example.com",
    "expected_favicon_url": "https://example.com/favicon.png",
    "minimum_size_px": 8,
    "require_recommended_size": true
  }
}
```

`site_identity` is optional for a deliberately narrow release and required by the suite's broad site-optimization closeout. With `require_recommended_size: true`, an owned new favicon must be square and larger than 48x48 rather than merely meeting Google's 8x8 eligibility minimum. The check cannot prove historical URL stability, recrawl, or final search-result display.

Use `expected_title`, `expected_description`, and `expected_h1` in a document override when the release contains approved search-result copy. The verifier normalizes whitespace and then requires the exact copy to be present on the live document. This prevents a deployment from passing merely because it emitted a non-empty but stale, generic, or truncated description; the editorial protocol remains responsible for making the approved copy useful and page-specific.

Run:

```powershell
python scripts/verify_live_release.py verify --plan work/release/plan.json --output work/release/live-release-report.json
```

Exit `0` means every declared raw/live check passed. Exit `1` writes a failure report. Exit `2` means the plan, target safety, or output contract was invalid. A passing report proves delivery checks only; it does not prove crawl, indexing, ranking, retrieval, citation, referral, traffic, or conversion.
