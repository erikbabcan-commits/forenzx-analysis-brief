"""Regression checks for the concrete interrupted-child cleanup risk.

The fixture CLI only sleeps. These checks never run Codex, access credentials,
contact an LLM, or require the upstream server/dependencies.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


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


class RoleConfigurationTests(unittest.TestCase):
    def test_cli_dispatches_the_selected_role(self):
        import run_probe

        for flags, role in [([], "analyst"), (["--codex-role", "analyst"], "analyst"),
                            (["--codex-role", "reporter"], "reporter")]:
            argv = ["run_probe.py", "--upstream", ".", "--output", "unused", "--with-codex", *flags]
            with self.subTest(flags=flags), patch.object(sys, "argv", argv), \
                    patch.object(run_probe, "install_signal_handlers"), \
                    patch.object(run_probe, "run", return_value=0) as run:
                self.assertEqual(run_probe.main(), 0)
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0].codex_role, role)

    def test_cli_rejects_unknown_role_before_dispatch(self):
        import run_probe

        argv = ["run_probe.py", "--upstream", ".", "--output", "unused", "--codex-role", "unknown"]
        with patch.object(sys, "argv", argv), patch.object(run_probe, "run") as run, \
                redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
            run_probe.main()
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()

    def test_main_cli_validation(self):
        import run_probe

        for argv, expected_code in [
            (["run_probe.py", "--upstream", "/dummy"], 2),
            (["run_probe.py", "--upstream", "/dummy", "--output", "/dummy", "--codex-timeout", "10"], 2),
            (["run_probe.py", "--upstream", "/dummy", "--output", "/dummy", "--codex-timeout", "301"], 2),
        ]:
            with self.subTest(argv=argv), patch.object(sys, "argv", argv), \
                    patch.object(run_probe, "install_signal_handlers"), \
                    patch.object(run_probe, "run") as run, \
                    redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                run_probe.main()
            self.assertEqual(error.exception.code, expected_code)
            run.assert_not_called()

    def test_reporter_claims_structure(self):
        import run_probe

        claims = run_probe.synthetic_reporter_claims("CASE-001", "JOB-001", 123456)
        self.assertEqual(claims, {
            "sub": "synthetic-reporter",
            "roles": ["reporter"],
            "organization": run_probe.ORGANIZATION,
            "report_case_ids": ["CASE-001"],
            "report_job_ids": ["JOB-001"],
            "exp": 123456,
        })


class CodexEvaluationLogicTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import run_probe
        self.run_probe = run_probe
        self.job_id = "test-job-uuid-1234"
        self.expected_hashes = {
            "forenzx_analysis_status": "sha256-status-hash-abc",
            "forenzx_analysis_results": "sha256-results-hash-xyz",
        }
        self.expected_final = {
            "job_id": self.job_id,
            "state": "COMPLETED",
            "classification": "HIT",
            "finding_count": 1,
            "warnings": ["warning 1"],
            "limitations": ["limitation 1"],
        }
        self.codex_meta_ok = {"exit_code": 0, "timed_out": False, "client": "codex-test"}

    def _event(self, tool_name: str, *, status: int = 200, rpc_code: int | None = None,
               has_result: bool = True, tool_is_error: bool = False,
               requested_job: str | None = None, returned_job: str | None = None,
               result_hash: str | None = None, bound: bool = True,
               role: str | None = "reporter") -> dict:
        return {
            "phase": "codex",
            "http_method": "POST",
            "path": "/mcp",
            "rpc_method": "tools/call",
            "tool_name": tool_name,
            "auth_role": role,
            "caller_credential_matched": bound,
            "http_status": status,
            "rpc_error_code": rpc_code,
            "has_result": has_result,
            "tool_is_error": tool_is_error,
            "requested_job_id": requested_job or self.job_id,
            "returned_job_id": returned_job or self.job_id,
            "tool_result_sha256": result_hash or self.expected_hashes.get(tool_name),
        }

    def test_both_reads_succeed_with_bound_reporter_credential(self):
        calls = [
            self._event("forenzx_analysis_status"),
            self._event("forenzx_analysis_results"),
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="reporter"
        )
        self.assertTrue(res["accepted"])
        self.assertTrue(res["server_accepted_reporter"])
        self.assertTrue(res["final_exact_match"])
        self.assertEqual(res["tool_verifications"]["forenzx_analysis_status"]["verified_event_present"], True)
        self.assertEqual(res["tool_verifications"]["forenzx_analysis_results"]["verified_event_present"], True)
        self.assertEqual(res["server_observed_successful_tools"], ["forenzx_analysis_status", "forenzx_analysis_results"])

    def test_missing_credential_binding_on_one_read_rejects(self):
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="reporter"),
            self._event("forenzx_analysis_results", bound=False, role="reporter"),  # Missing binding on results!
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="reporter"
        )
        self.assertFalse(res["accepted"])
        self.assertFalse(res["server_accepted_reporter"])
        self.assertTrue(res["tool_verifications"]["forenzx_analysis_status"]["verified_event_present"])
        self.assertFalse(res["tool_verifications"]["forenzx_analysis_results"]["verified_event_present"])
        self.assertEqual(res["server_observed_successful_tools"], ["forenzx_analysis_status"])

    def test_reporter_only_on_unsuccessful_event_rejects(self):
        # results read: an unauthorized success event (wrong token/unbound) + an error event where reporter token was used
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="reporter"),
            self._event("forenzx_analysis_results", bound=False, role=None),  # successful call but unbound
            self._event("forenzx_analysis_results", status=403, rpc_code=-32603, has_result=False,
                        tool_is_error=None, bound=True, role="reporter"),  # reporter on error event!
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="reporter"
        )
        self.assertFalse(res["accepted"])
        self.assertFalse(res["server_accepted_reporter"])
        self.assertFalse(res["tool_verifications"]["forenzx_analysis_results"]["verified_event_present"])

    def test_analyst_role_default_behavior_preserved(self):
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="analyst"),
            self._event("forenzx_analysis_results", bound=True, role="analyst"),
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="analyst"
        )
        self.assertTrue(res["accepted"])
        self.assertIsNone(res["server_accepted_reporter"])
        self.assertTrue(res["tool_verifications"]["forenzx_analysis_status"]["verified_event_present"])
        self.assertTrue(res["tool_verifications"]["forenzx_analysis_results"]["verified_event_present"])

    def test_analyst_expected_with_bound_reporter_tokens_rejects(self):
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="reporter"),
            self._event("forenzx_analysis_results", bound=True, role="reporter"),
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="analyst"
        )
        self.assertFalse(res["accepted"])
        self.assertFalse(res["tool_verifications"]["forenzx_analysis_status"]["verified_event_present"])
        self.assertFalse(res["tool_verifications"]["forenzx_analysis_results"]["verified_event_present"])
        self.assertEqual(res["server_observed_successful_tools"], [])

    def test_unexpected_tool_call_rejects(self):
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="reporter"),
            self._event("forenzx_analysis_results", bound=True, role="reporter"),
            self._event("forenzx_analysis_start", bound=True, role="reporter"),
        ]
        res = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, self.codex_meta_ok, expected_role="reporter"
        )
        self.assertFalse(res["accepted"])
        self.assertEqual(res["unexpected_tool_calls"], ["forenzx_analysis_start"])

    def test_in_memory_recorder_credential_binding(self):
        import asyncio
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            (temp / "phase.txt").write_text("codex", encoding="utf-8")
            async def dummy_app(scope, receive, send):
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b'{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{}"}],"isError":false}}'})

            issued = {"synthetic-token-abc": "reporter"}
            recorder = self.run_probe.Recorder(dummy_app, temp, issued_tokens=issued)

            # Request 1: with issued token
            scope_valid = {
                "type": "http", "method": "POST", "path": "/mcp",
                "headers": [(b"authorization", b"Bearer synthetic-token-abc")],
            }
            async def dummy_receive():
                return {"type": "http.request", "body": b'{"method":"tools/call","params":{"name":"forenzx_analysis_status","arguments":{"job_id":"j1"}}}'}
            async def dummy_send(m):
                pass

            asyncio.run(recorder(scope_valid, dummy_receive, dummy_send))

            # Request 2: with non-issued token
            scope_invalid = {
                "type": "http", "method": "POST", "path": "/mcp",
                "headers": [(b"authorization", b"Bearer forged-token-xyz")],
            }
            asyncio.run(recorder(scope_invalid, dummy_receive, dummy_send))

            traffic_lines = [json.loads(l) for l in (temp / "traffic.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(traffic_lines), 2)
            self.assertTrue(traffic_lines[0]["caller_credential_matched"])
            self.assertEqual(traffic_lines[0]["auth_role"], "reporter")
            self.assertFalse(traffic_lines[1]["caller_credential_matched"])

            # Verify no secret leaked into traffic.jsonl
            content = (temp / "traffic.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("synthetic-token-abc", content)
            self.assertNotIn("forged-token-xyz", content)

    def test_codex_non_zero_exit_or_timeout_rejects(self):
        calls = [
            self._event("forenzx_analysis_status", bound=True, role="reporter"),
            self._event("forenzx_analysis_results", bound=True, role="reporter"),
        ]
        res_exit_err = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, {"exit_code": 1, "timed_out": False}, expected_role="reporter"
        )
        self.assertFalse(res_exit_err["accepted"])

        res_timeout = self.run_probe.evaluate_codex_events(
            calls, self.job_id, self.expected_hashes, self.expected_final,
            self.expected_final, {"exit_code": 0, "timed_out": True}, expected_role="reporter"
        )
        self.assertFalse(res_timeout["accepted"])


class UtilityFunctionsTests(unittest.TestCase):
    def setUp(self):
        import run_probe
        self.run_probe = run_probe

    def test_digest_and_canonical(self):
        d = self.run_probe.digest(b"test-bytes")
        self.assertEqual(d, "837fa4675d0ea98b79c41533ed9f35feefd73b7b88ca9134fd8a750cb7863ffc")
        c = self.run_probe.canonical({"z": 1, "a": [2, 3]})
        self.assertEqual(c, b'{"a":[2,3],"z":1}')

    def test_redact(self):
        text = "Authorization: Bearer my-secret-token with secret_password here"
        redacted = self.run_probe.redact(text, ["secret_password"])
        self.assertNotIn("my-secret-token", redacted)
        self.assertNotIn("secret_password", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)
        self.assertIn("[REDACTED] here", redacted)

    def test_probe_terminated_exit_codes(self):
        p_int = self.run_probe.ProbeTerminated(signal.SIGINT)
        self.assertEqual(p_int.exit_code, 128 + signal.SIGINT)
        p_term = self.run_probe.ProbeTerminated(signal.SIGTERM)
        self.assertEqual(p_term.exit_code, 128 + signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
