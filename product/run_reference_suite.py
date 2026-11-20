#!/usr/bin/env python3
"""Evaluate authored synthetic FX-006 expectations against the local validator.

No MCP, network, model or generated findings brief is exercised here. The
materializer and catalog author expected results; this runner only compares.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any


PRODUCT = Path(__file__).resolve().parent
MAX_MANIFEST_BYTES = 2_097_152
MAX_INPUT_BYTES = 4_194_305
MAX_TOTAL_INPUT_BYTES = 33_554_432
MAX_CASES = 200
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}\Z")
INPUT_KINDS = {"analysis_result", "status_response", "rpc_error", "malformed_json", "boundary_result"}
LIMIT_KEYS = {"max_bytes", "max_records", "max_depth", "max_nodes"}
COMMON_EXPECTATIONS = {
    "/report_generation_allowed": False,
    "/coverage/scope": "RECEIVED_JSON_ONLY",
    "/coverage/upstream_total": "UNKNOWN",
    "/coverage/transport_completeness": "NOT_VERIFIED",
    "/coverage/model_context": "NOT_VERIFIED",
    "/verification/source_authenticity": "NOT_VERIFIED",
    "/verification/original_artifacts": "NOT_VERIFIED",
    "/verification/signatures": "NOT_VERIFIED",
    "/limits/basis": "PROVISIONAL_ENGINEERING_LIMITS_NOT_LLM_CONTEXT",
}
NOT_TESTED = {
    "live_mcp_client": "NOT_TESTED",
    "live_authentication_and_authorization": "NOT_TESTED",
    "transport_completeness": "NOT_TESTED",
    "model_context_capacity": "NOT_TESTED",
    "llm_prompt_injection_resistance": "NOT_TESTED",
    "generated_brief_fidelity": "NOT_TESTED",
}


class SuiteError(Exception):
    """Fixed error codes deliberately omit paths and authored/input values."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SuiteError("MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _module(PRODUCT / "validate_input.py", "fx006_reference_validator")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _no_constant(value):
    raise ValueError("non-finite JSON")


def _json(raw: bytes):
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_unique_object,
                      parse_constant=_no_constant)


def _shape(value: Any, required: set[str], optional: set[str] | None = None) -> None:
    if type(value) is not dict or required - value.keys() or value.keys() - required - (optional or set()):
        raise SuiteError("INVALID_MANIFEST_SHAPE")


def _identifier(value: Any) -> bool:
    return type(value) is str and ID.fullmatch(value) is not None


def _pointer_parts(pointer: Any) -> list[str]:
    if type(pointer) is not str or not pointer.startswith("/") or len(pointer) > 512:
        raise SuiteError("INVALID_ASSERTION_POINTER")
    parts = pointer[1:].split("/")
    if any(not part or re.search(r"~(?![01])", part) for part in parts):
        raise SuiteError("INVALID_ASSERTION_POINTER")
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def _assertions(value: Any) -> None:
    if type(value) is not list or len(value) > 100:
        raise SuiteError("INVALID_ASSERTIONS")
    pointers = set()
    for assertion in value:
        _shape(assertion, {"pointer", "equals"})
        _pointer_parts(assertion["pointer"])
        if assertion["pointer"] in pointers:
            raise SuiteError("DUPLICATE_ASSERTION_POINTER")
        pointers.add(assertion["pointer"])
        try:
            json.dumps(assertion["equals"], allow_nan=False)
        except (ValueError, TypeError, RecursionError):
            raise SuiteError("INVALID_ASSERTION_VALUE") from None


def _resolve(value: Any, pointer: str) -> tuple[bool, Any]:
    for part in _pointer_parts(pointer):
        if type(value) is dict and part in value:
            value = value[part]
        elif type(value) is list and re.fullmatch(r"0|[1-9][0-9]*", part) and int(part) < len(value):
            value = value[int(part)]
        else:
            return False, None
    return True, value


def _same_json(a: Any, b: Any) -> bool:
    # Python treats True == 1; reference assertions must preserve JSON types.
    return json.dumps(a, sort_keys=True, ensure_ascii=True, allow_nan=False) == json.dumps(
        b, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _read_regular(path: Path, maximum: int) -> bytes:
    try:
        if path.is_symlink():
            raise SuiteError("SYMLINK_INPUT")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise SuiteError("INPUT_NOT_REGULAR_FILE")
            if info.st_size > maximum:
                raise SuiteError("SUITE_RESOURCE_LIMIT")
            raw = stream.read(maximum + 1)
            if len(raw) > maximum:
                raise SuiteError("SUITE_RESOURCE_LIMIT")
            return raw
    except OSError:
        raise SuiteError("INPUT_READ_ERROR") from None


def _input_path(root: Path, relative: Any) -> Path:
    if type(relative) is not str or not relative or "\\" in relative:
        raise SuiteError("INVALID_INPUT_PATH")
    pieces = relative.split("/")
    if any(part in {"", ".", ".."} for part in pieces) or PurePosixPath(relative).is_absolute():
        raise SuiteError("INVALID_INPUT_PATH")
    current = root
    for part in pieces:
        current = current / part
        if current.is_symlink():
            raise SuiteError("SYMLINK_INPUT")
    if not current.resolve().is_relative_to(root.resolve()):
        raise SuiteError("INVALID_INPUT_PATH")
    return current


def load_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read_regular(path, MAX_MANIFEST_BYTES)
    try:
        manifest = _json(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise SuiteError("INVALID_MANIFEST_JSON") from None
    _shape(manifest, {"format_version", "suite_id", "profile", "upstream_commit", "synthetic", "catalog_sha256", "cases"})
    if type(manifest["format_version"]) is not int or manifest["format_version"] != 1:
        raise SuiteError("UNSUPPORTED_MANIFEST_VERSION")
    if not _identifier(manifest["suite_id"]) or manifest["synthetic"] is not True:
        raise SuiteError("INVALID_SUITE_IDENTITY")
    if manifest["profile"] != validator.PROFILE or manifest["upstream_commit"] != validator.UPSTREAM_COMMIT:
        raise SuiteError("UNSUPPORTED_SUITE_PROFILE")
    if type(manifest["catalog_sha256"]) is not str or not SHA256.fullmatch(manifest["catalog_sha256"]):
        raise SuiteError("INVALID_CATALOG_HASH")
    cases = manifest["cases"]
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise SuiteError("INVALID_CASE_COUNT")
    ids = set()
    inputs = set()
    required = {"id", "title", "tags", "input_kind", "input_path", "sha256", "bytes", "profile", "expected_identity", "limits", "expected", "future_workflow"}
    for case in cases:
        _shape(case, required, {"input_assertions"})
        if not _identifier(case["id"]) or case["id"] in ids:
            raise SuiteError("INVALID_OR_DUPLICATE_CASE_ID")
        ids.add(case["id"])
        _input_path(path.parent, case["input_path"])
        if case["input_path"] in inputs:
            raise SuiteError("DUPLICATE_INPUT_PATH")
        inputs.add(case["input_path"])
        if type(case["title"]) is not str or not case["title"].strip():
            raise SuiteError("INVALID_CASE_METADATA")
        if type(case["tags"]) is not list or any(not _identifier(tag) for tag in case["tags"]):
            raise SuiteError("INVALID_CASE_METADATA")
        if type(case["input_kind"]) is not str or case["input_kind"] not in INPUT_KINDS:
            raise SuiteError("INVALID_INPUT_KIND")
        if not _identifier(case["profile"]) or type(case["bytes"]) is not int or not 0 <= case["bytes"] <= MAX_INPUT_BYTES:
            raise SuiteError("INVALID_CASE_METADATA")
        if type(case["sha256"]) is not str or not SHA256.fullmatch(case["sha256"]):
            raise SuiteError("INVALID_INPUT_HASH")
        _shape(case["expected_identity"], {"job_id", "case_id", "evidence_id"})
        if any(type(value) is not str or len(value) > 256 for value in case["expected_identity"].values()):
            raise SuiteError("INVALID_EXPECTED_IDENTITY")
        _shape(case["limits"], LIMIT_KEYS)
        if any(type(value) is not int or not 0 <= value <= 10_000_000 for value in case["limits"].values()):
            raise SuiteError("INVALID_LIMIT_CONFIGURATION")
        _shape(case["expected"], {"status", "issue_codes", "assertions"})
        if type(case["expected"]["status"]) is not str or case["expected"]["status"] not in {"STRUCTURE_VALID", "REJECTED"}:
            raise SuiteError("INVALID_EXPECTED_STATUS")
        codes = case["expected"]["issue_codes"]
        if type(codes) is not list or any(type(code) is not str or not CODE.fullmatch(code) for code in codes) or len(set(codes)) != len(codes):
            raise SuiteError("INVALID_EXPECTED_CODES")
        _assertions(case["expected"]["assertions"])
        _assertions(case.get("input_assertions", []))
        _shape(case["future_workflow"], {"expected_behavior", "validation_status"})
        if type(case["future_workflow"]["expected_behavior"]) is not str or not case["future_workflow"]["expected_behavior"].strip() or case["future_workflow"]["validation_status"] != "NOT_TESTED":
            raise SuiteError("INVALID_FUTURE_WORKFLOW_SCOPE")
    return manifest, raw


def evaluate_suite(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest, manifest_bytes = load_manifest(manifest_path)
    # Bind external/saved manifests to the full authored oracle and the exact
    # deterministic inputs, not merely a self-declared digest. A deleted case,
    # edited expectation or replaced input+hash cannot masquerade as this suite.
    # The materializer does not call the validator or derive expected verdicts.
    with tempfile.TemporaryDirectory(prefix="fx006-oracle-") as folder:
        canonical_path = materialize(Path(folder))
        canonical, _ = load_manifest(canonical_path)
    if not _same_json(manifest, canonical):
        raise SuiteError("MANIFEST_ORACLE_MISMATCH")
    inputs = []
    total_bytes = 0
    for case in manifest["cases"]:
        raw = _read_regular(_input_path(manifest_path.parent, case["input_path"]), MAX_INPUT_BYTES)
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_INPUT_BYTES:
            raise SuiteError("SUITE_RESOURCE_LIMIT")
        if len(raw) != case["bytes"] or hashlib.sha256(raw).hexdigest() != case["sha256"]:
            raise SuiteError("INPUT_INTEGRITY_MISMATCH")
        inputs.append(raw)
    results = []
    for case, raw in zip(manifest["cases"], inputs):
        failures = []
        input_assertions = case.get("input_assertions", [])
        if input_assertions:
            try:
                parsed = _json(raw)
                for index, assertion in enumerate(input_assertions):
                    found, actual = _resolve(parsed, assertion["pointer"])
                    if not found or not _same_json(actual, assertion["equals"]):
                        failures.append(f"INPUT_ASSERTION_{index + 1:03}_MISMATCH")
            except (ValueError, UnicodeError, RecursionError):
                failures.append("INPUT_ASSERTION_JSON_INVALID")
        identity = case["expected_identity"]
        result = validator.validate_bytes(raw, profile=case["profile"],
            expected_job_id=identity["job_id"], expected_case_id=identity["case_id"],
            expected_evidence_id=identity["evidence_id"], limits=validator.Limits(**case["limits"]))
        observed_status = result.get("status")
        if observed_status != case["expected"]["status"]:
            failures.append("STATUS_MISMATCH")
        if result.get("passed") is not (case["expected"]["status"] == "STRUCTURE_VALID"):
            failures.append("PASSED_FLAG_MISMATCH")
        observed_codes = sorted({item["code"] for item in result.get("issues", [])})
        if observed_codes != sorted(case["expected"]["issue_codes"]):
            failures.append("ISSUE_CODES_MISMATCH")
        for index, (pointer, expected) in enumerate(COMMON_EXPECTATIONS.items()):
            found, actual = _resolve(result, pointer)
            if not found or not _same_json(actual, expected):
                failures.append(f"COMMON_SCOPE_{index + 1:03}_MISMATCH")
        for index, assertion in enumerate(case["expected"]["assertions"]):
            found, actual = _resolve(result, assertion["pointer"])
            if not found or not _same_json(actual, assertion["equals"]):
                failures.append(f"OUTPUT_ASSERTION_{index + 1:03}_MISMATCH")
        results.append({
            "id": case["id"], "input_kind": case["input_kind"], "input_sha256": case["sha256"],
            "input_bytes": len(raw), "profile": case["profile"], "status": "FAIL" if failures else "PASS",
            "observed_validator_status": observed_status, "observed_issue_codes": observed_codes,
            "input_assertions": len(input_assertions), "output_assertions": len(case["expected"]["assertions"]),
            "failed_checks": failures, "future_workflow": "NOT_TESTED",
        })
    passed = sum(case["status"] == "PASS" for case in results)
    return {
        "format_version": 1, "suite_id": manifest["suite_id"], "synthetic": True,
        "profile": manifest["profile"], "upstream_commit": manifest["upstream_commit"],
        "catalog_sha256": manifest["catalog_sha256"], "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "validator_version": validator.VERSION,
        "validator_source_sha256": hashlib.sha256((PRODUCT / "validate_input.py").read_bytes()).hexdigest(),
        "runner_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "LOCAL_SYNTHETIC_REFERENCE_SUITE_ONLY", "catalog_complete": True,
        "status": "PASS" if passed == len(results) else "FAIL",
        "total": len(results), "passed": passed, "failed": len(results) - passed,
        "not_tested": dict(NOT_TESTED), "cases": results,
    }


def materialize(output: Path) -> Path:
    builder = _module(PRODUCT / "reference" / "build_fixtures.py", "fx006_reference_builder")
    return Path(builder.materialize_suite(output))


def _write_report(path: Path, report: dict[str, Any], overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SuiteError("REPORT_WRITE_ERROR")
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    flags |= os.O_TRUNC if overwrite else os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2) + "\n")
    except OSError:
        raise SuiteError("REPORT_WRITE_ERROR") from None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise SuiteError("INVALID_CLI")


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path, help="Evaluate an already materialized manifest.")
    source.add_argument("--materialize", type=Path, help="Retain generated inputs in a new or empty directory.")
    parser.add_argument("--report", type=Path, help="Write deterministic JSON results to a new file.")
    parser.add_argument("--overwrite-report", action="store_true", help="Explicitly allow replacing the report file.")
    try:
        args = parser.parse_args(argv)
        if args.overwrite_report and args.report is None:
            raise SuiteError("INVALID_CLI")
        if args.manifest is not None:
            report = evaluate_suite(args.manifest)
        elif args.materialize is not None:
            report = evaluate_suite(materialize(args.materialize))
        else:
            with tempfile.TemporaryDirectory(prefix="fx006-reference-") as folder:
                report = evaluate_suite(materialize(Path(folder)))
        if args.report is not None:
            _write_report(args.report, report, args.overwrite_report)
        print(f"FX-006 {report['status']}: {report['passed']}/{report['total']} local synthetic cases; {report['failed']} failed.")
        print("Live MCP, authorization, model context and LLM injection resistance: NOT_TESTED.")
        for case in report["cases"]:
            if case["status"] == "FAIL":
                print(f"{case['id']}: {', '.join(case['failed_checks'])}")
        return 0 if report["status"] == "PASS" else 1
    except (SuiteError, OSError, ValueError, TypeError, KeyError, RecursionError):
        error = sys.exc_info()[1]
        code = error.code if isinstance(error, SuiteError) else "SUITE_PROCESSING_ERROR"
        print(f"FX-006 ERROR: {code}; no successful suite result was issued.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
