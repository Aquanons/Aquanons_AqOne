"""Acceptance tests for REQ-010 (plan execution modes) in docs/58_MULTI_AGENT_HANDOFF_SPEC.md.

Fast checks:  python -m unittest discover -s .agents/tests -v
Agent check:  set HANDOFF_E2E=1 first. It calls claude in a throwaway
sandbox repo and spends real quota.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_handoff import AGENT_TIMEOUT, E2E, EM_DASH, ROOT, SPEC, git, read

SKILL_COPIES = [
    ".agents/skills/implementation-plan/SKILL.md",
    ".claude/skills/implementation-plan/SKILL.md",
]
SKILL = SKILL_COPIES[1]
MODE_FIELD = re.compile(r"^\*\*Execution mode:\*\* (auto|hard-stop)\s*$", re.MULTILINE)


class PlanModeSkill(unittest.TestCase):
    def setUp(self):
        for rel in SKILL_COPIES:
            self.assertTrue((ROOT / rel).exists(), f"{rel} missing")

    def test_copies_are_byte_identical(self):  # AC-24
        first, second = ((ROOT / rel).read_bytes() for rel in SKILL_COPIES)
        self.assertTrue(first == second, "implementation-plan skill copies differ")

    def test_declares_modes_header_and_toggle(self):  # AC-25
        text = read(SKILL)
        for token in ["**Execution mode:**", "`auto`", "`hard-stop`", "mode auto", "mode hard-stop"]:
            self.assertTrue(token in text, f"skill lacks {token!r}")
        self.assertTrue("next phase boundary" in text.lower(), "skill lacks the boundary rule")

    def test_frontmatter_argument_hint_mentions_mode(self):  # AC-26
        text = read(SKILL)
        self.assertTrue(text.startswith("---\n"), "skill has no frontmatter")
        frontmatter = text.split("---\n")[1]
        hints = [line for line in frontmatter.splitlines() if line.startswith("argument-hint:")]
        self.assertEqual(len(hints), 1, "need exactly one argument-hint")
        self.assertTrue("mode" in hints[0])

    def test_keeps_handoff_wording(self):  # AC-27
        self.assertTrue("in the approved doc, linked from the current handoff" in read(SKILL))

    def test_no_em_dash(self):
        self.assertNotIn(EM_DASH, read(SKILL))

    def test_spec_declares_its_own_mode(self):  # REQ-010 dogfood
        self.assertTrue((ROOT / SPEC).exists(), f"{SPEC} missing")
        self.assertIsNotNone(MODE_FIELD.search(read(SPEC)), "spec header lacks an execution mode")


FIXTURE_PLAN = """# Fixture - Implementation Plan

**Status:** ACTIVE
**Owner:** Test
**Created:** 2026-09-23
**Updated:** 2026-09-23
**Related:** none
**Execution mode:** auto

## Phase 1: Say hello

- [ ] 1.1 Create `hello.txt` containing FIXTURE-PHASE-ONE.
"""
FIXTURE_PLAN_PATH = "docs/90_FIXTURE_IMPLEMENTATION_PLAN.md"


@unittest.skipUnless(E2E, "set HANDOFF_E2E=1 to run agent scenarios")
class PlanModeToggle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-mode-e2e-")
        self.sandbox = Path(self._tmp.name)
        for rel in ["AGENTS.md", "CLAUDE.md", SKILL]:
            target = self.sandbox / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        plan = self.sandbox / FIXTURE_PLAN_PATH
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text(FIXTURE_PLAN, encoding="utf-8")
        git("init", "-q", "-b", "master", cwd=self.sandbox)
        git("add", "-A", cwd=self.sandbox)
        git("-c", "user.name=test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "fixture", cwd=self.sandbox)

    def tearDown(self):
        self._tmp.cleanup()

    def test_claude_toggles_plan_mode(self):  # AC-28
        exe = shutil.which("claude")
        if not exe:
            self.skipTest("claude not installed")
        result = subprocess.run(
            [exe, "-p", "/implementation-plan mode hard-stop", "--permission-mode", "acceptEdits"],
            cwd=self.sandbox, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=AGENT_TIMEOUT, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = (self.sandbox / FIXTURE_PLAN_PATH).read_text(encoding="utf-8")
        self.assertEqual(MODE_FIELD.findall(plan), ["hard-stop"], plan)
        self.assertIn("- [ ] 1.1 Create `hello.txt` containing FIXTURE-PHASE-ONE.", plan)
        self.assertFalse((self.sandbox / "hello.txt").exists(), "toggle ran the phase")


if __name__ == "__main__":
    unittest.main()
