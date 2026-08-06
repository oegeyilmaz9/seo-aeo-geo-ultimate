# GEO audit protocol

## Provenance

Treat Research Packs, target metadata, target captures, source captures, and answer observations as immutable. Verify hashes before analysis. An engine/surface result exists only when a dated raw observation is supplied; otherwise record a limitation or gap.

Audit evidence is a new direct observation of supplied captures. It uses the exact metadata URL and raw capture reference. It never republishes a Research Pack source record.

## Dimensions

### Entity consistency

Compare names, aliases, entity types, claims, attributes, and ambiguities across supplied targets and sources. Record only concrete inconsistencies. Entity prominence or mention frequency requires supplied observations and belongs to measurement when tracked over time.

### Evidence traceability

Resolve material claims to source records compatible with the finding's engine, surface, locale, and validity window. Preserve conflicts and stale support; do not select the convenient claim silently.

### Citation suitability

Assess whether a supplied source directly and clearly supports the in-scope entity or fact. This is source-quality analysis, not a prediction that an engine will cite it. Avoid passage-length formulas and universal source hierarchies.

### Cited-source alignment

Use a metadata-bound `content_set` target whose JSON capture lives under `raw/observations/`. Require exactly: `observed_at`, `engine`, `surface`, `locale`, `access_status`, `answer`, `mentioned_entities`, `cited_urls`, and `collection_method`. Require a timezone-aware `observed_at` no later than the metadata `captured_at`, and `captured_at` no later than Brief creation. Also require `access_status=observed`, a non-empty answer, matching finding scope, and at least one HTTPS cited URL that equals a source URL in the finding's referenced Research Pack evidence. A normal page, arbitrary file, brand mention, empty citation list, unrelated URL, or impossible chronology cannot be relabeled as cited-source alignment evidence.

### Documented engine control

Require current vendor documentation or an applicable standard. Record vendor advice as `vendor-recommended`, not as a ranking factor or guarantee. Delegate robots, rendering, directives, headers, transport, and indexing implementation to `seo-technical`.

## Myth-resistance gate

Decline universal GEO scores, fixed word counts, mandatory `llms.txt`, blanket crawler allow/block instructions, unsupported platform source percentages, guaranteed citation uplift, and correlation presented as causation. A documented feature is not automatically a visibility control.

## Recommendation gate

Every recommendation must link to findings, overlap their evidence, stay within their scope, inherit the weakest linked-finding classification, state an outcome, use an approved implementation owner, and include confidence plus a verification method. A speculative or experimental linked finding never supports implementation. Experimental-only support creates an experiment, not an implementation task.
