"""Verify the CLI's source and model traffic with independent loopback receivers."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from provider_probe import FIXTURE, endpoint


class ReportClientTests(unittest.TestCase):
    def exercise(self, overrides=(), *, malformed=False, model_status=200):
        raw = FIXTURE.read_bytes()
        calls = []

        def source(path, body):
            calls.append(("source", path, json.loads(body)))
            result = raw.rstrip()[:-1] if malformed else raw
            return 200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
                "content": [{"type": "text", "text": result.decode()}],
            }}).encode()

        def model(path, body):
            calls.append(("model", path, body))
            return model_status, b""

        def fallback(path, body):
            calls.append(("fallback", path, body))
            return 200, b""

        with endpoint(source) as hub, endpoint(model) as primary, endpoint(fallback) as secondary:
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("report_client.py")),
                 "--hub-port", str(hub), "--approved-model-port", str(primary),
                 *[str(secondary) if arg == "SECONDARY" else arg for arg in overrides]],
                capture_output=True, timeout=10,
            )
        return proc, calls

    def test_unknown_profile_never_reads_or_dispatches(self):
        for override in (("--provider", "unknown"), ("--model", "unknown"),
                         ("--model-port", "SECONDARY"), ("--retention", ""), ("--training", "enabled")):
            with self.subTest(override=override):
                proc, calls = self.exercise(override)
                self.assertEqual((proc.returncode, proc.stdout, proc.stderr, calls),
                                 (2, b"", b"UNAPPROVED_PROFILE\n", []))

    def test_positive_control_delivers_exact_fixture_once(self):
        proc, calls = self.exercise()
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"OK\n", b""))
        self.assertEqual(calls, [
            ("source", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "forenzx_analysis_results", "arguments": {"job_id": "demo-job-hit"}}}),
            ("model", "/model", FIXTURE.read_bytes()),
        ])

    def test_partial_source_data_never_reaches_model_or_console(self):
        proc, calls = self.exercise(malformed=True)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (2, b"", b"INVALID_RESULT\n"))
        self.assertEqual([call[0] for call in calls], ["source"])

    def test_primary_failure_is_not_retried(self):
        proc, calls = self.exercise(model_status=503)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (2, b"", b"PRIMARY_UNAVAILABLE\n"))
        self.assertEqual([call[0] for call in calls], ["source", "model"])
