# AEO audit protocol

## Inputs and evidence

Treat the supplied Research Pack, target metadata, and target captures as immutable. Verify the metadata SHA-256, require its exact field set, verify every Brief target field against it, then verify the target capture SHA-256. Never infer or invent a canonical URL from a file name or brand. Cite the exact artifact ID, schema version, SHA-256, collection, and record ID. Audit-created evidence belongs to the Optimization Brief and must not copy or amend Research Pack evidence.

Use `SELF` only for a reference from the Optimization Brief to its own `audit_evidence`; a literal self-hash would be circular. External artifact references always require their real SHA-256.

## Dimensions

### Direct-answer completeness

Check whether the visible target answers each in-scope researched question with the facts needed for that intent. Do not require one preferred sentence shape, answer length, heading style, or placement.

### Intent and audience coverage

Map every finding to resolved Research Pack query IDs. Keep its locale equal to the target locale and its engine/surface pairs within the mapped queries' applicability. Identify absent or conflicting coverage by locale, audience, and journey stage. Do not manufacture a query, expand arrays to hide a mismatch, or demand coverage beyond the declared scope.

### Clarity and extractability

An answer is self-contained when its subject, action or fact, qualifications, and relevant scope remain understandable when read alone. Treat this as an editorial diagnostic, not evidence that an engine will select it.

### Claim support

Trace material claims to current, scope-matched evidence. Distinguish first-party documentation, standards, direct observations, original research, and secondary context. Surface stale, inaccessible, or contradictory support.

### Entity consistency

Check names, aliases, attributes, and disambiguation inside the answer. Broad entity prominence and third-party mention strategy belong to `seo-geo`.

### Visible and structured content

When a structured-data capture is supplied, compare its claims with visible content. Record mismatches and hand off syntax, eligibility, and generation work to `seo-schema`. Do not invent markup.

## Myth-resistance gate

Decline any requested mandatory rule that lacks evidence scoped to the engine, surface, locale, and observation window. Common examples include fixed passage lengths, fixed first-sentence limits, a universal AEO score, guaranteed citation uplift, mandatory `llms.txt`, blanket crawler directives, and correlation presented as causation.

## Recommendation gate

Every recommendation must:

- link to one or more findings;
- carry its own resolved evidence references;
- overlap the evidence of every linked finding and remain compatible with the linked scope;
- state an outcome rather than prescribe unsupported copy;
- use an approved implementation owner;
- include confidence and a verification method;
- remain non-mandatory when supported only by experimental or speculative evidence.

Speculative evidence never supports an implementation recommendation. Experimental evidence belongs in an experiment unless independently supported by stronger evidence. If evidence is insufficient, create a limitation, gap, experiment, declined claim, or research backlog item instead of an implementation recommendation.
