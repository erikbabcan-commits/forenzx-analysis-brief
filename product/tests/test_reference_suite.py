"""Reference-suite controls; expected outcomes remain in the authored catalog."""

from __future__ import annotations

import copy
import contextlib
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
from unittest import mock


PRODUCT = Path(__file__).resolve().parents[1]
SCRIPT = PRODUCT / "run_reference_suite.py"
spec = importlib.util.spec_from_file_location("fx006_suite_runner_tests", SCRIPT)
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


class ReferenceSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite_temp = tempfile.TemporaryDirectory(prefix="fx006-authored-test-")
        cls.suite_root = Path(cls.suite_temp.name)
        cls.canonical_path = runner.materialize(cls.suite_root)
        cls.canonical = json.loads(cls.canonical_path.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.suite_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fx006-runner-test-")
        self.root = Path(self.temp.name)
        self.manifest_path = self.root / "manifest.json"
        shutil.copytree(self.suite_root, self.root, dirs_exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    def test_all_authored_cases_pass_with_explicit_unverified_scope(self):
        result = runner.evaluate_suite(self.manifest_path)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["total"], len(self.canonical["cases"]))
        self.assertGreaterEqual(result["total"], 40)
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["failed"], 0)
        self.assertTrue(result["catalog_complete"])
        self.assertEqual(result["scope"], "LOCAL_SYNTHETIC_REFERENCE_SUITE_ONLY")
        self.assertEqual(set(result["not_tested"].values()), {"NOT_TESTED"})
        self.assertEqual({c["id"] for c in result["cases"]}, {c["id"] for c in self.canonical["cases"]})
        self.assertTrue(all(c["future_workflow"] == "NOT_TESTED" for c in result["cases"]))
        tags = {tag for case in self.canonical["cases"] for tag in case["tags"]}
        self.assertTrue({"completed", "queued", "validating", "running", "parsing", "verifying",
            "failed", "cancelled", "security_blocked", "missing_job", "access_denied",
            "missing_reference", "unknown_timezone", "identity_mismatch", "no_known_ioc",
            "prompt_injection", "truncated_json", "duplicate_keys", "invalid_type", "unknown_enum",
            "unknown_schema", "declared_version", "unknown_profile", "missing_section", "late_warning"} <= tags)
        for category in ("byte_boundary", "record_boundary"):
            boundary_cases = [case for case in self.canonical["cases"] if category in case["tags"]]
            self.assertEqual(len(boundary_cases), 3)
            self.assertTrue(all(any(position in case["tags"] for case in boundary_cases)
                                for position in ("below_limit", "at_limit", "above_limit")))

    def test_empty_partial_duplicate_or_falsely_identified_suite_cannot_pass(self):
        variants = []
        empty = copy.deepcopy(self.canonical)
        empty["cases"] = []
        variants.append(empty)
        partial = copy.deepcopy(self.canonical)
        partial["cases"] = partial["cases"][:1]
        variants.append(partial)
        duplicate = copy.deepcopy(self.canonical)
        duplicate["cases"][1]["id"] = duplicate["cases"][0]["id"]
        variants.append(duplicate)
        wrong_hash = copy.deepcopy(self.canonical)
        wrong_hash["catalog_sha256"] = "0" * 64
        variants.append(wrong_hash)
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                self.write_manifest(value)
                with self.assertRaises(runner.SuiteError):
                    runner.evaluate_suite(self.manifest_path)

    def test_modified_expected_value_is_rejected_and_cli_exits_nonzero(self):
        manifest = copy.deepcopy(self.canonical)
        manifest["cases"][0]["expected"]["status"] = "REJECTED"
        self.write_manifest(manifest)
        with self.assertRaisesRegex(runner.SuiteError, "MANIFEST_ORACLE_MISMATCH"):
            runner.evaluate_suite(self.manifest_path)
        process = subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(self.manifest_path)],
                                 cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 2)
        self.assertIn("MANIFEST_ORACLE_MISMATCH", process.stderr)
        self.assertNotIn("PASS", process.stdout)

    def test_mutant_validator_result_fails_real_comparison_and_preserves_bool_type(self):
        original = runner.validator.validate_bytes
        first_hash = self.canonical["cases"][0]["sha256"]

        def wrong_result(raw, **kwargs):
            result = original(raw, **kwargs)
            if hashlib.sha256(raw).hexdigest() == first_hash and "counts" in result["coverage"]:
                result["coverage"]["counts"]["warnings"] = True  # True must not equal 1.
                result["report_generation_allowed"] = True
            return result

        with mock.patch.object(runner.validator, "validate_bytes", side_effect=wrong_result):
            result = runner.evaluate_suite(self.manifest_path)
            with contextlib.redirect_stdout(io.StringIO()):
                cli_code = runner.main(["--manifest", str(self.manifest_path)])
        self.assertEqual(cli_code, 1)
        first = next(c for c in result["cases"] if c["id"] == self.canonical["cases"][0]["id"])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(first["status"], "FAIL")
        self.assertTrue(any(code.startswith("OUTPUT_ASSERTION_") for code in first["failed_checks"]))
        self.assertIn("COMMON_SCOPE_001_MISMATCH", first["failed_checks"])

    def test_missing_and_changed_inputs_fail_before_validation(self):
        path = self.root / self.canonical["cases"][0]["input_path"]
        raw = path.read_bytes()
        path.unlink()
        with mock.patch.object(runner.validator, "validate_bytes") as validate:
            with self.assertRaisesRegex(runner.SuiteError, "INPUT_READ_ERROR"):
                runner.evaluate_suite(self.manifest_path)
            validate.assert_not_called()
        path.write_bytes(raw + b" ")
        with mock.patch.object(runner.validator, "validate_bytes") as validate:
            with self.assertRaisesRegex(runner.SuiteError, "INPUT_INTEGRITY_MISMATCH"):
                runner.evaluate_suite(self.manifest_path)
            validate.assert_not_called()

    def test_changed_input_and_rewritten_digest_cannot_replace_authored_case(self):
        manifest = copy.deepcopy(self.canonical)
        first = manifest["cases"][0]
        path = self.root / first["input_path"]
        raw = path.read_bytes() + b" "
        path.write_bytes(raw)
        first.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.write_manifest(manifest)
        with self.assertRaisesRegex(runner.SuiteError, "MANIFEST_ORACLE_MISMATCH"):
            runner.evaluate_suite(self.manifest_path)

    def test_unknown_malformed_and_missing_assertions_cannot_be_silently_skipped(self):
        variants = []
        missing = copy.deepcopy(self.canonical)
        del missing["cases"][0]["expected"]["assertions"]
        variants.append(missing)
        unknown = copy.deepcopy(self.canonical)
        unknown["cases"][0]["expected"]["assertions"][0]["operator"] = "ignore"
        variants.append(unknown)
        bad_pointer = copy.deepcopy(self.canonical)
        bad_pointer["cases"][0]["expected"]["assertions"][0]["pointer"] = "/bad~escape"
        variants.append(bad_pointer)
        duplicate = copy.deepcopy(self.canonical)
        duplicate["cases"][0]["expected"]["assertions"].append(copy.deepcopy(duplicate["cases"][0]["expected"]["assertions"][0]))
        variants.append(duplicate)
        for index, manifest in enumerate(variants):
            with self.subTest(index=index):
                self.write_manifest(manifest)
                with self.assertRaises(runner.SuiteError):
                    runner.evaluate_suite(self.manifest_path)
        self.assertEqual(runner._resolve({"ok": None}, "/missing"), (False, None))
        self.assertFalse(runner._same_json(True, 1))

    def test_path_traversal_and_symlinks_are_rejected(self):
        for invalid in ("../outside.bin", "/tmp/outside.bin", "files/../outside.bin", "files\\outside.bin"):
            with self.subTest(path=invalid):
                manifest = copy.deepcopy(self.canonical)
                manifest["cases"][0]["input_path"] = invalid
                self.write_manifest(manifest)
                with self.assertRaisesRegex(runner.SuiteError, "INVALID_INPUT_PATH"):
                    runner.evaluate_suite(self.manifest_path)
        self.write_manifest(self.canonical)
        first = self.root / self.canonical["cases"][0]["input_path"]
        first.unlink()
        first.symlink_to(self.suite_root / self.canonical["cases"][0]["input_path"])
        with self.assertRaisesRegex(runner.SuiteError, "SYMLINK_INPUT"):
            runner.evaluate_suite(self.manifest_path)

    def test_materialization_and_reports_are_reproducible(self):
        with tempfile.TemporaryDirectory(prefix="fx006-repro-") as other:
            second_path = runner.materialize(Path(other))
            self.assertEqual(self.manifest_path.read_bytes(), second_path.read_bytes())
            for case in self.canonical["cases"]:
                self.assertEqual((self.root / case["input_path"]).read_bytes(),
                                 (Path(other) / case["input_path"]).read_bytes())
            self.assertEqual(runner.evaluate_suite(self.manifest_path), runner.evaluate_suite(second_path))

    def test_cli_foreign_cwd_report_and_explicit_overwrite(self):
        report = self.root / "result.json"
        command = [sys.executable, str(SCRIPT), "--report", str(report)]
        process = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("NOT_TESTED", process.stdout)
        saved = report.read_bytes()
        result = json.loads(saved)
        self.assertEqual(result["status"], "PASS")
        repeat = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(repeat.returncode, 2)
        self.assertEqual(report.read_bytes(), saved)
        overwrite = subprocess.run(command + ["--overwrite-report"], cwd=self.root,
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(overwrite.returncode, 0, overwrite.stderr)
        self.assertEqual(report.read_bytes(), saved)

    def test_materializer_does_not_overwrite_a_nonempty_directory(self):
        preserved = self.root / "sentinel.txt"
        preserved.write_text("KEEP_ME")
        with self.assertRaises(ValueError):
            runner.materialize(self.root)
        self.assertEqual(preserved.read_text(), "KEEP_ME")

    def test_report_does_not_copy_raw_injection_or_late_warning_text(self):
        report = json.dumps(runner.evaluate_suite(self.manifest_path))
        selected = [case for case in self.canonical["cases"]
                    if any("injection" in tag or "late_warning" in tag for tag in case["tags"])]
        self.assertGreaterEqual(len(selected), 2)
        text_assertions = [assertion["equals"] for case in selected for assertion in case.get("input_assertions", [])
                           if type(assertion["equals"]) is str and len(assertion["equals"]) > 20]
        self.assertGreaterEqual(len(text_assertions), 2)
        for value in text_assertions:
            self.assertNotIn(value, report)


if __name__ == "__main__":
    unittest.main()
