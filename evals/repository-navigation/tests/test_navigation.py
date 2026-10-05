from pathlib import Path
import sys
import tempfile
import json
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import manage_repository_map as maps


class RepositoryNavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/'manifests').mkdir()
        (self.root/'manifests/suite.json').write_text(json.dumps({'suite_version':'3.3.0'}))
        (self.root/'docs').mkdir()
        (self.root/'docs/guide.md').write_text('# Evidence guide\n\nActual source content.\n')
        (self.root/'README.md').write_text('# Project\n')
        (self.root/'skills/seo').mkdir(parents=True)
        (self.root/'skills/seo/SKILL.md').write_text('# Router\n')

    def tearDown(self): self.temp.cleanup()

    def write(self):
        outputs=maps.render(self.root)
        for name,body in outputs.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
        return outputs

    def test_full_inventory_uses_exact_raw_native_and_markdown_destinations(self):
        self.write()
        outputs=maps.check(self.root)
        all_maps='\n'.join(outputs.values())
        for p in maps.inventory(self.root):
            self.assertIn(maps.BASE+p.relative_to(self.root).as_posix(),all_maps)
        self.assertIn('Native JSON',all_maps)
        self.assertIn('skills/seo/SKILL.md',all_maps)
        self.assertIn('report that gap',outputs['llms.txt'])

    def test_added_removed_or_renamed_resource_requires_regeneration(self):
        self.write()
        (self.root/'docs/guide.md').rename(self.root/'docs/renamed.md')
        with self.assertRaises(ValueError): maps.check(self.root)

    def test_changed_title_requires_map_refresh(self):
        self.write()
        (self.root/'docs/guide.md').write_text('# New contract title\n')
        with self.assertRaises(ValueError): maps.check(self.root)

    def test_missing_topic_and_orphan_map_fail(self):
        self.write()
        (self.root/'docs/maps/stale.md').write_text('Old manual map')
        with self.assertRaises(ValueError): maps.check(self.root)
        (self.root/'docs/maps/stale.md').unlink()
        (self.root/'docs/maps/protocols.md').unlink()
        with self.assertRaises(ValueError): maps.check(self.root)

    def test_cache_files_are_not_published_resources(self):
        p=self.root/'skills/seo/__pycache__/cached.pyc'
        p.parent.mkdir();p.write_bytes(b'cache')
        self.assertNotIn(p,maps.inventory(self.root))

    def test_unclassified_root_resource_blocks_full_coverage_claim(self):
        (self.root/'unreviewed-note.md').write_text('Do not silently omit or publish this')
        with self.assertRaises(ValueError): maps.render(self.root)

    def test_real_repository_has_complete_verified_navigation(self):
        maps.check(ROOT)


if __name__=='__main__': unittest.main()
