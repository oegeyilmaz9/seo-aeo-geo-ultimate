#!/usr/bin/env python3
"""Export reviewed public Markdown with complete maps and verify exact delivery.

No crawling, HTML extraction, editorial approval, deployment or indexing claim.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from install_runtime import assert_safe_existing_path, paths_overlap
from validate_llms_txt import public_https_url, resolved_public_addresses, PinnedHTTPSConnection

LINK = re.compile(r"\[[^\]\n]*\]\(([^\s)]+)\)")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def markdown_links(source: str) -> list[str]:
    """Collect inline and reference destinations, excluding literal code examples."""
    source = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', source)
    source = re.sub(r'(`+)[^`\n]*?\1', '', source)
    definitions = dict((label.strip().casefold(), target) for label, target in
                       re.findall(r'^ {0,3}\[([^\]\n]+)\]:\s*<?([^\s>]+)>?', source, re.M))
    targets = LINK.findall(source) + list(definitions.values())
    for label, reference in re.findall(r'\[([^\]\n]+)\]\[([^\]\n]*)\]', source):
        key = (reference or label).strip().casefold()
        if key not in definitions:
            raise ValueError(f'unresolved Markdown reference: {key}')
        targets.append(definitions[key])
    return targets


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n|[]<>"):
        raise ValueError(f"{label}: expected nonempty single-line text without Markdown delimiters")
    return value.strip()


def safe_url(value: str) -> str:
    errors: list[str] = []
    public_https_url(value, "URL", errors)
    p = urlsplit(value)
    if errors or p.query or p.fragment or any(c.isspace() for c in value) or "\\" in value:
        raise ValueError(f"invalid public canonical URL: {value}")
    return value


def relative(value: str) -> str:
    p = Path(value)
    if not value or p.is_absolute() or "\\" in value or ":" in value or any(x in ("..", ".", "") for x in value.split("/")):
        raise ValueError(f"unsafe relative path: {value}")
    return value


def local(root: Path, value: str) -> Path:
    candidate = root / relative(value)
    assert_safe_existing_path(candidate, "local source/output")
    candidate.resolve().relative_to(root.resolve())
    return candidate


def load_inventory(path: Path) -> dict:
    assert_safe_existing_path(path, "inventory")
    inv = read_json(path)
    if inv.get("schema_version") != "1.0.0" or inv.get("inventory_scope") not in ("complete", "partial"):
        raise ValueError("inventory requires schema_version 1.0.0 and complete/partial inventory_scope")
    for field in ("site_name", "summary", "owner", "inventory_evidence", "refresh_trigger"):
        text(inv.get(field), field)
    origin = safe_url(inv["origin"]).rstrip("/")
    if urlsplit(origin).path or urlsplit(origin).port not in (None, 443):
        raise ValueError("origin must be a public HTTPS origin without path or nonstandard port")
    if inv.get("index_policy") not in ("canonical-to-html", "independent", "noindex"):
        raise ValueError("declare index_policy; headers are applied and verified by the technical owner")
    pages = inv.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("inventory pages must not be empty")
    ids, urls, routes = set(), set(), {"sitemap.md", "llms.txt"}
    eligible = 0
    for page in pages:
        pid = page.get("id", "")
        if not SLUG.fullmatch(pid) or pid in ids:
            raise ValueError(f"invalid/duplicate page id: {pid}")
        ids.add(pid)
        url = safe_url(page["url"])
        if urlsplit(url).netloc != urlsplit(origin).netloc or url in urls:
            raise ValueError(f"off-origin/duplicate inventory URL: {url}")
        urls.add(url)
        if page.get("disposition") == "exclude":
            text(page.get("reason"), "exclusion reason")
            continue
        if page.get("disposition") != "publish" or page.get("reviewed_public") is not True:
            raise ValueError(f"{pid}: unresolved disposition or missing public-content review")
        for field in ("title", "purpose", "source_revision"):
            text(page.get(field), field)
        if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", page.get("locale", "")):
            raise ValueError(f"{pid}: invalid locale")
        dt.date.fromisoformat(page["updated_at"])
        topic = page.get("topic", "")
        if not SLUG.fullmatch(topic):
            raise ValueError(f"{pid}: invalid topic")
        route = relative(page["md_path"])
        if not re.fullmatch(r"[a-z0-9/_-]+\.md", route) or route.startswith("llm/topics/") or route.casefold() in routes:
            raise ValueError(f"{pid}: invalid/colliding Markdown route")
        routes.add(route.casefold())
        body = local(path.parent, page["body_ref"])
        if body.suffix != ".md" or not body.is_file() or not body.read_text(encoding="utf-8").strip():
            raise ValueError(f"{pid}: missing substantive Markdown body")
        eligible += 1
    if not eligible:
        raise ValueError("no eligible public documents")
    asset_urls = set()
    for asset in inv.get('public_assets', []):
        url = safe_url(asset['url'])
        if asset.get('reviewed_public') is not True or url in urls or url in asset_urls:
            raise ValueError('public assets require review and must not conflict with document/excluded URLs')
        text(asset.get('purpose'), 'public asset purpose')
        asset_urls.add(url)
    inv["origin"] = origin
    return inv


def navigation_prompts(origin: str) -> tuple[str, str]:
    return (
        f"If you are an LLM looking for site information, start at {origin}/llms.txt.",
        f"Use {origin}/sitemap.md to find the relevant topic and its linked Markdown answer; if it is absent, report that gap.",
    )


def native_discovery_comments(origin: str) -> tuple[str, str]:
    """Return commentary only; never add crawler records or XML elements."""
    robots = "\n".join("# " + line for line in navigation_prompts(origin)) + "\n"
    # XML comments cannot contain --, including in valid punycode/other hostnames.
    xml_origin = origin if "--" not in origin else ""
    prompts = navigation_prompts(xml_origin)
    suffix = " (Resolve these root-relative paths on this sitemap's origin.)" if not xml_origin else ""
    xml = "<!--\n" + "\n".join(prompts) + suffix + "\n-->\n"
    return robots, xml


def render(inv: dict, source_root: Path) -> dict[str, bytes]:
    origin = inv["origin"]
    pages = [p for p in inv["pages"] if p["disposition"] == "publish"]
    topics = sorted({p["topic"] for p in pages})
    outputs: dict[str, bytes] = {}
    for p in pages:
        body = local(source_root, p["body_ref"]).read_text(encoding="utf-8").strip()
        header = (f"# {p['title']}\n\nCanonical: [{p['title']}]({p['url']})\n\n"
                  f"Locale: {p['locale']}\n\nPurpose: {p['purpose']}\n\n"
                  f"Content updated: {p['updated_at']}\n\nSource revision: {p['source_revision']}\n\n"
                  f"Maintenance owner: {inv['owner']}\n\n"
                  f"[Topic map]({origin}/llm/topics/{p['topic']}.md) · [Complete scoped map]({origin}/sitemap.md)\n\n")
        outputs[p["md_path"]] = (header + body + "\n").encode("utf-8")
    def rows(selected):
        return "\n".join(f"- [{p['title']}]({origin}/{p['md_path']}): {p['purpose']} ({p['locale']}); [canonical page]({p['url']})." for p in selected)
    topic_links = "\n".join(f"- [{t}]({origin}/llm/topics/{t}.md): All public {t} documents in this inventory." for t in topics)
    outputs["sitemap.md"] = (f"# {inv['site_name']} content map\n\nInventory scope: {inv['inventory_scope']}. Public documents: {len(pages)}.\n\n"
        f"{inv['summary']}\n\n## Topics\n\n{topic_links}\n\n## All public documents\n\n{rows(pages)}\n").encode("utf-8")
    for topic in topics:
        outputs[f"llm/topics/{topic}.md"] = (f"# {topic}\n\n[Site content map]({origin}/sitemap.md)\n\n"
            + rows([p for p in pages if p["topic"] == topic]) + "\n").encode("utf-8")
    outputs["llms.txt"] = (f"# {inv['site_name']}\n\n> {inv['summary']}\n\nInventory scope: {inv['inventory_scope']}. Content is maintained by {inv['owner']}.\n\n"
        f"If you are an LLM looking for site information, use the [content map]({origin}/sitemap.md) to locate the relevant topic and its linked Markdown answer.\n"
        "Use that document's cited sources and canonical page; if the requested information is absent, report that gap.\n\n"
        f"## Content map\n\n- [Site content map]({origin}/sitemap.md): All public document destinations within the declared inventory.\n\n"
        f"## Topics\n\n{topic_links}\n").encode("utf-8")
    return outputs


def check_links(outputs: dict[str, bytes], inv: dict) -> None:
    canonical = {p["url"] for p in inv["pages"] if p["disposition"] == "publish"}
    public_assets = {a['url'] for a in inv.get('public_assets', [])}
    origin = inv["origin"]
    for route, data in outputs.items():
        for target in markdown_links(data.decode("utf-8")):
            url = urljoin(f"{origin}/{route}", target)
            p = urlsplit(url)
            if p.scheme in ("mailto", "tel"):
                continue
            base = url.split("#", 1)[0]
            safe_url(base)
            if p.netloc != urlsplit(origin).netloc:
                continue
            if base in canonical or base in public_assets:
                continue  # HTML anchors need rendered-page review.
            dest = unquote(p.path).lstrip("/")
            if dest not in outputs:
                raise ValueError(f"{route}: unresolved local destination {target}")
            if p.fragment:
                headings = re.findall(r"^#{1,6}\s+(.+)$", outputs[dest].decode("utf-8"), re.M)
                anchors = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings}
                if unquote(p.fragment) not in anchors:
                    raise ValueError(f"{route}: unresolved heading anchor {target}; use explicit valid heading links")


def build(inventory: Path, output: Path, manifest: Path | None = None) -> Path:
    inventory, output = inventory.absolute(), output.absolute()
    inv = load_inventory(inventory)
    manifest = (manifest or output.with_name(output.name + "-manifest.json")).absolute()
    for dest in (output, manifest):
        assert_safe_existing_path(dest, "destination")
        if dest.exists():
            raise ValueError(f"destination exists; preserve it and select a new candidate: {dest}")
    if paths_overlap(output, inventory.parent) or paths_overlap(output, manifest):
        raise ValueError("public output must be separate from the private source/manifest directory")
    outputs = render(inv, inventory.parent)
    check_links(outputs, inv)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".markdown-stage-", dir=output.parent))
    try:
        for route, data in outputs.items():
            dest = stage / route
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        source_paths = sorted({str(local(inventory.parent, p["body_ref"])) for p in inv["pages"] if p["disposition"] == "publish"})
        source_rows = [{"path": path, "sha256": sha(Path(path).read_bytes())} for path in source_paths]
        payload = {"manifest_version": "1.0.0", "inventory_path": str(inventory), "inventory_sha256": sha(inventory.read_bytes()),
                   "sources": source_rows, "outputs": [{"path": route, "url": f"{inv['origin']}/{route}", "sha256": sha(data)} for route, data in outputs.items()],
                   "status": "generated-candidate", "limitations": ["Editorial truth and HTML parity require owner review.", "Inventory completeness is declared, not independently established.", "No live delivery or engine outcome established."]}
        stage.rename(output)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    finally:
        if stage.exists():
            stage.resolve().relative_to(output.parent.resolve())
            assert_safe_existing_path(stage, "owned temporary stage")
            if not stage.name.startswith(".markdown-stage-") or stage.resolve() == output.parent.resolve():
                raise ValueError("temporary cleanup target is not the owned stage")
            shutil.rmtree(stage)
    return manifest


def validate(manifest: Path, root: Path) -> dict:
    assert_safe_existing_path(manifest, "manifest")
    assert_safe_existing_path(root, "public root")
    payload = read_json(manifest)
    if payload.get("manifest_version") != "1.0.0":
        raise ValueError("unsupported manifest version")
    inventory = Path(payload["inventory_path"])
    assert_safe_existing_path(inventory, "inventory")
    if sha(inventory.read_bytes()) != payload["inventory_sha256"]:
        raise ValueError("inventory changed since build")
    inv = load_inventory(inventory)
    expected = render(inv, inventory.parent)
    rows = payload["outputs"]
    if len(rows) != len(expected) or {r["path"] for r in rows} != set(expected):
        raise ValueError("manifest output coverage mismatch")
    expected_sources = {str(local(inventory.parent, p["body_ref"])) for p in inv["pages"] if p["disposition"] == "publish"}
    if len(payload["sources"]) != len(expected_sources) or {s["path"] for s in payload["sources"]} != expected_sources:
        raise ValueError("manifest source coverage mismatch")
    for row in payload["sources"]:
        path = Path(row["path"])
        assert_safe_existing_path(path, "source")
        if sha(path.read_bytes()) != row["sha256"]:
            raise ValueError(f"source changed: {path}")
    for row in rows:
        data = local(root, row["path"]).read_bytes()
        if data != expected[row["path"]] or sha(data) != row["sha256"] or row["url"] != f"{inv['origin']}/{row['path']}":
            raise ValueError(f"output mismatch: {row['path']}")
    # Unexpected files could accidentally publish private inputs.
    actual = set()
    for p in root.rglob("*"):
        assert_safe_existing_path(p, "public file")
        if p.is_file():
            actual.add(p.relative_to(root).as_posix())
    if actual != set(expected):
        raise ValueError("unexpected public files or incomplete public tree")
    check_links(expected, inv)
    return payload


def fetch_exact(url: str, timeout: float, max_bytes: int = 5_000_000) -> tuple[int, str, bytes, dict[str, str]]:
    safe_url(url)
    p = urlsplit(url)
    addresses = resolved_public_addresses(url)
    connection = PinnedHTTPSConnection(p.hostname, p.port or 443, addresses[0], timeout)
    try:
        connection.request("GET", p.path or "/", headers={"Accept": "text/markdown,text/plain", "User-Agent": "seo-markdown-delivery/1.0"})
        response = connection.getresponse()
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("response exceeds 5 MB delivery-check limit")
        return response.status, response.headers.get("Content-Type", ""), data, {k.lower(): ', '.join(response.headers.get_all(k)) for k in response.headers.keys()}
    finally:
        connection.close()


def live(manifest: Path, root: Path, report: Path, timeout: float, fetcher=fetch_exact) -> bool:
    payload = validate(manifest, root)
    inv = load_inventory(Path(payload['inventory_path']))
    page_owners = {p['md_path']: p['url'] for p in inv['pages'] if p['disposition'] == 'publish'}
    assert_safe_existing_path(report, "private report")
    if report.exists() or paths_overlap(root, report):
        raise ValueError("report must be a new private file outside public root")
    lines = ["# Markdown live delivery", "", f"Checked: {dt.datetime.now(dt.timezone.utc).isoformat()}", "",
             "Scope: every generated public resource. No engine outcome inferred.", ""]
    passed = True
    for row in payload["outputs"]:
        try:
            status, content_type, data, headers = fetcher(row["url"], timeout)
            mime = content_type.split(";", 1)[0].strip().lower()
            data.decode("utf-8")
            charset = re.search(r'charset\s*=\s*["\']?([^;"\'\s]+)', content_type, re.I)
            encoding_ok = not charset or charset.group(1).lower() in ('utf-8', 'utf8')
            policy_ok = True
            owner = page_owners.get(row['path'])
            if owner and inv['index_policy'] == 'canonical-to-html':
                canonicals = re.findall(r'<([^>]+)>\s*;\s*rel\s*=\s*["\']?canonical["\']?',headers.get('link',''),re.I)
                policy_ok = canonicals == [owner] and not re.search(r'\bnoindex\b',headers.get('x-robots-tag',''),re.I)
            elif owner and inv['index_policy'] == 'noindex':
                policy_ok = bool(re.search(r'\bnoindex\b',headers.get('x-robots-tag',''),re.I))
            ok = status == 200 and mime in ("text/markdown", "text/plain") and encoding_ok and policy_ok and sha(data) == row["sha256"]
            lines.append(f"- {'PASS' if ok else 'FAIL'} [{row['path']}]({row['url']}): HTTP {status}, type `{content_type}`, indexing policy {'PASS' if policy_ok else 'FAIL'}, SHA-256 `{sha(data)}`.")
            passed &= ok
            if status in (401, 403, 429) or status >= 500:
                lines.append("- Remaining resources NOT_RUN: access/rate/provider failure; resume only after resolution.")
                passed = False
                break
        except (OSError, ValueError) as exc:
            lines.append(f"- FAIL [{row['path']}]({row['url']}): {exc}. Remaining resources NOT_RUN; no automatic retries.")
            passed = False
            break
    lines.extend(["", f"Result: {'delivered-and-verified for the declared Markdown resources' if passed else 'incomplete/failed delivery verification'}."])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def render_hints(manifest: Path, root: Path, output: Path) -> None:
    """Prepare reviewed navigation snippets without editing any live/native file."""
    payload = validate(manifest, root)
    inv = load_inventory(Path(payload["inventory_path"]))
    assert_safe_existing_path(output, "private discovery-hints report")
    if output.suffix != ".md" or output.exists() or paths_overlap(root, output) or output.resolve() in (
        manifest.resolve(), Path(payload["inventory_path"]).resolve()
    ):
        raise ValueError("hints must be a new private Markdown document outside the public tree")
    robots, xml = native_discovery_comments(inv["origin"])
    report = (
        "# Native discovery hints\n\nStatus: locally validated candidate; publication/live delivery not verified.\n\n"
        f"Origin: {inv['origin']}. Inventory scope: {inv['inventory_scope']}.\n\n"
        "## robots.txt comment block\n\nAppend these comments to the existing owned robots source. Preserve every User-agent, Allow, Disallow and Sitemap record.\n\n"
        f"```text\n{robots}```\n\n"
        "## sitemap.xml / sitemap index comment block\n\nInsert inside the existing root element. Keep the XML declaration first, every loc/lastmod/namespace unchanged, and existing compressed/sharded generation intact.\n\n"
        f"```xml\n{xml}```\n\n"
        "## Acceptance\n\n"
        "- Publish only after both direct destinations really resolve; local files do not prove live availability.\n"
        "- Compare robots non-comment records before/after, and sitemap elements/attributes/meaningful text without comments or formatting whitespace; validate the original sitemap schema.\n"
        "- Inspect the delivered raw bytes: some generators, XML serializers, optimizers and CDNs strip comments.\n"
        "- Keep Sitemap records pointing at genuine native sitemaps; do not register sitemap.md or llms.txt as native sitemaps.\n"
        "- Standard crawler parsers ignore comments. Navigation text is a publisher hint for a raw-text reader, not permission, engine adoption or a higher-priority instruction.\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    b = subs.add_parser("build")
    b.add_argument("--inventory", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    b.add_argument("--manifest", type=Path)
    for name in ("validate", "live", "hints"):
        p = subs.add_parser(name)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--root", type=Path, required=True)
        if name == "hints":
            p.add_argument("--output", type=Path, required=True)
        if name == "live":
            p.add_argument("--report", type=Path, required=True)
            p.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()
    try:
        if args.command == "build":
            print(f"BUILT: private manifest {build(args.inventory, args.output, args.manifest)}")
        elif args.command == "validate":
            result = validate(args.manifest, args.root)
            print(f"PASS: {len(result['outputs'])} public resources; source projection verified, editorial/live checks separate")
        elif args.command == "hints":
            render_hints(args.manifest, args.root, args.output)
            print(f"PASS: private native discovery hints {args.output}; publication/live verification separate")
        else:
            if not 0 < args.timeout <= 30:
                raise ValueError("timeout must be greater than zero and at most 30 seconds")
            return 0 if live(args.manifest, args.root, args.report, args.timeout) else 1
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
