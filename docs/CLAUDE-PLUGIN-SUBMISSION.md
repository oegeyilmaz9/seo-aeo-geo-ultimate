# Claude Plugin Submission

This repository is already the public source package for the Claude Code plugin. It contains no hooks, MCP servers, background monitors, credentials, telemetry, or automatic network actions. It ships 19 shared instruction skills, their evidence contracts, and local validation helpers.

## Your only submission steps

1. Create or open a [Claude Console](https://platform.claude.com/) organization with your own account. A personal Claude.ai Free account is not enough for the Claude.ai organization form, but individual authors can submit through Console.
2. Open the [Console plugin submission form](https://platform.claude.com/plugins/submit).
3. Submit this public repository: `https://github.com/oegeyilmaz9/seo-aeo-geo-ultimate`.
4. Accept the directory terms and submit.

Anthropic asks for a public GitHub source and a passing `claude plugin validate` check. The repository CI runs an offline structural preflight, while Anthropic runs its own validation during submission. If you later install Claude Code, `claude plugin validate . --strict` is the matching local command; it is not a separate requirement for preparing this repository.

## Ready-to-paste listing copy

**Name**

```text
SEO-AEO-GEO Ultimate
```

**Short description**

```text
Evidence-first SEO, AEO, GEO, and AI-search workflows for Codex and Claude Code, with one router and 19 specialist skills.
```

**Long description**

```text
SEO-AEO-GEO Ultimate turns an ambiguous search or AI-visibility question into the next right research, audit, measurement, plan, or approved implementation step. Start with one router, then use focused specialist skills for technical SEO, content, schema, international targeting, answer readiness, entity and citation evidence, visibility monitoring, and action planning. The suite keeps evidence, ownership, approval, verification, and rollback connected without promising rankings, citations, traffic, or revenue.
```

**Security and data-access note**

```text
This is a skills-only plugin. It declares no MCP servers, hooks, background monitors, credentials, telemetry, or automatic network actions. It contains Markdown instructions, local schemas, and optional local validation scripts. Users remain in control of any research, browsing, files, and implementation work performed in their own Claude Code session.
```

**Keywords**

```text
SEO, AEO, GEO, AI search, agent skills, Claude Code, Codex, technical SEO
```

## After approval

The community marketplace may take time to reflect an approved submission. Once listed, users add the Anthropic community marketplace and install the plugin with its namespaced command. New commits pushed to this public repository are screened and picked up automatically; do not create a second submission for ordinary updates.

See the [official submission guidance](https://claude.com/docs/plugins/submit) and [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) for current platform rules.
