"""Exercise a reference adapter with synthetic data and three private loopback receivers."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, replace
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
from validate_input import PROFILE, validate_bytes

FIXTURE = ROOT / "product/fixtures/completed-hit.json"
READ_RESULT = "forenzx_analysis_results"


def pack(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


@dataclass(frozen=True)
class Profile:
    provider: str
    model: str
    port: int
    retention: str
    training: str


@contextmanager
def endpoint(handle):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.reply(200 if self.path == "/ready" else 404, b"")

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            if size > 327680 or size < 0:
                self.reply(413, b"")
                return
            self.reply(*handle(self.path, self.rfile.read(size)))

        def reply(self, status, data):
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.025})
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join()


def exchange(port, path, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET" if body is None else "POST", path, body,
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def tool_reply(payload, error=False):
    return {"jsonrpc": "2.0", "id": 1, "result": {
        "isError": error, "content": [{"type": "text", "text": payload}]}}


def reference_result(selected, approved, read_fixture):
    if selected != approved:
        return tool_reply("UNAPPROVED_PROFILE", True)
    raw = read_fixture()
    checked = validate_bytes(raw, profile=PROFILE, expected_job_id="demo-job-hit",
                             expected_case_id="demo-case", expected_evidence_id="demo-evidence")
    if not checked["passed"]:
        return tool_reply("INVALID_RESULT", True)
    return tool_reply(raw.decode("utf-8"))


class Receiver:
    def __init__(self, name, marker, expected, events, status=200):
        self.name, self.marker, self.expected = name, marker, expected
        self.events, self.status = events, status
        self.posts = self.nonempty = self.marked = self.exact = 0

    def handle(self, path, body):
        if path == "/calibration":
            return 204, b""
        self.posts += 1
        self.nonempty += bool(body)
        self.marked += self.marker in body
        self.exact += body == self.expected
        self.events.append(self.name)
        return (self.status if path == "/model" else 404), b""

    def counts(self):
        return {"post_requests": self.posts, "nonempty_bodies": self.nonempty,
                "with_marker": self.marked, "exact_result": self.exact}


def scenario(name):
    marker = ("FX009-" + secrets.token_hex(16)).encode()
    data = json.loads(FIXTURE.read_bytes())
    data["warnings"].append(marker.decode())
    data["limitations"].append("SYNTHETIC last limitation")
    valid = pack(data)
    raw = valid
    if name == "incomplete":
        raw = valid[:-1]
    elif name == "wrong_identity":
        raw = pack({**data, "case_id": "other-synthetic-case"})

    events = []
    primary = Receiver("primary", marker, valid, events, 503 if name == "primary_unavailable" else 200)
    fallback = Receiver("fallback", marker, valid, events)
    with endpoint(primary.handle) as first, endpoint(fallback.handle) as second:
        for port in (first, second):
            if exchange(port, "/ready")[0] != 200 or exchange(port, "/calibration", b"ready")[0] != 204:
                raise RuntimeError("receiver calibration failed")
        approved = Profile("synthetic", "fixture", first, "memory-only", "disabled")
        selected = {"unapproved_provider": replace(approved, provider="unknown"),
                    "changed_endpoint": replace(approved, port=second),
                    "changed_model": replace(approved, model="unknown"),
                    "missing_retention": replace(approved, retention="")}.get(name, approved)

        def read():
            events.append("read")
            return raw

        def mcp(path, body):
            request = json.loads(body)
            if (path != "/mcp" or request.get("method") != "tools/call" or
                    request.get("params") != {"name": READ_RESULT, "arguments": {"job_id": "demo-job-hit"}}):
                return 400, b""
            reply = reference_result(selected, approved, read)
            events.append("reply")
            return 200, pack(reply)

        with endpoint(mcp) as adapter:
            request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": READ_RESULT, "arguments": {"job_id": "demo-job-hit"}}}
            status, wire = exchange(adapter, "/mcp", pack(request))
            if status != 200:
                raise RuntimeError("fixture connector failed")
            reply = json.loads(wire)
            result = reply["result"]
            text = result["content"][0]["text"]
            if result["isError"]:
                reason = text
            else:
                code, _ = exchange(selected.port, "/model", text.encode())
                reason = "OK" if code == 200 else "PRIMARY_UNAVAILABLE"

    profile_denied = name in {"unapproved_provider", "changed_endpoint", "changed_model", "missing_retention"}
    invalid = name in {"incomplete", "wrong_identity"}
    delivered = not (profile_denied or invalid)
    expected_reason = ("UNAPPROVED_PROFILE" if profile_denied else "INVALID_RESULT" if invalid
                       else "PRIMARY_UNAVAILABLE" if name == "primary_unavailable" else "OK")
    expected_response = tool_reply(valid.decode() if delivered else expected_reason, not delivered)
    expected_events = (["reply"] if profile_denied else ["read", "reply"]) + (["primary"] if delivered else [])
    checks = {"client_received_exact_allowed_reply": reply == expected_response,
              "event_order": events == expected_events, "halt_reason": reason == expected_reason,
              "primary_counts": all(n == int(delivered) for n in primary.counts().values()),
              "fallback_counts": all(n == 0 for n in fallback.counts().values())}
    return {"scenario": name, "reason": reason if reason in {"OK","UNAPPROVED_PROFILE","INVALID_RESULT","PRIMARY_UNAVAILABLE"} else "OTHER",
            "source_reads": events.count("read"), "events": events, "client_contains_marker": marker in wire,
            "primary": primary.counts(), "fallback": fallback.counts(),
            "checks": checks, "verdict": "PASS" if all(checks.values()) else "FAIL"}


SCENARIOS = ("approved", "unapproved_provider", "changed_endpoint", "changed_model",
             "missing_retention", "incomplete", "wrong_identity", "primary_unavailable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new JSON report file (default: stdout)")
    args = parser.parse_args()
    rows = [scenario(name) for name in SCENARIOS]
    report = {"scope": "synthetic reference adapter and loopback client", "product_path": "NOT_VERIFIED",
              "report_generation_allowed": False, "provider_retention": "NOT_VERIFIED",
              "profile": {"provider": "synthetic", "model": "fixture", "targets": "two separate loopback ports",
                          "retention": "memory-only test receiver", "training": "disabled in test fixture"},
              "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "validator_sha256": hashlib.sha256((ROOT / "product/validate_input.py").read_bytes()).hexdigest(),
              "scenarios": rows}
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as file:
            file.write(output)
    else:
        sys.stdout.write(output)
    return int(any(row["verdict"] != "PASS" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
