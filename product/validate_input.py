#!/usr/bin/env python3
"""Read-only preflight for one pinned, extracted ForenZX AnalysisResult JSON.

No MCP transport, model call, report generation, or signature verification lives
here. A passing result covers the bytes supplied to this process only. This
standalone file intentionally has no package-relative runtime dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO


VERSION = "0.1.0"
UPSTREAM_COMMIT = "0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f"
PROFILE = "forenzx-analysis-result-0e4c7fae"
SECTIONS = ("findings", "timeline", "warnings", "limitations", "chain_of_custody")
CLASSIFICATIONS = {"HIT", "SUSPICIOUS", "NO_KNOWN_IOC", "INCONCLUSIVE", "ERROR"}
STATES = {"QUEUED", "VALIDATING", "RUNNING", "PARSING", "VERIFYING", "COMPLETED", "FAILED", "CANCELLED", "SECURITY_BLOCKED"}
SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}
SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
CONTAINER_DIGEST = re.compile(r"sha256:[a-fA-F0-9]{64}\Z")
MAX_DIAGNOSTICS = 100

# These are this product's serialized-input profile, not an upstream schema ID.
# model_dump(mode="json") emits defaulted fields too. Requiring them prevents
# silently treating a missing section or nullable field as empty or null.
ROOT_FIELDS = {
    "job_id", "pack_id", "pack_version", "case_id", "evidence_id", "started_at",
    "completed_at", "duration_seconds", "status", "summary_classification",
    "input_integrity", "findings", "timeline", "warnings", "limitations",
    "chain_of_custody", "execution_record",
}
FINDING_FIELDS = {
    "id", "classification", "confidence", "ioc_type", "ioc_name", "artifact_path",
    "artifact_hash", "timestamp", "severity", "description", "raw_evidence_ref",
    "is_ai_assisted",
}
TIMELINE_FIELDS = {
    "timestamp", "event_type", "source_tool", "description", "relevance_score",
    "original_timestamp", "timezone", "normalization_notes",
}
CUSTODY_FIELDS = {"timestamp", "action", "actor", "sha256_before", "sha256_after", "details"}
EXECUTION_FIELDS = {
    "record_version", "case_id", "evidence_id", "pack_id", "pack_version",
    "container_digest", "input_root_sha256", "ioc_bundle_sha256", "ioc_bundle_version",
    "tool_command", "exit_code", "started_at", "completed_at",
    "manifest_canonical_sha256", "server_hmac_signature", "signature_algorithm",
    "signing_key_id", "ed25519_signature",
}


@dataclass(frozen=True)
class Limits:
    """Provisional engineering limits; never a model-token-budget claim."""

    max_bytes: int = 262_144
    max_records: int = 1_000
    max_depth: int = 32
    max_nodes: int = 20_000

    def valid(self) -> bool:
        bounds = ((self.max_bytes, 4_194_304), (self.max_records, 100_000),
                  (self.max_depth, 64), (self.max_nodes, 250_000))
        return all(type(value) is int and 1 <= value <= ceiling for value, ceiling in bounds)


class InputError(Exception):
    def __init__(self, code: str):
        self.code = code


class CLIError(Exception):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse messages may echo input paths, IDs, or other user arguments.
        raise CLIError()


class Check:
    def __init__(self) -> None:
        self.issues: list[dict[str, str]] = []
        self.has_errors = False
        self.limited = False

    def issue(self, code: str, path: str, message: str, severity: str = "error") -> None:
        self.has_errors = self.has_errors or severity == "error"
        if len(self.issues) < MAX_DIAGNOSTICS:
            self.issues.append({"severity": severity, "code": code, "path": path, "message": message})
        else:
            self.limited = True

    def object(self, value: Any, fields: set[str] | None, path: str) -> bool:
        if type(value) is not dict:
            self.issue("INVALID_TYPE", path, "Expected an object.")
            return False
        if fields is not None:
            for key in sorted(fields - value.keys()):
                self.issue("MISSING_FIELD", f"{path}/{key}", "Required serialized field is missing.")
            if value.keys() - fields:
                # Do not echo an attacker-controlled property name into logs.
                self.issue("UNKNOWN_FIELD", path, "Object contains fields outside the supported input profile.")
        return True

    def string(self, value: Any, path: str, *, nullable: bool = False, nonempty: bool = False) -> bool:
        if nullable and value is None:
            return True
        if type(value) is not str:
            self.issue("INVALID_TYPE", path, "Expected a string" + (" or null." if nullable else "."))
            return False
        if nonempty and not value.strip():
            self.issue("EMPTY_REQUIRED_VALUE", path, "Required value must not be empty.")
            return False
        return True

    def number(self, value: Any, path: str, low: float | None = None, high: float | None = None) -> bool:
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            self.issue("INVALID_NUMBER", path, "Expected a finite JSON number; booleans are not numbers.")
            return False
        if (low is not None and value < low) or (high is not None and value > high):
            self.issue("NUMBER_OUT_OF_RANGE", path, "Number is outside the supported range.")
            return False
        return True

    def enum(self, value: Any, choices: set[str], path: str) -> bool:
        if type(value) is not str or value not in choices:
            self.issue("UNSUPPORTED_ENUM", path, "Value is not supported by this input profile.")
            return False
        return True

    def array(self, value: Any, path: str) -> bool:
        if type(value) is not list:
            self.issue("INVALID_TYPE", path, "Expected an array.")
            return False
        return True

    def hash(self, value: Any, path: str, *, empty: bool = False, container: bool = False) -> None:
        if not self.string(value, path):
            return
        if empty and value == "":
            return
        pattern = CONTAINER_DIGEST if container else SHA256
        if not pattern.fullmatch(value):
            self.issue("INVALID_HASH_FORMAT", path, "Hash metadata has an unsupported format; no hash was verified.")


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def no_constant(value: str) -> None:
    raise InputError("NON_FINITE_NUMBER")


def inspect_tree(value: Any, limits: Limits) -> None:
    stack = [(value, 1)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > limits.max_nodes:
            raise InputError("NODE_LIMIT_EXCEEDED")
        if depth > limits.max_depth:
            raise InputError("DEPTH_LIMIT_EXCEEDED")
        if type(current) is float and not math.isfinite(current):
            raise InputError("NON_FINITE_NUMBER")
        if type(current) is str:
            try:
                current.encode("utf-8", "strict")
            except UnicodeEncodeError:
                raise InputError("INVALID_UNICODE") from None
        if type(current) is dict:
            for key, item in current.items():
                try:
                    key.encode("utf-8", "strict")
                except UnicodeEncodeError:
                    raise InputError("INVALID_UNICODE") from None
                stack.append((item, depth + 1))
        elif type(current) is list:
            stack.extend((item, depth + 1) for item in current)


def parse_time(value: Any, path: str, check: Check, *, required: bool = False) -> datetime | None:
    if value is None and not required:
        return None
    if type(value) is not str or not value.strip():
        return None  # Structural field validation reports this separately.
    try:
        if "T" not in value and " " not in value:
            raise ValueError()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        check.issue("TIMESTAMP_NOT_INTERPRETED", path, "Timestamp was retained without interpretation or normalization.", "limitation")
        return None
    if parsed.tzinfo is None:
        check.issue("TIMEZONE_UNSPECIFIED", path, "Timestamp has no offset; no timezone or UTC value was inferred.", "limitation")
    return parsed


def compare_times(start: Any, end: Any, check: Check) -> None:
    a = parse_time(start, "/started_at", check, required=True)
    b = parse_time(end, "/completed_at", check, required=True)
    if a is not None and b is not None:
        # Two naive source times are not assumed to share an offset or clock.
        if a.tzinfo is not None and b.tzinfo is not None and b < a:
            check.issue("TIME_ORDER_CONFLICT", "/completed_at", "Completion precedes start for explicitly offset timestamps.")


def validate_result(data: Any, expected: dict[str, str], limits: Limits, check: Check) -> dict[str, Any]:
    info: dict[str, Any] = {"counts": {}, "finding_references": [], "warning_pointers": [], "limitation_pointers": []}
    if type(data) is not dict:
        check.issue("INVALID_ROOT", "", "Expected an extracted AnalysisResult object.")
        return info
    if "jsonrpc" in data or "content" in data or "structuredContent" in data:
        check.issue("UNSUPPORTED_WRAPPER", "", "Provide the extracted result JSON, not an MCP or JSON-RPC wrapper.")
        return info
    if "schema_version" in data or "forenzx_version" in data:
        check.issue("UNSUPPORTED_SCHEMA", "", "Unrecognized version-bearing payload; this legacy profile has no such upstream fields.")
        return info
    for key in ("job_id", "case_id", "evidence_id"):
        if key in data and data[key] != expected[key]:
            check.issue("IDENTITY_MISMATCH", f"/{key}", "Result identity does not match the independently supplied expected identity.")
    if "message" in data and "execution_record" not in data:
        check.issue("RESULT_UNAVAILABLE", "", "The source returned a status/message response rather than a completed result.")
        return info
    check.object(data, ROOT_FIELDS, "")
    for key in ("job_id", "case_id", "evidence_id", "pack_id", "pack_version", "started_at", "completed_at"):
        if key in data:
            check.string(data[key], f"/{key}", nonempty=True)
    check.number(data.get("duration_seconds"), "/duration_seconds", 0)
    state_known = check.enum(data.get("status"), STATES, "/status")
    check.enum(data.get("summary_classification"), CLASSIFICATIONS, "/summary_classification")
    if state_known and data["status"] != "COMPLETED":
        check.issue("ANALYSIS_NOT_COMPLETED", "/status", "A findings brief requires a completed source analysis.")
    if state_known and data["status"] in {"FAILED", "SECURITY_BLOCKED"} and data.get("summary_classification") != "ERROR":
        check.issue("INCONSISTENT_STATE", "/summary_classification", "Failed or security-blocked source must use the ERROR classification.")
    if data.get("summary_classification") == "NO_KNOWN_IOC":
        check.issue("NEGATIVE_IOC_SCOPE", "/summary_classification", "No known IOC match is limited to the source examination and indicators; it does not establish a safe device.", "limitation")
    check.object(data.get("input_integrity"), None, "/input_integrity")
    compare_times(data.get("started_at"), data.get("completed_at"), check)
    for section in SECTIONS:
        if section in data and check.array(data[section], f"/{section}"):
            info["counts"][section] = len(data[section])
    if sum(info["counts"].values()) > limits.max_records:
        check.issue("RECORD_LIMIT_EXCEEDED", "", "Aggregate received report-section items exceed the configured engineering limit.")
        return info
    for section, output in (("warnings", "warning_pointers"), ("limitations", "limitation_pointers")):
        if type(data.get(section)) is list:
            for index, value in enumerate(data[section]):
                pointer = f"/{section}/{index}"
                check.string(value, pointer)
                info[output].append(pointer)
    findings = data.get("findings")
    if type(findings) is list:
        seen: set[str] = set()
        for i, item in enumerate(findings):
            path = f"/findings/{i}"
            if not check.object(item, FINDING_FIELDS, path):
                continue
            for key in ("id", "ioc_type", "artifact_path", "description"):
                if key in item:
                    check.string(item[key], f"{path}/{key}", nonempty=key == "id")
            for key in ("ioc_name", "artifact_hash", "timestamp"):
                if key in item:
                    check.string(item[key], f"{path}/{key}", nullable=True)
            for key, choices in (("classification", CLASSIFICATIONS), ("confidence", CONFIDENCES), ("severity", SEVERITIES)):
                check.enum(item.get(key), choices, f"{path}/{key}")
            if item.get("is_ai_assisted") is not False:
                check.issue("INVALID_LITERAL", f"{path}/is_ai_assisted", "Source finding must declare the boolean false.")
            raw_ref = item.get("raw_evidence_ref")
            if raw_ref is not None:
                check.object(raw_ref, None, f"{path}/raw_evidence_ref")
            ref = {"finding_pointer": path, "artifact_path_pointer": None, "raw_evidence_ref_pointer": None}
            if type(item.get("artifact_path")) is str and item["artifact_path"].strip():
                ref["artifact_path_pointer"] = f"{path}/artifact_path"
            if type(raw_ref) is dict and raw_ref:
                ref["raw_evidence_ref_pointer"] = f"{path}/raw_evidence_ref"
            if ref["artifact_path_pointer"] is None and ref["raw_evidence_ref_pointer"] is None:
                check.issue("MISSING_ARTIFACT_REFERENCE", path, "No nonempty artifact path or raw reference was supplied; no reference was invented.", "limitation")
            info["finding_references"].append(ref)
            if type(item.get("id")) is str:
                if item["id"] in seen:
                    check.issue("DUPLICATE_FINDING_ID", f"{path}/id", "Finding IDs must be unique within the received result.")
                seen.add(item["id"])
            parse_time(item.get("timestamp"), f"{path}/timestamp", check)
        if data.get("summary_classification") == "NO_KNOWN_IOC" and any(
            type(item) is dict and type(item.get("classification")) is str
            and item["classification"] in {"HIT", "SUSPICIOUS", "ERROR"} for item in findings
        ):
            check.issue("SUMMARY_FINDING_CONFLICT", "/summary_classification", "Negative IOC summary conflicts with a positive, suspicious, or error finding.")
    if type(data.get("timeline")) is list:
        for i, item in enumerate(data["timeline"]):
            path = f"/timeline/{i}"
            if not check.object(item, TIMELINE_FIELDS, path):
                continue
            for key in ("timestamp", "event_type", "source_tool", "description"):
                if key in item:
                    check.string(item[key], f"{path}/{key}", nonempty=key == "timestamp")
            for key in ("original_timestamp", "timezone", "normalization_notes"):
                if key in item:
                    check.string(item[key], f"{path}/{key}", nullable=True)
            check.number(item.get("relevance_score"), f"{path}/relevance_score", 0, 1)
            parse_time(item.get("timestamp"), f"{path}/timestamp", check, required=True)
    if type(data.get("chain_of_custody")) is list:
        for i, item in enumerate(data["chain_of_custody"]):
            path = f"/chain_of_custody/{i}"
            if not check.object(item, CUSTODY_FIELDS, path):
                continue
            for key in ("timestamp", "action", "actor"):
                if key in item:
                    check.string(item[key], f"{path}/{key}", nonempty=True)
            for key in ("sha256_before", "sha256_after"):
                check.hash(item.get(key), f"{path}/{key}")
            check.object(item.get("details"), None, f"{path}/details")
            before, after = item.get("sha256_before"), item.get("sha256_after")
            if item.get("action") == "INTEGRITY_BREACH_DETECTED":
                check.issue("INTEGRITY_BREACH_RECORDED", path, "The source records an integrity-breach action; preserve it for analyst review.", "limitation")
            elif type(before) is str and type(after) is str and before.lower() != after.lower():
                check.issue("CUSTODY_HASH_CONFLICT", path, "Custody hash metadata differs without an explicit integrity-breach action.")
            parse_time(item.get("timestamp"), f"{path}/timestamp", check, required=True)
    record = data.get("execution_record")
    if check.object(record, EXECUTION_FIELDS, "/execution_record"):
        if record.get("record_version") != "2":
            check.issue("UNSUPPORTED_RECORD_VERSION", "/execution_record/record_version", "Only execution record version 2 is supported by this profile.")
        for key in ("case_id", "evidence_id", "pack_id", "pack_version", "ioc_bundle_version", "started_at", "completed_at"):
            if key in record:
                check.string(record[key], f"/execution_record/{key}", nonempty=True)
        for key in ("case_id", "evidence_id", "pack_id", "pack_version", "started_at", "completed_at"):
            if key in data and key in record and data[key] != record[key]:
                check.issue("EXECUTION_RECORD_MISMATCH", f"/execution_record/{key}", "Execution record metadata does not match the enclosing result.")
        check.hash(record.get("container_digest"), "/execution_record/container_digest", container=True)
        for key in ("input_root_sha256", "ioc_bundle_sha256"):
            check.hash(record.get(key), f"/execution_record/{key}")
        for key in ("manifest_canonical_sha256", "server_hmac_signature"):
            check.hash(record.get(key), f"/execution_record/{key}", empty=True)
        for key in ("signature_algorithm", "signing_key_id", "ed25519_signature"):
            if key in record:
                check.string(record[key], f"/execution_record/{key}")
        if type(record.get("exit_code")) is not int:
            check.issue("INVALID_TYPE", "/execution_record/exit_code", "Expected an integer; no string or boolean coercion is supported.")
        elif record["exit_code"] != 0:
            check.issue("NONZERO_EXECUTION_EXIT", "/execution_record/exit_code", "Source execution has a nonzero exit code; this reporting profile requires review before proceeding.")
        if check.array(record.get("tool_command"), "/execution_record/tool_command"):
            for i, arg in enumerate(record["tool_command"]):
                check.string(arg, f"/execution_record/tool_command/{i}")
    return info


def result_base(limits: Limits) -> dict[str, Any]:
    return {
        "validator_version": VERSION, "profile": PROFILE, "upstream_commit": UPSTREAM_COMMIT,
        "status": "REJECTED", "passed": False, "report_generation_allowed": False,
        "limits": {**limits.__dict__, "basis": "PROVISIONAL_ENGINEERING_LIMITS_NOT_LLM_CONTEXT"},
        "input": {"bytes_read": 0, "complete_byte_read": False, "sha256": None},
        "coverage": {"scope": "RECEIVED_JSON_ONLY", "upstream_total": "UNKNOWN", "transport_completeness": "NOT_VERIFIED", "model_context": "NOT_VERIFIED"},
        "verification": {"source_authenticity": "NOT_VERIFIED", "original_artifacts": "NOT_VERIFIED", "signatures": "NOT_VERIFIED"},
        "issues": [], "diagnostics_limited": False,
    }


def validate_bytes(raw: bytes, *, profile: str, expected_job_id: str, expected_case_id: str,
                   expected_evidence_id: str, limits: Limits | None = None) -> dict[str, Any]:
    limits = limits or Limits()
    result = result_base(limits)
    check = Check()
    expected = {"job_id": expected_job_id, "case_id": expected_case_id, "evidence_id": expected_evidence_id}
    if not limits.valid():
        check.issue("INVALID_LIMIT_CONFIGURATION", "", "Configured limits are outside supported engineering bounds.")
    if profile != PROFILE:
        check.issue("UNSUPPORTED_PROFILE", "", "An explicitly supported input profile is required.")
    if any(type(value) is not str or not value.strip() or len(value) > 128 for value in expected.values()):
        check.issue("INVALID_EXPECTED_IDENTITY", "", "Supply nonempty expected job, case and evidence IDs of at most 128 characters.")
    if check.has_errors:
        result["issues"] = check.issues
        return result
    result["input"]["bytes_read"] = len(raw)
    if len(raw) > limits.max_bytes:
        check.issue("BYTE_LIMIT_EXCEEDED", "", "Received bytes exceed the configured engineering limit; total input size and hash were not established.")
    else:
        result["input"].update({"complete_byte_read": True, "sha256": hashlib.sha256(raw).hexdigest()})
        try:
            data = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=no_duplicate_keys, parse_constant=no_constant)
            inspect_tree(data, limits)
            result["coverage"].update(validate_result(data, expected, limits, check))
        except UnicodeDecodeError:
            check.issue("INVALID_UTF8", "", "Input is not valid UTF-8.")
        except InputError as error:
            check.issue(error.code, "", "Input failed a deterministic JSON or resource-bound check.")
        except RecursionError:
            check.issue("DEPTH_LIMIT_EXCEEDED", "", "Input exceeds supported parser nesting.")
        except (json.JSONDecodeError, ValueError, OverflowError):
            check.issue("INVALID_JSON", "", "Input is not one complete supported JSON document.")
    result["issues"] = check.issues
    result["diagnostics_limited"] = check.limited
    result["passed"] = not check.has_errors
    result["status"] = "STRUCTURE_VALID" if result["passed"] else "REJECTED"
    return result


def read_bounded(source: BinaryIO, maximum: int) -> bytes:
    # Read one byte beyond the boundary to distinguish exact-limit from oversize.
    chunks: list[bytes] = []
    remaining = maximum + 1
    while remaining:
        chunk = source.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument("--input", default="-", help="Explicit local JSON file, or - for stdin.")
    parser.add_argument("--profile", required=True, help=f"Supported profile: {PROFILE}")
    parser.add_argument("--expected-job-id", required=True)
    parser.add_argument("--expected-case-id", required=True)
    parser.add_argument("--expected-evidence-id", required=True)
    parser.add_argument("--max-bytes", type=int, default=262_144)
    parser.add_argument("--max-records", type=int, default=1_000)
    parser.add_argument("--max-depth", type=int, default=32)
    parser.add_argument("--max-nodes", type=int, default=20_000)
    limits = Limits()
    try:
        args = parser.parse_args(argv)
        limits = Limits(args.max_bytes, args.max_records, args.max_depth, args.max_nodes)
        if not limits.valid():
            raise InputError("INVALID_LIMIT_CONFIGURATION")
        if args.profile != PROFILE:
            raise InputError("UNSUPPORTED_PROFILE")
        if any(not value.strip() or len(value) > 128 for value in (args.expected_job_id, args.expected_case_id, args.expected_evidence_id)):
            raise InputError("INVALID_EXPECTED_IDENTITY")
        if args.input == "-":
            raw = read_bounded(sys.stdin.buffer, limits.max_bytes)
        else:
            # A FIFO must not block before we can reject non-regular input.
            fd = os.open(args.input, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise InputError("INPUT_NOT_REGULAR_FILE")
                raw = read_bounded(stream, limits.max_bytes)
        result = validate_bytes(raw, profile=args.profile, expected_job_id=args.expected_job_id,
                                expected_case_id=args.expected_case_id, expected_evidence_id=args.expected_evidence_id,
                                limits=limits)
        code = 0 if result["passed"] else 2
    except (CLIError, InputError, OSError):
        error = sys.exc_info()[1]
        result = result_base(limits)
        result["issues"] = [{"severity": "error", "code": error.code if isinstance(error, InputError) else "INVALID_CLI" if isinstance(error, CLIError) else "INPUT_READ_ERROR", "path": "", "message": "Input or invocation could not be processed; no result was accepted."}]
        code = 2
    print(json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
