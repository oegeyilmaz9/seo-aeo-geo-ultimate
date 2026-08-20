# Claude Plugin Submission

This repository is already the public source package for the Claude Code plugin. It contains no hooks, MCP servers, background monitors, credentials, telemetry, or automatic network actions. It ships 27 shared instruction skills, their evidence contracts, and local validation helpers.

## Your only submission steps

1. Sign in with the account that will own the listing.
2. Open either the [Claude.ai plugin submission form](https://claude.ai/settings/plugins/submit) or the [Claude Console submission form](https://platform.claude.com/plugins/submit).
3. Submit this public repository: `https://github.com/oegeyilmaz9/seo-aeo-geo-ultimate`.
4. Accept the directory terms and submit.

Anthropic asks for a public GitHub source and a passing `claude plugin validate` check. The repository CI runs an offline structural preflight, while Anthropic runs its own validation during submission. If you later install Claude Code, `claude plugin validate .` is the matching local command; it is not a separate requirement for preparing this repository.

## Ready-to-paste listing copy

**Name**

```text
SEO-AEO-GEO Ultimate
```

**Short description**

```text
One autonomous SEO, AEO, GEO, and AI-search router that screens and coordinates 27 evidence-first specialist skills.
```

**Long description**

```text
SEO-AEO-GEO Ultimate lets a user describe the desired outcome without knowing SEO, AEO, GEO, specialist names, artifacts, or handoff order. Its autonomous router screens all 27 skills, executes every applicable workflow, carries evidence and intermediate results internally, and returns one consolidated outcome to the authorized boundary. The specialist system covers technical SEO, content, architecture, commerce, local, video, news, agentic journeys, answer readiness, entity and authority evidence, search performance, AI visibility, optional llms.txt publisher guides, action planning, implementation, and live verification. Shared contracts preserve evidence, ownership, approval, verification, and rollback while every specialist remains directly usable by experts.
```

**Security and data-access note**

```text
This is a skills-only plugin. It declares no MCP servers, hooks, background monitors, credentials, telemetry, or automatic network actions. It contains Markdown instructions, local schemas, and optional local validation scripts. Users remain in control of any research, browsing, files, and implementation work performed in their own Claude Code session.
```

**Keywords**

```text
SEO, AEO, GEO, AI search, agent skills, Claude Code, Codex, technical SEO, llms.txt
```

**Supported platforms**

```text
Claude Code
```

Select Claude Code only for this submission. Claude Cowork is not declared or tested by this package.

**License type**

```text
Apache 2.0
```

**Privacy policy URL**

Leave blank. It is optional, and this skills-only plugin does not collect or transmit data by itself.

**Contact email**

```text
o.egeyilmaz@gmail.com
```

## After approval

The plugin directory is community-contributed, but Claude Code exposes approved listings through Anthropic's official, automatically available `claude-plugins-official` marketplace. Once listed, users install this plugin with:

```text
/plugin install seo-aeo-geo-ultimate@claude-plugins-official
```

If Claude Code cannot find the listing, refresh the catalog with `/plugin marketplace update claude-plugins-official`; only a client missing the built-in marketplace needs `/plugin marketplace add anthropics/claude-plugins-official`. New commits pushed to this public repository are screened and picked up automatically, so ordinary updates do not require a second submission.

The repository's own marketplace remains a separate direct-distribution path:

```text
/plugin marketplace add oegeyilmaz9/seo-aeo-geo-ultimate
/plugin install seo-aeo-geo-ultimate@oegeyilmaz9-skills
```

See the [official submission guidance](https://claude.com/docs/plugins/submit), [plugin discovery and installation guide](https://code.claude.com/docs/en/discover-plugins), and [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) for current platform rules.
