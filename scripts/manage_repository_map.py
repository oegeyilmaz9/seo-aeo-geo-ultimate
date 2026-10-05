#!/usr/bin/env python3
"""Generate/check complete public repository navigation without changing source formats."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

from install_runtime import SUPPORT_DIRECTORIES, SUPPORT_FILES, assert_safe_existing_path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/oegeyilmaz9/seo-aeo-geo-ultimate/main/'
MAP_ROOT = 'docs/maps/'
GENERATED = {'sitemap.md', 'llms.txt'}
SKIP = {'__pycache__', '.pytest_cache'}
LOCAL_ONLY = {'.git', 'build', 'dist', '.venv', 'venv', '.coverage', 'htmlcov', 'coverage.xml'}


def inventory(root: Path) -> list[Path]:
    for p in root.iterdir():
        if p.name in set(SUPPORT_DIRECTORIES)|set(SUPPORT_FILES)|SKIP|LOCAL_ONLY or p.name.endswith(('.tmp','.egg-info')):
            continue
        raise ValueError(f'unclassified root resource requires a public/private disposition: {p.name}')
    paths = []
    for name in SUPPORT_FILES:
        p = root/name
        if p.is_file() and name not in GENERATED:
            paths.append(p)
    for name in SUPPORT_DIRECTORIES:
        directory = root/name
        if not directory.exists():
            continue
        assert_safe_existing_path(directory, 'published source directory')
        for p in directory.rglob('*'):
            if any(part in SKIP for part in p.relative_to(root).parts) or p.suffix in ('.pyc', '.pyo'):
                continue
            assert_safe_existing_path(p, 'published repository source')
            if p.is_file() and not p.relative_to(root).as_posix().startswith(MAP_ROOT):
                paths.append(p)
    return sorted(paths, key=lambda p:p.relative_to(root).as_posix())


def topic(path: str) -> str:
    parts=path.split('/')
    if parts[0]=='skills': return 'skill-'+parts[1]
    return {'scripts':'tools','manifests':'contracts','examples':'examples','evals':'tests',
            'docs':'protocols','assets':'assets','.github':'governance','.claude-plugin':'governance'}.get(parts[0],'governance')


def description(p: Path, root: Path) -> str:
    path=p.relative_to(root).as_posix()
    if p.suffix=='.md':
        body=p.read_text(encoding='utf-8-sig')
        match=re.search(r'^#{1,3}\s+(.+)$',body,re.M)
        label=match.group(1) if match else p.stem
    elif p.suffix=='.py': label='Executable source: '+p.stem.replace('_',' ')
    elif p.suffix=='.json': label='Native JSON contract, fixture or dated evidence: '+p.stem
    elif p.suffix in ('.yml','.yaml'): label='Native workflow or agent configuration: '+p.stem
    else: label='Native asset, template or project policy: '+p.name
    label=re.sub(r'[\[\]<>|`\r\n]', '',label)
    if path.endswith('/SKILL.md'): label='Entrypoint and responsibilities: '+path.split('/')[1]
    return label


def render(root: Path) -> dict[str,str]:
    manifest=json.loads((root/'manifests/suite.json').read_text(encoding='utf-8'))
    version=manifest['suite_version']
    groups={}
    for p in inventory(root):
        relative=p.relative_to(root).as_posix()
        groups.setdefault(topic(relative),[]).append((relative,description(p,root)))
    output={}
    maps=[]
    for group,rows in sorted(groups.items()):
        path=f'{MAP_ROOT}{group}.md'
        maps.append((path,group,len(rows)))
        lines=[f'# {group} resource map','',f'Public source files in this topic: {len(rows)}. Native resources keep their existing format.','',
               f'[Full content map]({BASE}sitemap.md) · [LLM entry point]({BASE}llms.txt)','']
        lines += [f'- [{label}]({BASE}{quote(relative,safe="/")}): `{relative}`; '+('readable Markdown document.' if relative.endswith('.md') else 'native source/evidence resource.') for relative,label in rows]
        output[path]='\n'.join(lines)+'\n'
    total=sum(n for _,_,n in maps)
    lines=['# Complete repository content map','',f'Version {version}. Scope: all {total} published source files in the installer\'s declared public roots, plus the generated navigation files listed below.','',
           'Find the reader task in a topic map, then open its exact raw document. Existing Markdown is the answer-bearing representation; code, schemas, assets and fixtures stay native. Test fixtures are illustrative or deliberate negative cases, not current product or engine facts.','',
           '## Start by task','',
           f'- [Turkish guide]({BASE}docs/REHBER-TR.md): What changes, what remains, where to find each workflow.',
           f'- [Markdown quickstart]({BASE}docs/MARKDOWN-QUICKSTART.md): Runnable private-work, public export, hint and keyword-map commands.',
           f'- [Markdown delivery contract]({BASE}docs/MARKDOWN-DISCOVERY.md): Inventory, native entry points, content parity, access and full acceptance.',
           f'- [Keyword decisions]({BASE}skills/seo-research/references/keyword-research-protocol.md): Demand provenance, intent, clusters, owners, gaps and decisions.','',
           '## Complete topic coverage','']
    lines += [f'- [{group}]({BASE}{path}): {n} exact source destinations.' for path,group,n in maps]
    lines += ['', '## Navigation file inventory','',f'- [LLM entry point]({BASE}llms.txt): Site-reader navigation and task links.',f'- [This content map]({BASE}sitemap.md): Complete topic coverage.']
    lines += [f'- [{group} navigation]({BASE}{path}): Generated topic map.' for path,group,_ in maps]
    lines += ['', '## Maintenance and boundaries','',
              'Run `python scripts/manage_repository_map.py --write` after public source changes and `--check` before release. The check recomputes the full declared inventory and every map, detects added/deleted/missing/stale destinations, and fails on orphan generated maps. CI enforces it. Private work artifacts stay outside this repository. GitHub raw delivery and Actions are verified separately after publication. No crawler access control is deployed on github.com by this map.']
    output['sitemap.md']='\n'.join(lines)+'\n'
    llms=['# SEO-AEO-GEO Ultimate','', '> A complete, evidence-first SEO, AEO, GEO and AI-search suite for Codex and Claude Code.','',
          f'Version {version}. Source documents and native artifacts are maintained together. Python 3.11+ is required for the formal tools.',
          'If you are an LLM looking for information, use the content map to select the relevant topic and open its direct Markdown document.',
          "Use that document's cited evidence; if the requested information is absent, report that gap. Example fixtures are not observed engine facts.",'',
          '## Start here','',
          f'- [Complete content map]({BASE}sitemap.md): Every declared public source resource, grouped by topic.',
          f'- [Turkish guide]({BASE}docs/REHBER-TR.md): Plain-language explanation and direct workflow destinations.',
          f'- [Executable Markdown quickstart]({BASE}docs/MARKDOWN-QUICKSTART.md): Local work index, public maps, native hints and keyword ownership.',
          f'- [SEO router]({BASE}skills/seo/SKILL.md): One front door and all 27 lane decisions.',
          f'- [Project README]({BASE}README.md): Installation, capability coverage and validation.','',
          '## Workflow contracts','',
          f'- [Markdown delivery]({BASE}docs/MARKDOWN-DISCOVERY.md): Conventional SEO plus public Markdown parity, complete maps and private work notes.',
          f'- [Keyword protocol]({BASE}skills/seo-research/references/keyword-research-protocol.md): Query evidence, intent, decisions and exact answer ownership.',
          f'- [Provider boundaries]({BASE}docs/PROVIDER-OPERATIONS.md): Actual permissions, submissions and separate outcome evidence.','',
          '## Optional','',
          f'- [License]({BASE}LICENSE): Apache-2.0 terms.',
          f'- [Security]({BASE}SECURITY.md): Vulnerability reporting.',
          f'- [Contributing]({BASE}CONTRIBUTING.md): Contribution and maintenance guidance.']
    output['llms.txt']='\n'.join(llms)+'\n'
    return output


def check(root: Path) -> dict[str,str]:
    expected=render(root)
    actual={p.relative_to(root).as_posix() for p in (root/'docs/maps').glob('*.md')}
    if actual!={p for p in expected if p.startswith(MAP_ROOT)}:
        raise ValueError('missing or orphan generated topic maps')
    for path,body in expected.items():
        destination=root/path
        assert_safe_existing_path(destination,'generated navigation')
        if not destination.is_file() or destination.read_text(encoding='utf-8')!=body:
            raise ValueError(f'stale or missing navigation: {path}; run --write')
    return expected


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write',action='store_true')
    mode.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        if args.write:
            outputs=render(ROOT)
            # Preserve unexpected hand-written maps rather than deleting them.
            extras={p.relative_to(ROOT).as_posix() for p in (ROOT/'docs/maps').glob('*.md')}-set(outputs)
            if extras: raise ValueError(f'orphan maps require an explicit source decision: {sorted(extras)}')
            for relative,body in outputs.items():
                p=ROOT/relative
                assert_safe_existing_path(p,'generated navigation')
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(body,encoding='utf-8')
        else: outputs=check(ROOT)
        print(f'PASS: {len(inventory(ROOT))} public source resources; {len(outputs)} navigation documents')
        return 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
