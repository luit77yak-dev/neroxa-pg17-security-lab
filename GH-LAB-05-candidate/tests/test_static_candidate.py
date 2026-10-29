import ast
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflow.preflight.candidate.yml"
README = ROOT / "README.md"
LOCK = ROOT / "postgresql17-source-lock.json"


def run_block(text, step_name):
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[run + 1:]:
        if line and not line.startswith("          "):
            break
        body.append(line[10:] if line.startswith("          ") else "")
    return "\n".join(body).rstrip() + "\n"


class CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_text = WORKFLOW.read_text()
        cls.probe = run_block(cls.workflow_text, "Probe runner only; no PostgreSQL, Docker, SQL, or external actions")
        cls.cleanup = run_block(cls.workflow_text, "Cleanup and residue audit")

    def test_manual_only_single_main_job_and_permissions(self):
        self.assertRegex(self.workflow_text, r"(?m)^\s+workflow_dispatch:\s*$")
        self.assertRegex(self.workflow_text, r"(?m)^jobs:\s*\n  runner-preflight:")
        self.assertEqual(self.workflow_text.count("runs-on: ubuntu-24.04"), 1)
        self.assertEqual(self.workflow_text.count("contents: none"), 2)
        self.assertNotRegex(self.workflow_text, r"(?m)^\s+(push|pull_request|schedule|create|release):")
        self.assertIn("permissions:\n  contents: none", self.workflow_text)
        self.assertIn("runs-on: ubuntu-24.04", self.workflow_text)
        self.assertIn("timeout-minutes: 10", self.workflow_text)
        self.assertIn("cancel-in-progress: false", self.workflow_text)
        self.assertNotIn("uses:", self.workflow_text)
        self.assertNotIn("secrets.", self.workflow_text)
        self.assertNotIn("${{ runner.temp }}", self.workflow_text)

    def test_no_service_or_sql_execution(self):
        for forbidden in ("docker ", "psql ", "initdb ", "postgres -D", "CREATE ROLE", "REVOKE "):
            self.assertNotIn(forbidden, self.workflow_text)
        self.assertIn("SQL_TESTS=NOT_RUN", self.probe)
        self.assertIn("POSTGRESQL_INITIALIZATION_DISK=NOT_TESTED", self.probe)

    def test_embedded_python_parses_and_has_resource_floors(self):
        match = re.search(r"/usr/bin/python3 - <<'PY'\n(.*?)\n\s*PY$", self.probe, re.S | re.M)
        self.assertIsNotNone(match)
        source = match.group(1)
        ast.parse(source)
        self.assertIn("MIN_CPUS = 2", source)
        self.assertIn("MIN_MEMORY = 1 * GIB", source)
        self.assertIn("MIN_DISK_BEFORE = 4 * GIB", source)
        self.assertIn("MIN_DISK_AFTER_PROBE = 3 * GIB", source)
        self.assertIn('"credential_like_environment_names_absent"', source)

        tree = ast.parse(source)
        allowlist = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "allowlisted_environment")
        namespace = {}
        exec(compile(ast.Module(body=[allowlist], type_ignores=[]), "embedded-preflight", "exec"), namespace)
        sentinel = "SYNTHETIC_NEVER_LOG_OR_FORWARD"
        clean = namespace["allowlisted_environment"]({"PATH": "/usr/bin", "GITHUB_TOKEN": sentinel, "FAKE_PASSWORD": sentinel})
        self.assertEqual(clean, {"PATH": "/usr/bin"})
        self.assertNotIn(sentinel, repr(clean))

    def test_resource_gate_precedes_temporary_directory_creation(self):
        match = re.search(r"/usr/bin/python3 - <<'PY'\n(.*?)\n\s*PY$", self.probe, re.S | re.M)
        self.assertIsNotNone(match)
        source = match.group(1)
        gate = source.index('if not all(results[name] for name in ("cpu_floor", "memory_floor", "disk_floor_before", "temporary_path_scope"))')
        create_dir = source.index('preflight_dir.mkdir(mode=0o700')
        privileged_probe = source.index('subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/install"')
        self.assertLess(gate, create_dir)
        self.assertLess(create_dir, privileged_probe)
        self.assertIn("no directory or privileged probe created", source[gate:create_dir])

        readme = README.read_text()
        self.assertIn("sudo`/`unshare` intentionally uses elevated runner privileges", readme)
        self.assertIn("drops the **test process**", readme)

    def test_source_lock_is_official_and_pinned(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock["major"], 17)
        self.assertEqual(lock["minor"], "17.11")
        self.assertTrue(lock["url"].startswith("https://ftp.postgresql.org/pub/source/v17.11/"))
        self.assertRegex(lock["sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(lock["execution_in_this_mission"])

    def test_cleanup_is_always_and_path_scoped(self):
        self.assertRegex(self.workflow_text, r"(?m)^\s+if: \$\{\{ always\(\) \}\}$")
        self.assertIn("target.parent != temp", self.cleanup)
        self.assertIn("CLEANUP=PASS", self.cleanup)
        self.assertIn("VM_TEARDOWN_CLEANUP=PLATFORM_DEPENDENT", self.cleanup)

    def test_static_boundaries_documented(self):
        readme = README.read_text()
        self.assertIn("Lab readiness remains BLOCKED", readme)
        self.assertIn("post-initialization", readme)
        self.assertIn("one-time-use guarantee", readme)
        self.assertIn("platform cancellation", readme)


if __name__ == "__main__":
    unittest.main()
