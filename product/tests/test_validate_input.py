"""Deterministic preflight tests; no model, MCP endpoint, or original evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PRODUCT = Path(__file__).resolve().parents[1]
SCRIPT = PRODUCT / "validate_input.py"
spec = importlib.util.spec_from_file_location("forenzx_input_validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)
HIT_BYTES = (PRODUCT / "fixtures" / "completed-hit.json").read_bytes()
HIT = json.loads(HIT_BYTES)
CAUTION_BYTES = (PRODUCT / "fixtures" / "completed-no-ioc.json").read_bytes()


def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def check(raw=HIT_BYTES, **kwargs):
    options = dict(profile=validator.PROFILE, expected_job_id="demo-job-hit",
                   expected_case_id="demo-case", expected_evidence_id="demo-evidence")
    options.update(kwargs)
    return validator.validate_bytes(raw, **options)


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def invocation(script=SCRIPT):
    return [sys.executable, str(script), "--profile", validator.PROFILE,
            "--expected-job-id", "demo-job-hit", "--expected-case-id", "demo-case",
            "--expected-evidence-id", "demo-evidence"]


class InputValidationTests(unittest.TestCase):
    def test_positive_fixture_has_exact_received_counts_and_no_report_authorization(self):
        result = check()
        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "STRUCTURE_VALID")
        self.assertFalse(result["report_generation_allowed"])
        self.assertEqual(result["coverage"]["counts"], {
            "findings": 1, "timeline": 1, "warnings": 1, "limitations": 1, "chain_of_custody": 1,
        })
        self.assertEqual(result["coverage"]["warning_pointers"], ["/warnings/0"])
        self.assertEqual(result["coverage"]["finding_references"][0]["artifact_path_pointer"], "/findings/0/artifact_path")
        self.assertEqual(result["input"]["sha256"], hashlib.sha256(HIT_BYTES).hexdigest())
        self.assertEqual(result["verification"]["signatures"], "NOT_VERIFIED")
        self.assertEqual(result["coverage"]["transport_completeness"], "NOT_VERIFIED")
        self.assertEqual(result["coverage"]["model_context"], "NOT_VERIFIED")
        self.assertEqual(result["coverage"]["upstream_total"], "UNKNOWN")

    def test_caution_fixture_retains_visible_missing_reference_and_time_limitations(self):
        result = check(CAUTION_BYTES, expected_job_id="demo-job-no-ioc")
        self.assertTrue(result["passed"])
        self.assertTrue({"MISSING_ARTIFACT_REFERENCE", "TIMEZONE_UNSPECIFIED", "NEGATIVE_IOC_SCOPE"} <= codes(result))
        self.assertEqual(result["coverage"]["counts"]["warnings"], 2)
        self.assertEqual(result["coverage"]["counts"]["limitations"], 3)
        self.assertIsNone(result["coverage"]["finding_references"][0]["artifact_path_pointer"])

    def test_explicit_profile_is_required(self):
        for profile in ("", "latest", "forenzx-5", "forenzx-analysis-result-unknown"):
            with self.subTest(profile=profile):
                result = check(profile=profile)
                self.assertFalse(result["passed"])
                self.assertIn("UNSUPPORTED_PROFILE", codes(result))
                self.assertIsNone(result["input"]["sha256"])

    def test_upstream_version_fields_are_not_invented_or_silently_ignored(self):
        for key in ("schema_version", "forenzx_version"):
            with self.subTest(key=key):
                value = copy.deepcopy(HIT)
                value[key] = "1"
                result = check(encode(value))
                self.assertFalse(result["passed"])
                self.assertIn("UNSUPPORTED_SCHEMA", codes(result))

    def test_unknown_fields_at_every_typed_object_are_rejected_without_echo(self):
        for location in ((), ("findings", 0), ("timeline", 0), ("chain_of_custody", 0), ("execution_record",)):
            with self.subTest(location=location):
                value = copy.deepcopy(HIT)
                target = value
                for key in location:
                    target = target[key]
                target["SECRET_PROPERTY_SENTINEL"] = "SECRET_VALUE_SENTINEL"
                result = check(encode(value))
                self.assertFalse(result["passed"])
                self.assertIn("UNKNOWN_FIELD", codes(result))
                self.assertNotIn("SECRET_", json.dumps(result))

    def test_missing_sections_are_not_defaulted_to_empty(self):
        for key in validator.SECTIONS:
            with self.subTest(section=key):
                value = copy.deepcopy(HIT)
                del value[key]
                result = check(encode(value))
                self.assertFalse(result["passed"])
                self.assertIn({"severity": "error", "code": "MISSING_FIELD", "path": f"/{key}", "message": "Required serialized field is missing."}, result["issues"])

    def test_missing_nested_defaulted_fields_are_rejected(self):
        for container, field in (("findings", "is_ai_assisted"), ("timeline", "timezone"), ("chain_of_custody", "details")):
            with self.subTest(container=container, field=field):
                value = copy.deepcopy(HIT)
                del value[container][0][field]
                self.assertFalse(check(encode(value))["passed"])
        value = copy.deepcopy(HIT)
        del value["execution_record"]["record_version"]
        self.assertIn("UNSUPPORTED_RECORD_VERSION", codes(check(encode(value))))

    def test_independent_expected_job_case_and_evidence_must_match(self):
        for field in ("job_id", "case_id", "evidence_id"):
            with self.subTest(field=field):
                result = check(**{f"expected_{field}": "different-expected-id"})
                self.assertFalse(result["passed"])
                self.assertIn("IDENTITY_MISMATCH", codes(result))
        self.assertIn("INVALID_EXPECTED_IDENTITY", codes(check(expected_case_id="")))

    def test_execution_identity_and_metadata_must_match_enclosing_result(self):
        for field in ("case_id", "evidence_id", "pack_id", "pack_version", "started_at", "completed_at"):
            with self.subTest(field=field):
                value = copy.deepcopy(HIT)
                value["execution_record"][field] = "different-value"
                result = check(encode(value))
                self.assertFalse(result["passed"])
                self.assertIn("EXECUTION_RECORD_MISMATCH", codes(result))

    def test_all_noncompleted_states_reject_findings_brief(self):
        for state in validator.STATES - {"COMPLETED"}:
            with self.subTest(state=state):
                value = copy.deepcopy(HIT)
                value["status"] = state
                if state in {"FAILED", "SECURITY_BLOCKED"}:
                    value["summary_classification"] = "ERROR"
                result = check(encode(value))
                self.assertFalse(result["passed"])
                self.assertIn("ANALYSIS_NOT_COMPLETED", codes(result))

    def test_failure_classification_invariant_is_preserved(self):
        value = copy.deepcopy(HIT)
        value["status"] = "FAILED"
        self.assertIn("INCONSISTENT_STATE", codes(check(encode(value))))

    def test_status_message_response_is_not_mistaken_for_result(self):
        result = check(encode({"job_id": "demo-job-hit", "status": "RUNNING", "message": "PRIVATE_MESSAGE_SENTINEL"}))
        self.assertIn("RESULT_UNAVAILABLE", codes(result))
        self.assertNotIn("PRIVATE_MESSAGE_SENTINEL", json.dumps(result))

    def test_json_rpc_and_mcp_wrappers_are_explicitly_unsupported(self):
        for value in ({"jsonrpc": "2.0", "result": HIT}, {"content": [{"type": "text", "text": json.dumps(HIT)}]}, {"structuredContent": HIT}):
            with self.subTest(wrapper=list(value)):
                self.assertIn("UNSUPPORTED_WRAPPER", codes(check(encode(value))))

    def test_invalid_root_and_truncated_or_multiple_documents_are_rejected(self):
        for raw in (b"[]", b"null", b"true", HIT_BYTES[:-4], HIT_BYTES + b" {}", b""):
            with self.subTest(raw_length=len(raw)):
                self.assertFalse(check(raw)["passed"])

    def test_duplicate_keys_are_rejected_even_in_opaque_nested_metadata(self):
        for raw in (b'{"job_id":"one","job_id":"two"}', b'{"input_integrity":{"SECRET_DUPLICATE":1,"SECRET_DUPLICATE":2}}'):
            result = check(raw)
            self.assertIn("DUPLICATE_JSON_KEY", codes(result))
            self.assertNotIn("SECRET_DUPLICATE", json.dumps(result))

    def test_non_finite_numbers_and_huge_numeric_fields_are_rejected_safely(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            raw = b'{"value":' + token + b'}'
            self.assertIn("NON_FINITE_NUMBER", codes(check(raw)))
        value = copy.deepcopy(HIT)
        value["duration_seconds"] = 10 ** 1000
        self.assertIn("INVALID_NUMBER", codes(check(encode(value))))

    def test_invalid_utf8_and_lone_surrogate_are_rejected(self):
        self.assertIn("INVALID_UTF8", codes(check(b"\xff")))
        self.assertIn("INVALID_UNICODE", codes(check(b'{"value":"\\ud800"}')))
        self.assertIn("INVALID_UNICODE", codes(check(b'{"\\ud800":1}')))

    def test_byte_boundary_below_on_and_above_limit(self):
        length = len(HIT_BYTES)
        self.assertTrue(check(limits=validator.Limits(max_bytes=length + 1))["passed"])
        self.assertTrue(check(limits=validator.Limits(max_bytes=length))["passed"])
        result = check(limits=validator.Limits(max_bytes=length - 1))
        self.assertIn("BYTE_LIMIT_EXCEEDED", codes(result))
        self.assertIsNone(result["input"]["sha256"])
        self.assertFalse(result["input"]["complete_byte_read"])

    def test_aggregate_section_record_boundary(self):
        self.assertTrue(check(limits=validator.Limits(max_records=6))["passed"])
        self.assertTrue(check(limits=validator.Limits(max_records=5))["passed"])
        self.assertIn("RECORD_LIMIT_EXCEEDED", codes(check(limits=validator.Limits(max_records=4))))

    def test_depth_boundary_and_parser_recursion_fail_closed(self):
        value = copy.deepcopy(HIT)
        value["input_integrity"] = {"a": {"b": {"c": "demo"}}}
        raw = encode(value)
        self.assertTrue(check(raw, limits=validator.Limits(max_depth=5))["passed"])
        self.assertIn("DEPTH_LIMIT_EXCEEDED", codes(check(raw, limits=validator.Limits(max_depth=4))))
        self.assertIn("DEPTH_LIMIT_EXCEEDED", codes(check(b"[" * 2000 + b"0" + b"]" * 2000)))

    def test_node_budget_and_invalid_limit_configuration(self):
        self.assertIn("NODE_LIMIT_EXCEEDED", codes(check(limits=validator.Limits(max_nodes=1))))
        for field, value in (("max_bytes", 0), ("max_bytes", 4_194_305), ("max_records", -1), ("max_depth", 65), ("max_nodes", True)):
            with self.subTest(field=field):
                self.assertIn("INVALID_LIMIT_CONFIGURATION", codes(check(limits=validator.Limits(**{field: value}))))

    def test_late_warning_is_counted_without_leaking_or_truncating_text(self):
        value = copy.deepcopy(HIT)
        value["findings"][0]["description"] = "x" * 150_000
        value["warnings"].append("LAST_WARNING_PRIVATE_SENTINEL")
        raw = encode(value)
        result = check(raw)
        self.assertTrue(result["passed"])
        self.assertEqual(result["coverage"]["counts"]["warnings"], 2)
        self.assertEqual(result["coverage"]["warning_pointers"][-1], "/warnings/1")
        self.assertEqual(result["input"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("LAST_WARNING_PRIVATE_SENTINEL", json.dumps(result))
        self.assertNotIn("x" * 50, json.dumps(result))

    def test_invalid_nested_types_never_silently_coerce(self):
        mutations = [
            (("duration_seconds",), True), (("duration_seconds",), "2"),
            (("status",), []), (("status",), {}), (("summary_classification",), {}),
            (("warnings",), "warning"), (("warnings", 0), None),
            (("input_integrity",), []), (("findings", 0), "not-object"),
            (("findings", 0, "classification"), {}), (("findings", 0, "is_ai_assisted"), 0),
            (("findings", 0, "raw_evidence_ref"), "reference"),
            (("timeline", 0, "relevance_score"), True), (("timeline", 0, "relevance_score"), 1.1),
            (("chain_of_custody", 0, "details"), []), (("execution_record",), None),
            (("execution_record", "exit_code"), False), (("execution_record", "exit_code"), "0"),
            (("execution_record", "tool_command"), "tool"), (("execution_record", "tool_command", 0), 1),
        ]
        for path, new_value in mutations:
            with self.subTest(path=path, value=new_value):
                value = copy.deepcopy(HIT)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = new_value
                self.assertFalse(check(encode(value))["passed"])

    def test_unknown_enum_values_are_rejected_without_echo(self):
        for path in (("status",), ("summary_classification",), ("findings", 0, "classification"), ("findings", 0, "confidence"), ("findings", 0, "severity")):
            value = copy.deepcopy(HIT)
            target = value
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = "UNKNOWN_PRIVATE_ENUM_SENTINEL"
            result = check(encode(value))
            self.assertIn("UNSUPPORTED_ENUM", codes(result))
            self.assertNotIn("UNKNOWN_PRIVATE_ENUM_SENTINEL", json.dumps(result))

    def test_duplicate_finding_id_and_negative_summary_conflict(self):
        value = copy.deepcopy(HIT)
        value["findings"].append(copy.deepcopy(value["findings"][0]))
        self.assertIn("DUPLICATE_FINDING_ID", codes(check(encode(value))))
        value = copy.deepcopy(HIT)
        value["summary_classification"] = "NO_KNOWN_IOC"
        self.assertIn("SUMMARY_FINDING_CONFLICT", codes(check(encode(value))))

    def test_custody_hash_conflict_is_rejected_but_explicit_breach_is_preserved(self):
        value = copy.deepcopy(HIT)
        value["chain_of_custody"][0]["sha256_after"] = "c" * 64
        self.assertIn("CUSTODY_HASH_CONFLICT", codes(check(encode(value))))
        value["chain_of_custody"][0]["action"] = "INTEGRITY_BREACH_DETECTED"
        result = check(encode(value))
        self.assertTrue(result["passed"])
        self.assertIn("INTEGRITY_BREACH_RECORDED", codes(result))
        self.assertEqual(result["verification"]["source_authenticity"], "NOT_VERIFIED")

    def test_hash_format_and_execution_exit_require_review(self):
        value = copy.deepcopy(HIT)
        value["execution_record"]["input_root_sha256"] = "not-a-hash"
        self.assertIn("INVALID_HASH_FORMAT", codes(check(encode(value))))
        value = copy.deepcopy(HIT)
        value["execution_record"]["exit_code"] = 1
        self.assertIn("NONZERO_EXECUTION_EXIT", codes(check(encode(value))))

    def test_timestamp_order_and_unknown_time_are_distinguished(self):
        value = copy.deepcopy(HIT)
        value["completed_at"] = value["execution_record"]["completed_at"] = "2025-12-31T12:00:00+00:00"
        self.assertIn("TIME_ORDER_CONFLICT", codes(check(encode(value))))
        value = copy.deepcopy(HIT)
        value["findings"][0]["timestamp"] = "UNKNOWN_PRIVATE_TIMESTAMP"
        result = check(encode(value))
        self.assertTrue(result["passed"])
        self.assertIn("TIMESTAMP_NOT_INTERPRETED", codes(result))
        self.assertNotIn("UNKNOWN_PRIVATE_TIMESTAMP", json.dumps(result))

    def test_diagnostic_cap_still_remembers_later_error(self):
        value = copy.deepcopy(HIT)
        value["findings"] = []
        for i in range(110):
            item = copy.deepcopy(HIT["findings"][0])
            item.update(id=f"demo-{i}", artifact_path="", raw_evidence_ref=None)
            value["findings"].append(item)
        value["execution_record"]["exit_code"] = "invalid"
        result = check(encode(value))
        self.assertFalse(result["passed"])
        self.assertTrue(result["diagnostics_limited"])
        self.assertEqual(len(result["issues"]), 100)

    def test_standalone_cli_from_temporary_file_and_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "independent_validator.py"
            shutil.copyfile(SCRIPT, target)
            completed = subprocess.run(invocation(target), input=HIT_BYTES, capture_output=True, cwd=directory, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            self.assertEqual(completed.stderr, b"")
            self.assertEqual(json.loads(completed.stdout)["status"], "STRUCTURE_VALID")

    def test_cli_file_is_not_modified_and_oversize_reads_only_limit_plus_one(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.json"
            target.write_bytes(HIT_BYTES)
            result = subprocess.run(invocation() + ["--input", str(target)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(target.read_bytes(), HIT_BYTES)
            limit = len(HIT_BYTES) - 100
            result = subprocess.run(invocation() + ["--input", str(target), "--max-bytes", str(limit)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertEqual(report["input"]["bytes_read"], limit + 1)
            self.assertFalse(report["input"]["complete_byte_read"])
            self.assertIsNone(report["input"]["sha256"])

    def test_cli_errors_are_json_without_argument_or_path_leaks(self):
        cases = [
            invocation() + ["--input", "/does-not-exist/SECRET_PATH_SENTINEL.json"],
            invocation() + ["--max-bytes", "SECRET_ARGUMENT_SENTINEL"],
            [sys.executable, str(SCRIPT), "--unknown", "SECRET_ARGUMENT_SENTINEL"],
        ]
        for command in cases:
            with self.subTest(case=cases.index(command)):
                result = subprocess.run(command, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["passed"])
                self.assertEqual(result.stderr, b"")
                self.assertNotIn(b"SECRET_", result.stdout)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Requires POSIX FIFO support")
    def test_fifo_input_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fifo"
            os.mkfifo(path)
            result = subprocess.run(invocation() + ["--input", str(path)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn("INPUT_NOT_REGULAR_FILE", codes(json.loads(result.stdout)))

    def test_bounded_reader_handles_partial_reads(self):
        class Partial(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 7))
        self.assertEqual(validator.read_bounded(Partial(b"a" * 20), 15), b"a" * 16)
        self.assertEqual(validator.read_bounded(Partial(b"a" * 15), 15), b"a" * 15)


if __name__ == "__main__":
    unittest.main()
