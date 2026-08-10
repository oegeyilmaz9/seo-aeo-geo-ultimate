from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_claude_plugin.py"


class ClaudePluginValidatorTests(unittest.TestCase):
    def test_claude_package_is_ready_for_validation(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("27 shared skills", completed.stdout)

    def test_plugin_is_skills_only_and_keeps_codex_metadata(self) -> None:
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["skills"], "./skills")
        self.assertFalse({"hooks", "mcpServers", "agents", "lspServers"} & set(plugin))
        skill_paths = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertEqual(len(skill_paths), 27)
        for path in skill_paths:
            self.assertTrue((path / "SKILL.md").is_file())
            self.assertTrue((path / "agents" / "openai.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
