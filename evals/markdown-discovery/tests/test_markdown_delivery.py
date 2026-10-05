from __future__ import annotations
import copy
import json
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
import manage_markdown_site as site
import manage_markdown_work as work
import render_keyword_map as keywords


class MarkdownDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private = self.root/'private'
        shutil.copytree(ROOT/'examples/markdown-discovery', self.private)
        self.inventory = self.private/'inventory.json'
        self.public = self.root/'public'
        self.inv = json.loads(self.inventory.read_text())

    def tearDown(self):
        self.temp.cleanup()

    def change(self, inv):
        self.inventory.write_text(json.dumps(inv), encoding='utf-8')

    def build(self):
        return site.build(self.inventory, self.public)

    def test_complete_maps_answer_navigation_and_private_exclusions(self):
        manifest = self.build()
        result = site.validate(manifest, self.public)
        self.assertEqual(len(result['outputs']), 5)
        for file in self.public.rglob('*'):
            if file.is_file():
                self.assertNotIn('private-account', file.read_text(encoding='utf-8'))
        # A reader starting only at llms.txt can locate both substantive answers.
        llms = (self.public/'llms.txt').read_text()
        self.assertIn('/sitemap.md', llms)
        content_map = (self.public/'sitemap.md').read_text()
        self.assertIn('/llm/pages/support.md', content_map)
        self.assertIn('Supported questions', (self.public/'llm/pages/support.md').read_text())

    def test_source_update_requires_rebuild(self):
        manifest = self.build()
        (self.private/'source/support.md').write_text('Updated facts', encoding='utf-8')
        with self.assertRaises(ValueError):
            site.validate(manifest, self.public)

    def test_navigation_prompts_and_native_comments_preserve_protocol_meaning(self):
        manifest = self.build()
        llms = (self.public/'llms.txt').read_text()
        self.assertIn('If you are an LLM', llms)
        self.assertIn('report that gap', llms)
        robots, xml = site.native_discovery_comments(self.inv['origin'])
        original = 'User-agent: *\nDisallow: /private/\nSitemap: https://example.com/sitemap.xml\nUser-agent: ExampleBot\nDisallow: /draft/\n'
        active = lambda value: [line for line in value.splitlines() if line and not line.startswith('#')]
        self.assertEqual(active(original+robots), active(original))
        before = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc><lastmod>2026-10-03</lastmod></url></urlset>'
        after = before.replace('<url>',xml+'<url>',1)
        semantic = lambda value: [(node.tag,node.attrib,node.text if node.text and node.text.strip() else None)
                                  for node in ET.fromstring(value).iter()]
        self.assertEqual(semantic(before),semantic(after))
        self.assertIn('/llms.txt', robots)
        self.assertIn('/sitemap.md', xml)
        site.validate(manifest,self.public)

    def test_xml_hint_handles_valid_double_hyphen_host(self):
        robots, xml = site.native_discovery_comments('https://xn--example-domain.com')
        self.assertIn('https://xn--example-domain.com/llms.txt',robots)
        self.assertIn('/llms.txt',xml)
        self.assertNotIn('--',xml[4:-4])
        ET.fromstring('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+xml+'<sitemap><loc>https://xn--example-domain.com/main.xml</loc></sitemap></sitemapindex>')

    def test_hints_are_private_candidate_with_no_excluded_urls_or_mutation(self):
        manifest = self.build()
        before = {p.relative_to(self.public):p.read_bytes() for p in self.public.rglob('*') if p.is_file()}
        report = self.root/'native-hints.md'
        site.render_hints(manifest,self.public,report)
        body=report.read_text()
        self.assertIn('locally validated candidate',body)
        self.assertIn('Standard crawler parsers ignore comments',body)
        self.assertNotIn('private-account',body)
        self.assertEqual(before,{p.relative_to(self.public):p.read_bytes() for p in self.public.rglob('*') if p.is_file()})

    def test_hints_refuse_overwrite_or_public_work_report(self):
        manifest=self.build()
        existing=self.root/'manual.md'
        existing.write_text('Preserve manual notes')
        for output in (existing,self.public/'hints.md',self.root/'wrong.txt'):
            with self.assertRaises(ValueError):
                site.render_hints(manifest,self.public,output)
        self.assertEqual(existing.read_text(),'Preserve manual notes')

    def test_hints_require_real_validated_local_destinations(self):
        manifest=self.build()
        (self.public/'sitemap.md').unlink()
        report=self.root/'native-hints.md'
        with self.assertRaises(OSError):
            site.render_hints(manifest,self.public,report)
        self.assertFalse(report.exists())

    def test_wrong_output_or_spa_fallback_cannot_pass(self):
        manifest = self.build()
        (self.public/'llm/pages/support.md').write_text('<html>SPA shell</html>')
        with self.assertRaises(ValueError):
            site.validate(manifest, self.public)

    def test_manifest_cannot_omit_a_public_document(self):
        manifest = self.build()
        data = json.loads(manifest.read_text())
        data['outputs'].pop()
        manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            site.validate(manifest, self.public)

    def test_unknown_or_unreviewed_urls_block_generation(self):
        for field, value in [('disposition','unknown'), ('reviewed_public',False)]:
            inv = copy.deepcopy(self.inv)
            inv['pages'][0][field] = value
            self.change(inv)
            with self.assertRaises(ValueError):
                self.build()

    def test_path_traversal_and_reserved_route_collision(self):
        for route in ('../leak.md','sitemap.md','llm/topics/documentation.md'):
            inv = copy.deepcopy(self.inv)
            inv['pages'][0]['md_path'] = route
            self.change(inv)
            with self.assertRaises(ValueError):
                self.build()

    def test_bad_answer_link_blocks_generation(self):
        with (self.private/'source/support.md').open('a') as f:
            f.write('\n[Missing](https://example.com/llm/pages/missing.md)\n')
        with self.assertRaises(ValueError):
            self.build()

    def test_bad_heading_link_blocks_generation(self):
        p = self.private/'source/overview.md'
        p.write_text(p.read_text().replace('#supported-questions','#missing-heading'))
        with self.assertRaises(ValueError):
            self.build()

    def test_literal_code_links_do_not_become_navigation_requirements(self):
        with (self.private/'source/support.md').open('a') as f:
            f.write('\n```markdown\n[Literal example](https://example.com/does-not-exist.md)\n```\n')
        site.validate(self.build(), self.public)

    def test_reference_links_are_checked_and_missing_references_fail(self):
        p=self.private/'source/support.md'
        p.write_text(p.read_text()+'\n[Answer][destination]\n\n[destination]: https://example.com/missing.md\n')
        with self.assertRaises(ValueError):
            self.build()

    def test_reviewed_native_media_destination_is_preserved(self):
        self.inv['public_assets']=[{'url':'https://example.com/images/diagram.png','purpose':'Public diagram','reviewed_public':True}]
        self.change(self.inv)
        with (self.private/'source/support.md').open('a') as f:
            f.write('\n![Diagram meaning](https://example.com/images/diagram.png)\n')
        site.validate(self.build(),self.public)

    def test_media_exception_cannot_publish_an_excluded_account_url(self):
        self.inv['public_assets']=[{'url':'https://example.com/private-account','purpose':'Account','reviewed_public':True}]
        self.change(self.inv)
        with self.assertRaises(ValueError):
            self.build()

    def test_existing_candidate_is_preserved(self):
        self.public.mkdir()
        manual = self.public/'manual.md'
        manual.write_text('Preserve this work')
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(manual.read_text(), 'Preserve this work')

    def test_partial_inventory_is_visibly_partial(self):
        self.inv['inventory_scope'] = 'partial'
        self.change(self.inv)
        self.build()
        self.assertIn('Inventory scope: partial', (self.public/'sitemap.md').read_text())

    def test_live_checks_entire_universe_and_exact_bodies(self):
        manifest = self.build()
        calls = []
        def fetch(url, timeout):
            calls.append(url)
            route = url.split('example.com/',1)[1]
            headers = {'link': '<https://example.com/overview>; rel="canonical"'} if route.endswith('overview.md') else {'link': '<https://example.com/support>; rel="canonical"'}
            return 200, 'text/markdown; charset=utf-8', (self.public/route).read_bytes(), headers
        report = self.private/'live.md'
        self.assertTrue(site.live(manifest,self.public,report,5,fetch))
        self.assertEqual(len(calls), 5)
        self.assertIn('delivered-and-verified',report.read_text())

    def test_live_rejects_html_and_wrong_content_without_fake_success(self):
        manifest = self.build()
        def fetch(url, timeout):
            return 200, 'text/html', b'<html>challenge</html>', {}
        report = self.private/'live.md'
        self.assertFalse(site.live(manifest,self.public,report,5,fetch))
        self.assertIn('incomplete/failed',report.read_text())

    def test_live_rate_limit_stops_without_retries(self):
        manifest = self.build()
        calls = []
        def fetch(url, timeout):
            calls.append(url)
            return 429,'text/plain',b'limited',{}
        self.assertFalse(site.live(manifest,self.public,self.private/'live.md',5,fetch))
        self.assertEqual(len(calls),1)

    def test_live_rejects_missing_or_wrong_canonical_policy(self):
        manifest=self.build()
        def fetch(url,timeout):
            route=url.split('example.com/',1)[1]
            return 200,'text/markdown; charset=utf-8',(self.public/route).read_bytes(),{}
        self.assertFalse(site.live(manifest,self.public,self.private/'missing-canonical.md',5,fetch))

    def test_live_verifies_explicit_noindex_profile(self):
        self.inv['index_policy']='noindex';self.change(self.inv)
        manifest=self.build()
        def fetch(url,timeout):
            route=url.split('example.com/',1)[1]
            return 200,'text/markdown; charset=utf-8',(self.public/route).read_bytes(),{'x-robots-tag':'noindex'}
        self.assertTrue(site.live(manifest,self.public,self.private/'noindex.md',5,fetch))

    def test_work_index_rejects_untracked_stale_and_unresolved_steps(self):
        root = self.root/'work'
        root.mkdir()
        work.save(root,{'ledger_version':'1.0.0','title':'Research','steps':[]})
        doc = root/'research.md'
        doc.write_text('# Research\n\nActual scope, evidence and decisions.\n')
        work.register(root,'research','research.md','Research','provisional','Owner','Evidence gap')
        with self.assertRaises(ValueError):
            work.check(root,True)
        work.register(root,'research','research.md','Research','completed','Owner','Scoped research complete')
        work.check(root,True)
        extra = root/'unregistered.md'; extra.write_text('# Lost work')
        with self.assertRaises(ValueError):
            work.check(root,True)
        extra.unlink()
        doc.write_text('# Changed without re-registration')
        with self.assertRaises(ValueError):
            work.check(root,True)

    def test_work_index_rejects_broken_direct_destinations(self):
        root = self.root/'work'; root.mkdir()
        work.save(root,{'ledger_version':'1.0.0','title':'Work','steps':[]})
        (root/'step.md').write_text('# Step\n\n[Missing evidence](raw/missing.json)\n')
        work.register(root,'step-id','step.md','Step','completed','Owner','Done')
        with self.assertRaises(ValueError):
            work.check(root,True)

    def test_keyword_map_preserves_unavailable_demand_and_unresolved_destination(self):
        manifest = self.build()
        bundle = ROOT/'examples/ai-search-handoff'
        output = self.private/'keyword-map.md'
        keywords.render(bundle/'query-corpus.json',bundle,manifest,self.public,output)
        note = output.read_text(encoding='utf-8')
        self.assertIn('monthly=unavailable',note)
        self.assertIn('planned/unresolved',note)
        self.assertIn('example-turkey-availability-query',note)
        self.assertNotIn('monthly=0',note)

    def test_keyword_map_resolves_only_actual_eligible_markdown_owner(self):
        self.inv['pages'][0]['url']='https://example.com/docs/availability'
        self.change(self.inv)
        manifest=self.build()
        bundle=ROOT/'examples/ai-search-handoff'
        output=self.private/'keyword-map.md'
        keywords.render(bundle/'query-corpus.json',bundle,manifest,self.public,output)
        note=output.read_text(encoding='utf-8')
        self.assertIn('https://example.com/llm/pages/overview.md',note)
        self.assertNotIn('Canonical owners absent',note)

    def test_keyword_map_rejects_invalid_corpus(self):
        manifest=self.build()
        bundle=self.private/'bundle'
        shutil.copytree(ROOT/'examples/ai-search-handoff',bundle)
        corpus=bundle/'query-corpus.json'
        value=json.loads(corpus.read_text()); value['queries'][0]['demand']['monthly_volume']=5000
        corpus.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            keywords.render(corpus,bundle,manifest,self.public,self.private/'keyword-map.md')

    def test_keyword_map_refuses_public_work_leak_or_overwrite(self):
        manifest=self.build()
        bundle=ROOT/'examples/ai-search-handoff'
        with self.assertRaises(ValueError):
            keywords.render(bundle/'query-corpus.json',bundle,manifest,self.public,self.public/'keyword-map.md')
        output=self.private/'manual.md'; output.write_text('Preserve manual research')
        with self.assertRaises(ValueError):
            keywords.render(bundle/'query-corpus.json',bundle,manifest,self.public,output)
        self.assertEqual(output.read_text(),'Preserve manual research')


if __name__ == '__main__':
    unittest.main()
