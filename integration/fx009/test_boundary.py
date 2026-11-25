"""Independent assertions on the synthetic reference path and on its receivers."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import provider_probe as probe
from provider_probe import Receiver, scenario
from validate_input import no_duplicate_keys


class BoundaryTests(unittest.TestCase):
    def test_denied_profile_stops_before_fixture_read(self):
        item = scenario("changed_endpoint")
        self.assertEqual(item["events"], ["reply"])
        self.assertEqual(item["reason"], "UNAPPROVED_PROFILE")
        self.assertFalse(item["client_contains_marker"])
        self.assertEqual(item["fallback"]["post_requests"], 0)

    def test_nonempty_fragment_is_counted_even_without_marker(self):
        events = []
        receiver = Receiver("test", b"unique-marker", b"full-result", events)
        receiver.handle("/model", b"full")
        self.assertEqual(receiver.counts(), {"post_requests": 1, "nonempty_bodies": 1,
                                             "with_marker": 0, "exact_result": 0})

    def test_outage_observed_at_primary_and_fallback_remains_unused(self):
        item = scenario("primary_unavailable")
        self.assertEqual(item["events"], ["read", "reply", "primary"])
        self.assertEqual(item["reason"], "PRIMARY_UNAVAILABLE")
        self.assertEqual(item["primary"]["exact_result"], 1)
        self.assertEqual(item["fallback"]["post_requests"], 0)

    def test_invalid_snapshot_never_reaches_client_or_provider(self):
        item = scenario("incomplete")
        self.assertEqual(item["source_reads"], 1)
        self.assertEqual(item["reason"], "INVALID_RESULT")
        self.assertTrue(item["checks"]["client_received_exact_allowed_reply"])
        self.assertEqual(item["primary"]["nonempty_bodies"], 0)

    def test_wire_error_and_delivery_against_independent_expectations(self):
        # Observe the original adapter and real HTTP exchanges; retain synthetic bytes only in memory.
        real_adapter = probe.reference_result
        real_exchange = probe.exchange
        for name, reason, expected_reads in (("unapproved_provider", "UNAPPROVED_PROFILE", 0),
                                             ("incomplete", "INVALID_RESULT", 1),
                                             ("approved", "OK", 1)):
            with self.subTest(scenario=name):
                snapshots, replies, posts = [], [], []

                def measured_adapter(selected, approved, read_case):
                    def read():
                        snapshot = read_case()
                        snapshots.append(snapshot)
                        return snapshot
                    return real_adapter(selected, approved, read)

                def measured_exchange(port, path, body=None):
                    status, wire = real_exchange(port, path, body)
                    if path == "/mcp":
                        replies.append((status, json.loads(wire, object_pairs_hook=no_duplicate_keys)))
                    elif path == "/model":
                        posts.append(body)
                    return status, wire

                with (patch.object(probe, "reference_result", measured_adapter),
                      patch.object(probe, "exchange", measured_exchange)):
                    row = scenario(name)

                self.assertEqual(len(snapshots), expected_reads)
                self.assertEqual(row["source_reads"], expected_reads)
                self.assertEqual(row["reason"], reason)
                self.assertEqual(len(replies), 1)
                status, reply = replies[0]
                self.assertEqual(status, 200)
                delivered = name == "approved"
                text = snapshots[0].decode("utf-8") if delivered else reason
                # An extra field or a partial case string must fail even if the full marker is absent.
                expected = {"jsonrpc": "2.0", "id": 1, "result": {"isError": not delivered,
                            "content": [{"type": "text", "text": text}]}}
                self.assertTrue(reply == expected, "MCP reply differed from the independent contract")
                self.assertIs(reply["result"]["isError"], not delivered)
                self.assertEqual(len(posts), int(delivered))
                self.assertEqual(row["primary"]["post_requests"], int(delivered))
                self.assertEqual(row["fallback"]["post_requests"], 0)
                if delivered:
                    self.assertTrue(posts[0] == snapshots[0], "provider received different bytes")
                    self.assertEqual(row["primary"]["exact_result"], 1)

    def test_cli_report_has_no_console_logs_or_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            report = cwd / "report.json"
            result = subprocess.run([sys.executable, "-I", "-B", probe.__file__, "--output", str(report)],
                                    cwd=cwd, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertEqual((len(result.stdout), len(result.stderr)), (0, 0))
            self.assertEqual(set(cwd.iterdir()), {report})
            rows = json.loads(report.read_bytes())["scenarios"]
            self.assertEqual([item["scenario"] for item in rows], list(probe.SCENARIOS))
            self.assertTrue(all(item["verdict"] == "PASS" for item in rows))
