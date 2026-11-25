"""Run the synthetic reporting path against local MCP and model receivers."""
from __future__ import annotations

import argparse
from dataclasses import replace
import http.client
import json
from pathlib import Path
import re
import sys

from provider_probe import PROFILE, READ_RESULT, Profile, pack, validate_bytes

MAX_REPLY = 512 * 1024


def port(value):
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("expected a TCP port between 1 and 65535")
    return number


def post(target, path, body, *, read_reply=False, token=None):
    connection = http.client.HTTPConnection("127.0.0.1", target, timeout=3)
    try:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        connection.request("POST", path, body, headers)
        with connection.getresponse() as response:
            return response.status, response.read(MAX_REPLY + 1) if read_reply else b""
    finally:
        connection.close()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def run(selected, approved, hub_port, *, job_id="demo-job-hit", token_file=None):
    if selected != approved:
        return "UNAPPROVED_PROFILE"
    token = None
    if token_file:
        try:
            with token_file.open("r", encoding="ascii") as stream:
                token = stream.read(16385).strip()
            if len(token) > 16384 or not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}", token):
                return "SOURCE_CREDENTIAL_INVALID"
        except (OSError, ValueError):
            return "SOURCE_CREDENTIAL_INVALID"
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": READ_RESULT, "arguments": {"job_id": job_id}}}
    try:
        status, wire = post(hub_port, "/mcp", pack(request), read_reply=True, token=token)
    except (OSError, http.client.HTTPException):
        return "SOURCE_UNAVAILABLE"
    if status in (401, 403):
        return "SOURCE_AUTH_DENIED"
    if status != 200 or len(wire) > MAX_REPLY:
        return "INVALID_RESULT"
    try:
        reply = json.loads(wire, object_pairs_hook=unique_object)
        if reply["jsonrpc"] != "2.0" or type(reply["id"]) is not int or reply["id"] != 1 or "error" in reply:
            return "INVALID_RESULT"
        result = reply["result"]
        content = result["content"]
        if result.get("isError", False) is not False or not isinstance(content, list) or len(content) != 1:
            return "INVALID_RESULT"
        if content[0]["type"] != "text":
            return "INVALID_RESULT"
        raw = content[0]["text"].encode("utf-8")
        checked = validate_bytes(raw, profile=PROFILE, expected_job_id=job_id,
                                 expected_case_id="demo-case", expected_evidence_id="demo-evidence")
        if not checked["passed"]:
            return "INVALID_RESULT"
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return "INVALID_RESULT"
    try:
        code, _ = post(approved.port, "/model", raw)
    except (OSError, http.client.HTTPException):
        return "PRIMARY_UNAVAILABLE"
    return "OK" if 200 <= code < 300 else "PRIMARY_UNAVAILABLE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub-port", type=port, required=True)
    parser.add_argument("--approved-model-port", type=port, required=True)
    parser.add_argument("--model-port", type=port)
    parser.add_argument("--provider", default="synthetic")
    parser.add_argument("--model", default="fixture")
    parser.add_argument("--retention", default="memory-only")
    parser.add_argument("--training", default="disabled")
    parser.add_argument("--job-id", default="demo-job-hit", help="synthetic job ID from the local Hub")
    parser.add_argument("--token-file", type=Path, help="private synthetic reporter bearer token file")
    args = parser.parse_args()
    approved = Profile("synthetic", "fixture", args.approved_model_port, "memory-only", "disabled")
    selected = replace(approved, provider=args.provider, model=args.model,
                       port=args.model_port or approved.port, retention=args.retention, training=args.training)
    reason = run(selected, approved, args.hub_port, job_id=args.job_id, token_file=args.token_file)
    print(reason, file=sys.stdout if reason == "OK" else sys.stderr)
    return 0 if reason == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
