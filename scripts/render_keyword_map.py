#!/usr/bin/env python3
"""Render a validated Query Corpus with exact canonical/Markdown destinations.

This is evidence-preserving mapping, not automated keyword research or scoring.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from manage_markdown_site import load_inventory, read_json, sha, validate as validate_site
from render_artifact_report import validate as validate_artifact
from install_runtime import assert_safe_existing_path, paths_overlap


def cell(value) -> str:
    if value is None:
        return 'unavailable'
    return str(value).replace('|', '\\|').replace('\n',' ').replace('\r',' ')


def render(corpus: Path, bundle: Path, manifest: Path, public_root: Path, output: Path) -> None:
    for path in (corpus,bundle,manifest,public_root,output):
        assert_safe_existing_path(path,'keyword input/output')
    if output.suffix != '.md' or output.exists() or paths_overlap(output,public_root):
        raise ValueError('keyword map must be a new private Markdown file outside the public tree')
    data=read_json(corpus)
    validate_artifact('query-corpus',corpus,bundle,data,None)
    site=validate_site(manifest,public_root)
    inv=load_inventory(Path(site['inventory_path']))
    pages={p['url']:p for p in inv['pages'] if p['disposition']=='publish'}
    lines=['# Keyword and answer destination map','',f"Corpus: `{data['corpus_id']}`. SHA-256: `{sha(corpus.read_bytes())}`.",'',
           f"Declared query scope: {data['scope']}",'',
           'Validated corpus and local Markdown projection. Editorial intent decisions and live availability remain separate. No volume, rank or AI fan-out is inferred.','',
           '| Query / need IDs | Type / reader task / intent | Locale / market / device | Evidence and collection date | Demand | Canonical HTML owner | Markdown answer destination | Topic map | Coverage / competitors |',
           '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    missing=[]
    for q in data['queries']:
        coverage=q['coverage']; url=coverage['target_url']; page=pages.get(url)
        if url and not page:
            missing.append(q['query_id'])
        source=q['source']; demand=q['demand']
        evidence=f"{source['source_kind']}; {source['observed_at']}; {source.get('source_url') or source.get('source_ref') or 'no public source'}"
        demand_text=f"{demand['status']}; provider={cell(demand['provider'])}; monthly={cell(demand['monthly_volume'])}; trend={cell(demand['trend_index'])}; difficulty={cell(demand['difficulty'])}; date={cell(demand['observed_at'])}"
        md=f"{inv['origin']}/{page['md_path']}" if page else 'planned/unresolved; not a fetchable claim'
        topic=f"{inv['origin']}/llm/topics/{page['topic']}.md" if page else 'unresolved'
        cols=[f"{q['query_id']} / {q['need_id']}",f"{q['query_type']} / {q['text']} / {q['intent']}",
              f"{q['locale']} / {q['country']} / {q['location']} / {q['device']}",evidence,demand_text,url,md,topic,
              f"{coverage['state']}; competing={', '.join(coverage['competing_urls']) or 'none declared'}"]
        lines.append('| '+' | '.join(cell(c) for c in cols)+' |')
    lines.extend(['','## Limits and next decisions',''])
    for limitation in data['limitations']:
        lines.append('- '+limitation)
    for q in data['queries']:
        for limitation in q['limitations']+q['demand']['limitations']:
            lines.append(f"- `{q['query_id']}`: {limitation}")
    if missing:
        lines.append('- Canonical owners absent from this public inventory: '+', '.join(missing)+'. Collect/approve their content before claiming answer coverage.')
    lines.append('- Complete keyword-decisions.md with source-linked SERP intent, primary/supporting clusters, answer section, action/no-action, cannibalization rationale, two ambition tracks, owner, priority and refresh trigger. This rendered map is an input to those decisions, not a claim of market completeness.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        f.write('\n'.join(lines)+'\n')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('corpus','bundle','manifest','public-root','output'):
        parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args()
    try:
        render(args.corpus,args.bundle,args.manifest,args.public_root,args.output)
        print(f'PASS: private keyword destination map {args.output}; decision gaps remain explicit')
        return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
