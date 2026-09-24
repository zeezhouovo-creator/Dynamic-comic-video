"""Regression checks for the canonical workflow/version documentation."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class DocumentationTests(unittest.TestCase):
    def test_current_contract_versions_are_consistent(self):
        skill = read("SKILL.md")
        contracts = read("references/contracts.md")
        comic = read("references/sequential-comic.md")
        limited = read("references/limited-animation.md")
        self.assertIn('motion_plan.version: "0.3"', skill)
        self.assertIn('motion_plan.json` 使用 `version: "0.3"', contracts)
        self.assertIn("motion_plan 使用版本0.3", comic)
        self.assertIn('motion_plan.version="0.3"', limited)
        self.assertIn("0.2` 是可读取的旧有限动画合同", limited)

    def test_legacy_entry_points_delegate_to_current_rules(self):
        intake = read("references/project-intake.md")
        director = read("references/storyboard-director.md")
        self.assertIn("动态漫画制作向导", intake)
        self.assertIn("总控复用边界", director)
        self.assertNotIn("基础 Motion Director/Parallax", intake)
        self.assertNotIn("用户确认角色身份 →", intake)

    def test_release_version_has_one_public_story(self):
        skill = read("SKILL.md")
        readme = read("README.md")
        closure = read("references/v04-production.md")
        self.assertIn("当前对外版本是 V1.0", skill)
        self.assertIn("## V1.0 workflow", readme)
        self.assertIn("不是当前对外版本", closure)
        self.assertNotIn("V1.0 candidate / V0.4 stable engine", readme)


if __name__ == "__main__":
    unittest.main()
