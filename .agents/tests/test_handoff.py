"""Acceptance tests for docs/43_MULTI_AGENT_MEMORY_AND_HANDOFF_PLAN.md.

Fast checks:  python -m unittest discover -s .agents/tests -v
Agent checks: set HANDOFF_E2E=1 first. They call claude, codex and agy
in a throwaway sandbox repo and spend real quota.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ".agents/templates/docs/HANDOFF.md"
SPEC = "docs/58_MULTI_AGENT_HANDOFF_SPEC.md"
STALE_SPEC_POINTERS = ["docs/43", "43_MULTI_AGENT"]
LIVE_POINTERS = ["AGENTS.md", "CLAUDE.md", ".gitignore", ".agents/rules/GEMINI.md", TEMPLATE]
MASTER_BUILD_STEP_1 = (
    "1. Deployed skeleton " + chr(0x2014) + " FastAPI on Render, green `/health/ready`, migrations run."
)
HEADER_FIELDS = ["**Status**", "**Updated**", "**Agent**", "**Branch**", "**Worktree**"]
SECTIONS = [
    "## 1. Objective",
    "## 2. Approved Scope",
    "## 3. Settled Decisions",
    "## 4. Done and Verified",
    "## 5. Working Tree Evidence",
    "## 6. The Baton",
    "## 7. Open Questions for Len",
]
SKILLS_THAT_RECORD_APPROVAL = [
    ".agents/skills/spec/SKILL.md",
    ".claude/skills/spec/SKILL.md",
    ".agents/skills/implementation-plan/SKILL.md",
]
BATON = "BATON-7F3A"
EM_DASH = chr(0x2014)
E2E = os.environ.get("HANDOFF_E2E") == "1"
AGENT_TIMEOUT = 600


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def markdown_section(text, heading):
    start = text.find(heading + "\n")
    if start == -1:
        return None
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def git_bash():
    override = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if override:
        return override
    if os.name != "nt":
        return shutil.which("bash")
    # On Windows, plain `bash` resolves to the WSL stub in System32, not the
    # Git Bash that Claude Code runs hooks with.
    git = shutil.which("git")
    if not git:
        return None
    for folder in Path(git).resolve().parents:
        candidate = folder / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    return None


def handoff_hook_commands():
    settings = json.loads(read(".claude/settings.json"))
    return [
        hook["command"]
        for group in settings.get("hooks", {}).get("SessionStart", [])
        for hook in group.get("hooks", [])
        if hook.get("type") == "command" and "HANDOFF.md" in hook.get("command", "")
    ]


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


class ConventionFiles(unittest.TestCase):
    def test_template_has_every_section_in_order(self):  # AC-1
        text = read(TEMPLATE)
        for field in HEADER_FIELDS:
            self.assertIn(field, text)
        positions = [text.find(s) for s in SECTIONS]
        self.assertNotIn(-1, positions, "template is missing a section")
        self.assertEqual(positions, sorted(positions), "template sections out of order")
        self.assertNotIn(EM_DASH, text)

    def test_root_handoff_is_ignored_but_template_is_not(self):  # AC-13
        self.assertEqual(git("check-ignore", "-q", "HANDOFF.md").returncode, 0)
        self.assertEqual(git("check-ignore", "-q", TEMPLATE).returncode, 1)

    def test_agents_md_has_one_handoff_section(self):  # AC-5, AC-14
        text = read("AGENTS.md")
        self.assertEqual(text.count("\n## Agent handoff\n"), 1)
        section = markdown_section(text, "## Agent handoff")
        for token in [
            "HANDOFF.md",
            TEMPLATE,
            "git status",
            "ACTIVE",
            "COMPLETED",
            "Updated",
            "Baton",
            "LOAM_KEY",
            SPEC,
        ]:
            self.assertTrue(token in section, f"Agent handoff section lacks {token!r}")
        self.assertNotIn(EM_DASH, section)

    def test_claude_md_points_to_handoff_section(self):  # AC-6
        text = read("CLAUDE.md")
        for token in ["Agent handoff", "AGENTS.md"]:
            self.assertTrue(token in text, f"CLAUDE.md lacks {token!r}")

    def test_gemini_entry_point_reads_agents_and_handoff(self):  # REQ-003
        text = read(".agents/rules/GEMINI.md")
        for token in ["AGENTS.md", "HANDOFF.md"]:
            self.assertTrue(token in text, f"GEMINI.md lacks {token!r}")

    def test_skills_record_approval_in_the_approved_doc(self):  # REQ-007
        for rel in SKILLS_THAT_RECORD_APPROVAL:
            with self.subTest(skill=rel):
                text = read(rel)
                self.assertTrue("in the approved doc" in text, f"{rel} not reworded")
                self.assertFalse("approved revisions in the current handoff." in text)


def table_row(text, first_cell):
    for line in text.splitlines():
        if line.startswith(f"| {first_cell} |"):
            return line
    return ""


class SpecDocument(unittest.TestCase):
    def test_spec_renumbered(self):  # AC-17
        self.assertTrue((ROOT / SPEC).exists(), f"{SPEC} missing")
        old = ROOT / "docs" / ("43_" + "MULTI_AGENT_MEMORY_AND_HANDOFF_PLAN.md")
        self.assertFalse(old.exists(), "old doc 43 path still exists")

    def test_no_live_pointer_to_old_spec(self):  # AC-18
        texts = {rel: read(rel) for rel in LIVE_POINTERS}
        if (ROOT / "HANDOFF.md").exists():
            texts["HANDOFF.md"] = read("HANDOFF.md")
        texts["test_handoff.py docstring"] = __doc__
        for name, text in texts.items():
            for stale in STALE_SPEC_POINTERS:
                with self.subTest(file=name, stale=stale):
                    self.assertFalse(stale in text, f"{name} still points at {stale}")

    def test_spec_is_indexed(self):  # AC-29
        self.assertTrue(Path(SPEC).name in read("docs/SPEC_INDEX.md"),
                        "docs/SPEC_INDEX.md does not link the handoff spec")

    def test_spec_has_required_header(self):  # AC-19
        self.assertTrue((ROOT / SPEC).exists(), f"{SPEC} missing")
        head = "\n".join(read(SPEC).splitlines()[:12])
        for field in ["**Status:**", "**Owner:**", "**Created:**", "**Updated:**",
                      "**Related:**", "**Execution mode:**"]:
            self.assertTrue(field in head, f"spec header lacks {field}")


class EntryFileFacts(unittest.TestCase):
    def test_entry_files_say_render_not_railway(self):  # AC-20, AC-21
        self.assertTrue(MASTER_BUILD_STEP_1 in read("AGENTS.md"),
                        "AGENTS.md build step 1 differs from master")
        self.assertTrue("FastAPI on Render" in read("CLAUDE.md"))
        for rel in ["AGENTS.md", "CLAUDE.md"]:
            with self.subTest(file=rel):
                self.assertFalse("railway" in read(rel).lower(), f"{rel} mentions Railway")

    def test_ownership_matches_len(self):  # AC-22
        for rel in ["AGENTS.md", "CLAUDE.md"]:
            text = read(rel)
            with self.subTest(file=rel):
                self.assertTrue("Flutter" in table_row(text, "Jade"), f"{rel}: Jade row")
                self.assertTrue("dashboard" in table_row(text, "Arnold").lower(),
                                f"{rel}: Arnold row")

    def test_public_api_consumer_is_arnold(self):  # AC-23
        for rel in ["AGENTS.md", "CLAUDE.md"]:
            with self.subTest(file=rel):
                row = table_row(read(rel), "Public REST + SSE")
                self.assertTrue("dashboard (Arnold)" in row, f"{rel}: {row!r}")


@unittest.skipUnless(git_bash(), "Git Bash not found")
class SessionStartHook(unittest.TestCase):
    def run_hook(self, project_dir):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
        commands = handoff_hook_commands()
        self.assertEqual(len(commands), 1, "need exactly one SessionStart hook for HANDOFF.md")
        return subprocess.run(
            [git_bash(), "-c", commands[0]],
            env=env, capture_output=True, text=True, timeout=30, check=False,
        )

    def test_settings_keep_existing_keys(self):
        settings = json.loads(read(".claude/settings.json"))
        self.assertIn("skillOverrides", settings)

    def test_exactly_one_handoff_hook(self):  # REQ-005
        self.assertEqual(len(handoff_hook_commands()), 1)

    def test_prints_handoff_when_present(self):  # AC-10, AC-12
        with tempfile.TemporaryDirectory(prefix="handoff hook ") as tmp:
            Path(tmp, "HANDOFF.md").write_text(f"> {BATON}\n", encoding="utf-8")
            result = self.run_hook(tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(BATON, result.stdout)

    def test_silent_when_absent(self):  # AC-11
        with tempfile.TemporaryDirectory(prefix="handoff hook ") as tmp:
            result = self.run_hook(tmp)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


FIXTURE = """# Agent Handoff

- **Status**: {status}
- **Updated**: 2026-09-23T09:00:00+08:00
- **Agent**: Claude Code (test fixture)
- **Branch**: `master`
- **Worktree**: `{worktree}`

## 1. Objective

Add a greeting file for the handoff test.

## 2. Approved Scope

- none - test fixture

## 3. Settled Decisions

- none

## 4. Done and Verified

- none yet

## 5. Working Tree Evidence

As of **Updated** above.
Any file changed after that time is unrecorded work.

- **Modified**: none
- **Untracked**: none
- **Last check**: none

## 6. The Baton

> Create `greeting.txt` containing {baton}.

## 7. Open Questions for Len

- none
"""

SANDBOX_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    ".claude/settings.json",
    ".agents/rules/GEMINI.md",
    TEMPLATE,
]

# Prompts avoid quotes and cmd.exe metacharacters because claude is a .CMD shim on Windows.
ARRIVAL_PROMPT = (
    "Follow this repository arrival rules. Do not edit any files. "
    "Reply with one line: the exact next action you should take."
)
COMPLETED_PROMPT = (
    "Follow this repository arrival rules. Do not edit any files. "
    "Is there active work to resume? Reply with one line: RESUME followed by the action, or NONE."
)
MISMATCH_PROMPT = (
    "Follow this repository arrival rules. Do not edit any files. "
    "Reply with one line: MATCH if the working tree matches the handoff evidence, "
    "otherwise MISMATCH followed by the files that differ."
)


@unittest.skipUnless(E2E, "set HANDOFF_E2E=1 to run agent scenarios")
class AgentScenarios(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="handoff-e2e-")
        self.sandbox = Path(self._tmp.name)
        for rel in SANDBOX_FILES:
            target = self.sandbox / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        git("init", "-q", "-b", "master", cwd=self.sandbox)
        git("add", "-A", cwd=self.sandbox)
        git("-c", "user.name=test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "fixture", cwd=self.sandbox)

    def tearDown(self):
        self._tmp.cleanup()

    def write_handoff(self, status="ACTIVE"):
        text = FIXTURE.format(status=status, worktree=self.sandbox, baton=BATON)
        (self.sandbox / "HANDOFF.md").write_text(text, encoding="utf-8")

    def ask(self, argv):
        exe = shutil.which(argv[0])
        if not exe:
            self.skipTest(f"{argv[0]} not installed")
        result = subprocess.run(
            [exe, *argv[1:]], cwd=self.sandbox, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=AGENT_TIMEOUT, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def claude(self, prompt):
        no_tools = ["Bash", "PowerShell", "Read", "Glob", "Grep", "Edit", "Write", "Agent"]
        return self.ask(["claude", "-p", prompt, "--disallowedTools", *no_tools])

    def test_t1_claude_gets_handoff_injected(self):  # AC-10
        self.write_handoff()
        self.assertIn(BATON, self.claude(ARRIVAL_PROMPT).upper())

    def test_t2_claude_starts_cleanly_without_handoff(self):  # AC-11
        self.assertNotIn(BATON, self.claude(ARRIVAL_PROMPT).upper())

    def test_t4_codex_follows_arrival_rule(self):  # AC-7
        self.write_handoff()
        out = self.ask(["codex", "exec", "-s", "read-only", ARRIVAL_PROMPT])
        self.assertIn(BATON, out.upper())

    def test_t5_antigravity_follows_arrival_rule(self):  # AC-7
        if os.environ.get("ANTIGRAVITY_AGENT"):
            self.skipTest("nested agy execution inside Antigravity agent not supported")
        self.write_handoff()
        self.assertIn(BATON, self.ask(["agy", "-p", ARRIVAL_PROMPT]).upper())

    def test_t6_codex_reports_unrecorded_file(self):  # AC-8, AC-9
        self.write_handoff()
        (self.sandbox / "extra.txt").write_text("not in the handoff\n", encoding="utf-8")
        out = self.ask(["codex", "exec", "-s", "read-only", MISMATCH_PROMPT])
        self.assertIn("MISMATCH", out.upper())
        self.assertIn("extra.txt", out)

    def test_t8_completed_handoff_is_not_resumed(self):  # Flow 3.4
        self.write_handoff(status="COMPLETED")
        out = self.claude(COMPLETED_PROMPT).upper()
        self.assertIn("NONE", out)
        self.assertNotIn("RESUME", out)


if __name__ == "__main__":
    unittest.main()
