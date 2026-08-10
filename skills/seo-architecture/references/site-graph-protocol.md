# Site graph protocol

Every node records stable ID, canonical URL, target type, locale, status, index intent, title, capture reference, observed time, and business/user role. Its hash-pinned metadata envelope must repeat the observable node fields and bind them to the exact body capture. Every edge records stable ID, source/target node, raw href, link location, anchor/accessibility name, follow state, rendered or raw discovery, template/context classification, and capture reference. Its own hash-pinned metadata envelope binds those claims to the source capture; the validator also requires a real parsed anchor whose context and `rel` state agree. One graph uses one evidence mode: raw or rendered. Compare modes with two separately captured and validated graphs; never label one capture as both.

Preserve crawl seeds, excluded patterns, maximum scope, collection method, and incomplete coverage. "Orphan" requires no inbound edge in the bounded graph plus an explicit limitation; it is not proof that no external or unobserved link exists.

Architecture recommendations must name the user task, destination ownership, source templates, expected discovery path, rollout sample, verification recrawl, and rollback.
