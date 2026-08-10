# Query Corpus protocol

`query-corpus.json` is the shared map between conventional search research and AI-search observation. It prevents keywords, prompts, and generated subqueries from being treated as if they were the same thing.

## Four query types

| Type | Meaning |
| --- | --- |
| `user_need` | The underlying job, question, or decision a person is trying to resolve. |
| `observed_search_query` | A query observed in a declared first-party or third-party source. |
| `ai_prompt` | A prompt selected for an AI-search test, including conversational context when relevant. |
| `executed_subquery` | A query visibly executed by an AI surface during an observed run. It must point to its parent prompt and observed provenance. |

Every entry records locale and market context, evidence provenance, demand status, coverage intent, confidence, and limitations. An `observed_search_query` requires first-party, third-party-estimate, or direct-observation provenance; an editorial hypothesis cannot impersonate an observed query. Local source and asserted coverage evidence is SHA-256-pinned. `covered` requires a current target URL, `gap` cannot declare a current URL, and `cannibalized` requires at least two evidenced current competitors. Demand remains `unavailable` unless a dated provider plus a source URL or hash-pinned source file supports it. A Query Corpus can optionally bind to a validated Research Pack by ID and SHA-256 hash.

## Validate

```powershell
python scripts/validate_query_corpus.py validate-corpus query-corpus.json --bundle <artifact-directory>
```

Use the corpus as a versioned input for `seo-performance`, `ai-visibility-monitor`, and specialists that need query coverage. Update it when intent, market, surface behavior, or evidence changes; do not silently rewrite an earlier measurement input.
