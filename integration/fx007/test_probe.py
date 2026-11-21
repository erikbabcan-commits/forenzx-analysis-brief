"""Regression checks for the concrete interrupted-child cleanup risk.

The fixture CLI only sleeps. These checks never run Codex, access credentials,
contact an LLM, or require the upstream server/dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == "posix", "Process-group signal checks require POSIX")
class InterruptedClientCleanupTests(unittest.TestCase):
    def assert_interrupt_cleans_child(self, interrupted_by: int, expected_code: int) -> None:
        with tempfile.TemporaryDirectory(prefix="fx007-cleanup-test-") as name:
            temporary = Path(name)
            pid_file = temporary / "client.pid"
            fake = temporary / "codex-fixture"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import os, sys, time\nfrom pathlib import Path\n"
                "if '--version' in sys.argv:\n    print('codex-cleanup-fixture')\n    sys.exit(0)\n"
                "Path(os.environ['FX007_TEST_PID_FILE']).write_text(str(os.getpid()))\n"
                "while True:\n    time.sleep(1)\n", encoding="utf-8")
            fake.chmod(0o700)
            helper = temporary / "helper.py"
            helper.write_text(
                "import sys\nfrom pathlib import Path\n"
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\n"
                "import run_probe\n"
                f"run_probe.shutil.which = lambda _: {str(fake)!r}\n"
                "run_probe.install_signal_handlers()\n"
                f"temporary = Path({str(temporary)!r})\n"
                "output = temporary / 'output'\noutput.mkdir()\n"
                "try:\n"
                "    run_probe.run_codex(1, 'synthetic-test-token', 'synthetic-job', temporary, output, [], 120)\n"
                "except KeyboardInterrupt:\n    raise SystemExit(130)\n"
                "except run_probe.ProbeTerminated as error:\n    raise SystemExit(error.exit_code)\n",
                encoding="utf-8")
            process = subprocess.Popen([sys.executable, str(helper)],
                                       env=dict(os.environ, FX007_TEST_PID_FILE=str(pid_file)),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            child_pid = None
            try:
                deadline = time.monotonic() + 8
                while not pid_file.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail(f"Fixture did not start: {process.communicate(timeout=2)}")
                    time.sleep(0.02)
                child_pid = int(pid_file.read_text())
                process.send_signal(interrupted_by)
                stdout, stderr = process.communicate(timeout=12)
                self.assertEqual(process.returncode, expected_code, stdout + stderr)
                with self.assertRaises(ProcessLookupError, msg="Interrupted probe left its client alive"):
                    os.kill(child_pid, 0)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
                if child_pid is not None:
                    try:
                        os.killpg(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_sigint_stops_owned_client(self):
        self.assert_interrupt_cleans_child(signal.SIGINT, 130)

    def test_sigterm_stops_owned_client(self):
        self.assert_interrupt_cleans_child(signal.SIGTERM, 143)


if __name__ == "__main__":
    unittest.main()
