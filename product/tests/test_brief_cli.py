import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from product import brief_cli

PRODUCT = Path(__file__).resolve().parents[1]


class DemoCLITests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.cli = PRODUCT / "brief_cli.py"

    def run_cli(self, *args, data=b"", timezone="UTC"):
        return subprocess.run(
            [sys.executable, str(self.cli), *args], cwd=self.work, input=data, capture_output=True,
            timeout=10, env=dict(os.environ, TZ=timezone, PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1"))

    def copy_demo(self):
        root = self.work / "package"
        root.mkdir()
        for name in ("brief_cli.py", "render_brief.py", "validate_input.py"):
            shutil.copy(PRODUCT / name, root / name)
        shutil.copytree(PRODUCT / "fixtures", root / "fixtures")
        shutil.copytree(PRODUCT / "brief_reference", root / "brief_reference")
        self.cli = root / "brief_cli.py"
        return root

    def test_foreign_cwd_separate_processes_and_timezone(self):
        root = self.copy_demo()
        for name in ("completed-hit", "completed-no-ioc"):
            raw = (root / "fixtures" / (name + ".json")).read_bytes()
            frozen = (PRODUCT / "brief_reference" / (name + ".md")).read_bytes()
            for tz in ("UTC", "Pacific/Honolulu"):
                result = self.run_cli(name, timezone=tz)
                self.assertEqual((result.returncode, result.stderr, result.stdout), (0, b"", frozen))
            self.assertEqual((root / "fixtures" / (name + ".json")).read_bytes(), raw)

    def test_both_demos_with_network_and_child_processes_denied(self):
        root = self.copy_demo()
        guard = self.work / "offline.py"
        guard.write_text(
            "import runpy, sys\n"
            "def deny(event, args):\n"
            "    if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn', 'os.system')):\n"
            "        raise RuntimeError(event)\n"
            "sys.addaudithook(deny)\n"
            "sys.path.insert(0, sys.argv.pop(1))\n"
            "runpy.run_module('brief_cli', run_name='__main__')\n",
            encoding="utf-8",
        )
        for name in ("completed-hit", "completed-no-ioc"):
            result = subprocess.run([sys.executable, "-I", "-B", str(guard), str(root), name],
                                    cwd=self.work, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, (PRODUCT / "brief_reference" / (name + ".md")).read_bytes())

    def test_rejects_external_inputs_and_stdin(self):
        for args in [[], ["-"], ["https://private.invalid/case"], ["../private.json"], ["--input", "private.json"]]:
            result = self.run_cli(*args, data=b"private-sentinel")
            self.assertEqual((result.returncode, result.stdout), (2, b""))
            self.assertNotIn(b"private", result.stderr)

    def test_failure_creates_no_output(self):
        root = self.copy_demo()
        path = root / "fixtures/completed-hit.json"
        target = self.work / "result.md"
        for data in (path.read_bytes() + b" ", b"{", b" " * 262145):
            path.write_bytes(data)
            result = self.run_cli("completed-hit", "--output", target)
            self.assertEqual((result.returncode, result.stdout), (2, b""))
            self.assertFalse(target.exists())

    def test_output_publication_and_collision(self):
        path = self.work / "demo.md"
        self.assertEqual(self.run_cli("completed-hit", "--output", path).returncode, 0)
        original = path.read_bytes()
        self.assertEqual(original, (PRODUCT / "brief_reference/completed-hit.md").read_bytes())
        self.assertEqual(self.run_cli("completed-no-ioc", "--output", path).returncode, 2)
        self.assertEqual(path.read_bytes(), original)
        link = self.work / "dangling"
        link.symlink_to(self.work / "absent")
        self.assertEqual(self.run_cli("completed-hit", "--output", link).returncode, 2)
        self.assertEqual(set(self.work.iterdir()), {path, link})

    def test_symlink_and_nonregular_fixture_refused(self):
        root = self.copy_demo()
        path = root / "fixtures/completed-hit.json"
        path.unlink()
        path.symlink_to(PRODUCT / "fixtures/completed-hit.json")
        self.assertEqual(self.run_cli("completed-hit").returncode, 2)
        path.unlink()
        os.mkfifo(path)
        self.assertEqual(self.run_cli("completed-hit").returncode, 2)

    def test_snapshot_survives_fixture_replacement_after_validation(self):
        root = self.copy_demo()
        path = root / "fixtures/completed-hit.json"
        validate = brief_cli.brief.validator.validate_bytes
        def replace(*args, **kwargs):
            verdict = validate(*args, **kwargs)
            path.write_bytes(b"changed after validation")
            return verdict
        with patch.object(brief_cli.brief, "PRODUCT", root), patch.object(
                brief_cli.brief.validator, "validate_bytes", replace):
            output = self.work / "brief.md"
            self.assertEqual(brief_cli.main(["completed-hit", "--output", str(output)]), 0)
        self.assertEqual(output.read_bytes(), (PRODUCT / "brief_reference/completed-hit.md").read_bytes())
        self.assertEqual(path.read_bytes(), b"changed after validation")
