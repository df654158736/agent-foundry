"""Release and project initialization must carry the developer methods and reviewers."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest
from zipfile import ZipFile

from foundry.project import ROOT, initialize, upgrade
from scripts.package_release import build


class DeveloperAssetTests(unittest.TestCase):
    def test_portable_assets_reach_zip_and_new_project(self):
        names = {
            "goal-aligned-design", "codebase-design", "debug-agent-reallink",
            "agent-evaluation-scoring", "session-handoff",
            "foundry-build", "foundry-gold", "foundry-iterate", "improve-codebase-architecture",
        }
        skills = ROOT / ".agents/skills"
        self.assertEqual(names, {p.parent.name for p in skills.glob("*/SKILL.md")})
        references = skills / "debug-agent-reallink/references"
        for reference in ("agent-type-checklist", "evidence-ledger", "full-suite-reallink",
                          "harness-repair-generalization"):
            self.assertTrue((references / (reference + ".md")).is_file())
        for role in ("reviewer", "spec-delivery-reviewer"):
            config = tomllib.loads((ROOT / ".codex/agents" / (role + ".toml")).read_text())
            self.assertEqual(config["name"], role.replace("-", "_"))
            self.assertEqual(config["sandbox_mode"], "read-only")
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            project = initialize(temp / "project")
            archive = build(temp / "release")
            with ZipFile(archive) as zipped:
                for base in (skills, ROOT / ".codex/agents"):
                    for path in base.rglob("*"):
                        if not path.is_file() or "__pycache__" in path.parts:
                            continue
                        relative = path.relative_to(ROOT)
                        self.assertEqual(path.read_bytes(), (project / relative).read_bytes())
                        self.assertEqual(path.read_bytes(), zipped.read(f"{archive.stem}/{relative.as_posix()}"))

    def test_frontend_opt_in_survives_packaging_and_upgrade(self):
        from hashlib import sha256

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            plain = initialize(temp / "plain")
            installed = Path(".agents/skills/web-design-guidelines")
            self.assertFalse((plain / installed).exists())
            self.assertFalse((upgrade(plain, temp / "next") / installed).exists())
            ui = initialize(temp / "ui", frontend=True)
            files = ("SKILL.md", "LICENSE", "references/command.md")
            self.assertEqual(sha256((ui / installed / files[-1]).read_bytes()).hexdigest(),
                             "d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234")
            upgraded = upgrade(ui, temp / "ui-next")
            enabled = upgrade(plain, temp / "enabled", frontend=True)
            archive = build(temp / "release")
            with ZipFile(archive) as zipped:
                for name in files:
                    data = (ui / installed / name).read_bytes()
                    self.assertEqual(data, (upgraded / installed / name).read_bytes())
                    self.assertEqual(data, (enabled / installed / name).read_bytes())
                    self.assertEqual(data, zipped.read(f"{archive.stem}/extensions/web-design-guidelines/{name}"))
