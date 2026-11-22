#!/usr/bin/env python3
"""Reproducible, synthetic HTTP/client probe against an unmodified ForenZX checkout.

Run with the isolated upstream environment's Python. This does not execute a
forensic analysis, validate signatures, or certify an LLM-generated report.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

BASELINE = "0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f"
PROTOCOL = "2026-07-28"
OWNER, ORGANIZATION = "fx007-owner", "fx007-org"
ROOT = Path(__file__).resolve().parents[2]
READ_TOOLS = ["forenzx_analysis_status", "forenzx_analysis_results"]


class ProbeTerminated(Exception):
    def __init__(self, signal_number: int):
        self.exit_code = 128 + signal_number
        super().__init__(f"Probe interrupted by signal {signal_number}.")


def install_signal_handlers() -> None:
    def interrupted(signal_number, _frame):
        raise ProbeTerminated(signal_number)

    signal.signal(signal.SIGTERM, interrupted)


def json_write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def redact(text: str, sensitive: list[str]) -> str:
    for value in sorted(sensitive, key=len, reverse=True):
        if value:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text)
    return text


def finish_process(process: subprocess.Popen, timeout: float = 8) -> None:
    """Only stop the process group created by this probe."""
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=3)


def verify_upstream(upstream: Path, expected_commit: str = BASELINE) -> dict:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(upstream), *args], text=True).strip()

    commit = git("rev-parse", "HEAD")
    if commit != expected_commit:
        raise ValueError(f"Expected upstream commit {expected_commit}; found {commit}.")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Upstream checkout must be clean, including untracked files.")
    paths = ["core/main.py", "core/server.py", "core/config.py", "core/jobs.py",
             "core/acl.py", "core/db.py", "core/models/forensic.py", "pyproject.toml", "poetry.lock"]
    return {"repository": "erikbabcan-commits/forenzx-mcp-hub", "commit": commit,
            "clean": True, "files_sha256": {p: digest((upstream / p).read_bytes()) for p in paths}}


class Recorder:
    """Observe the actual ASGI app without changing request or response messages."""

    def __init__(self, app, temporary: Path, issued_tokens: dict[str, str] | None = None,
                 tokens_lock: threading.Lock | None = None):
        self.app, self.temporary = app, temporary
        self.issued_tokens = issued_tokens if issued_tokens is not None else {}
        self.tokens_lock = tokens_lock if tokens_lock is not None else threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        request_body, response_body = bytearray(), bytearray()
        response_hash, response_status = hashlib.sha256(), None
        phase = (self.temporary / "phase.txt").read_text(encoding="utf-8").strip()

        async def observed_receive():
            message = await receive()
            if message["type"] == "http.request" and len(request_body) < 262144:
                request_body.extend(message.get("body", b"")[:262144 - len(request_body)])
            return message

        async def observed_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_hash.update(body)
                response_body.extend(body[:max(0, 65536 - len(response_body))])
            await send(message)

        try:
            await self.app(scope, observed_receive, observed_send)
        finally:
            def object_or_empty(raw):
                try:
                    value = json.loads(raw)
                    return value if isinstance(value, dict) else {}
                except (ValueError, UnicodeDecodeError):
                    return {}

            request, response = object_or_empty(request_body), object_or_empty(response_body)
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            error = response.get("error") if isinstance(response.get("error"), dict) else {}
            meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
            allowed_meta = {key: meta[key] for key in ["io.modelcontextprotocol/protocolVersion",
                            "io.modelcontextprotocol/clientInfo", "io.modelcontextprotocol/clientCapabilities"] if key in meta}
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            tool_result = unwrap(response)
            auth = headers.get(b"authorization") or headers.get("authorization")
            caller_credential_matched = False
            auth_role = None
            if auth and auth.startswith("Bearer "):
                bearer_token = auth[7:].strip()
                with self.tokens_lock:
                    for issued_t, issued_role in self.issued_tokens.items():
                        if hmac.compare_digest(bearer_token, issued_t):
                            caller_credential_matched = True
                            auth_role = issued_role
                            break
                if auth_role is None:
                    try:
                        import jwt as _jwt
                        unverified = _jwt.decode(bearer_token, options={"verify_signature": False})
                        roles = unverified.get("roles")
                        if isinstance(roles, list) and roles:
                            auth_role = str(roles[0])
                    except Exception:
                        pass
            event = {
                "phase": phase, "http_method": scope["method"], "path": scope["path"],
                "rpc_method": request.get("method"), "tool_name": params.get("name"),
                "auth_role": auth_role,
                "caller_credential_matched": caller_credential_matched,
                "protocol_header": headers.get(b"mcp-protocol-version"),
                "method_header": headers.get(b"mcp-method"), "name_header": headers.get(b"mcp-name"),
                "meta": allowed_meta, "http_status": response_status,
                "rpc_error_code": error.get("code"), "has_result": "result" in response,
                "tool_is_error": response.get("result", {}).get("isError") if isinstance(response.get("result"), dict) else None,
                "requested_job_id": arguments.get("job_id"),
                "returned_job_id": tool_result.get("job_id") if tool_result else None,
                "tool_result_sha256": digest(canonical(tool_result)) if tool_result is not None else None,
                "response_sha256": response_hash.hexdigest(),
            }
            # Only the synthetic job identifier is selected from tool arguments.
            # No authorization values, cookies, or other request arguments are stored.
            with (self.temporary / "traffic.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def serve(upstream: Path, temporary: Path, port: int) -> None:
    sys.path.insert(0, str(upstream))
    from core.jobs import job_manager
    from core.models.forensic import AnalysisResult
    from core.main import app
    import uvicorn

    payload = json.loads((ROOT / "product/fixtures/completed-hit.json").read_text(encoding="utf-8"))
    job_id, _, _ = job_manager.create_job_ex(
        case_id=payload["case_id"], evidence_id=payload["evidence_id"], pack_id=payload["pack_id"],
        owner_id=OWNER, organization_id=ORGANIZATION,
    )
    try:
        from core.acl import case_access_provider
        case_access_provider.register_case(payload["case_id"], OWNER, ORGANIZATION)
    except (ImportError, AttributeError):
        pass
    payload["job_id"] = job_id
    validated = AnalysisResult.model_validate(payload)
    job_manager.store_result(job_id, validated)
    json_write(temporary / "seeded-result.json", validated.model_dump(mode="json"))

    issued_tokens: dict[str, str] = {}
    tokens_lock = threading.Lock()

    def token_reader():
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    role, t = line.split(":", 1)
                    with tokens_lock:
                        issued_tokens[t] = role
                else:
                    with tokens_lock:
                        issued_tokens[line] = "unknown"
        except Exception:
            pass

    threading.Thread(target=token_reader, daemon=True).start()

    uvicorn.run(Recorder(app, temporary, issued_tokens=issued_tokens, tokens_lock=tokens_lock),
                host="127.0.0.1", port=port, access_log=False, log_level="warning")


def http_request(port: int, method: str, path: str, payload: dict | None = None,
                 headers: dict | None = None) -> tuple[int, dict, str]:
    # This endpoint is deliberately loopback-only; no remote URL is accepted.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = canonical(payload) if payload is not None else None
    request_headers = {"Accept": "application/json, text/event-stream", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        raw = response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("Unexpected response exceeds 1 MiB probe limit.")
        try:
            content = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            content = {"non_json_response": True}
        return response.status, content, digest(raw)
    finally:
        connection.close()


def unwrap(response: dict) -> dict | None:
    result = response.get("result")
    if not isinstance(result, dict) or result.get("isError") is not False:
        return None
    content = result.get("content")
    if not isinstance(content, list) or len(content) != 1 or content[0].get("type") != "text":
        return None
    try:
        value = json.loads(content[0]["text"])
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError, KeyError):
        return None


def evaluate_codex_events(
    calls: list[dict],
    job_id: str,
    expected_hashes: dict[str, str],
    expected_final: dict,
    final_response: dict | None,
    codex_meta: dict,
    expected_role: str = "analyst",
) -> dict:
    tool_verifications = {}
    for tool in READ_TOOLS:
        tool_events = [e for e in calls if e.get("tool_name") == tool]
        valid_events = [
            e for e in tool_events
            if e.get("http_status") == 200
            and e.get("rpc_error_code") is None
            and e.get("has_result") is True
            and e.get("tool_is_error") is False
            and e.get("requested_job_id") == job_id
            and e.get("returned_job_id") == job_id
            and e.get("tool_result_sha256") == expected_hashes.get(tool)
            and e.get("caller_credential_matched") is True
            and e.get("auth_role") == expected_role
        ]
        tool_verifications[tool] = {
            "verified_event_present": bool(valid_events),
            "total_calls": len(tool_events),
            "credential_bound": any(e.get("caller_credential_matched") is True for e in tool_events),
            "role_matched": any(e.get("auth_role") == expected_role for e in tool_events),
            "result_hash_matched": any(e.get("tool_result_sha256") == expected_hashes.get(tool) for e in tool_events),
        }

    successful = [tool for tool, v in tool_verifications.items() if v["verified_event_present"]]
    observed_roles = sorted(list({e["auth_role"] for e in calls if e.get("auth_role")}))
    unexpected_calls = [e.get("tool_name") for e in calls if e.get("tool_name") not in READ_TOOLS]
    final_match = (final_response == expected_final)

    server_accepted_reporter = (
        all(tool_verifications[t]["verified_event_present"] for t in READ_TOOLS)
        if expected_role == "reporter" else None
    )

    accepted = (
        codex_meta.get("exit_code") == 0
        and not codex_meta.get("timed_out")
        and all(tool_verifications[t]["verified_event_present"] for t in READ_TOOLS)
        and final_match
        and not unexpected_calls
        and (expected_role != "reporter" or server_accepted_reporter is True)
    )

    return {
        "credential_role": expected_role,
        "tool_verifications": tool_verifications,
        "server_observed_roles": observed_roles,
        "server_accepted_reporter": server_accepted_reporter,
        "server_observed_successful_tools": successful,
        "unexpected_tool_calls": unexpected_calls,
        "final_exact_match": final_match,
        "accepted": accepted,
    }


def run_codex(port: int, token: str, job_id: str, temporary: Path, output: Path,
              sensitive: list[str], timeout: int) -> dict:
    binary = shutil.which("codex")
    if not binary:
        return {"status": "UNAVAILABLE", "reason": "codex executable not found", "accepted": False}
    version = subprocess.check_output([binary, "--version"], text=True, timeout=10).strip()
    workspace = temporary / "codex-workspace"
    workspace.mkdir()
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {"job_id": {"type": "string"}, "state": {"type": "string"},
                       "classification": {"type": "string"}, "finding_count": {"type": "integer"},
                       "warnings": {"type": "array", "items": {"type": "string"}},
                       "limitations": {"type": "array", "items": {"type": "string"}}},
        "required": ["job_id", "state", "classification", "finding_count", "warnings", "limitations"],
    }
    json_write(temporary / "codex-output-schema.json", schema)
    config = (f'mcp_servers.fx007={{url="http://127.0.0.1:{port}/mcp",'
              'bearer_token_env_var="FX007_SYNTHETIC_BEARER",'
              'enabled_tools=["forenzx_analysis_status","forenzx_analysis_results"],'
              'required=true,startup_timeout_sec=20,tool_timeout_sec=20}')
    command = [binary, "exec", "--ignore-user-config", "--ephemeral", "--sandbox", "read-only",
               "--skip-git-repo-check", "--json", "--color", "never", "-C", str(workspace),
               "-c", config,
               "-c", 'mcp_servers.fx007.tools.forenzx_analysis_status.approval_mode="approve"',
               "-c", 'mcp_servers.fx007.tools.forenzx_analysis_results.approval_mode="approve"',
               "--output-schema", str(temporary / "codex-output-schema.json"),
               "--output-last-message", str(temporary / "codex-last.json"), "-"]
    prompt = (
        "Perform a synthetic integration test, using only the two available ForenZX MCP read tools. "
        f"Call forenzx_analysis_status for job_id {job_id}, then forenzx_analysis_results for that same ID. "
        "Do not use shell, web, files, other tools, or create/cancel analyses. The data is entirely fictional. "
        "Return JSON matching the schema: exact job_id, state from status, classification from "
        "summary_classification, finding_count, and the complete original warnings and limitations "
        "arrays verbatim. Do not infer a forensic conclusion or claim to have verified evidence. "
        "If either tool cannot be called, say so; never invent a successful response."
    )
    (output / "codex-prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    json_write(output / "codex-command.json", command)
    environment = dict(os.environ, FX007_SYNTHETIC_BEARER=token)
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=environment, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        finish_process(process)
        stdout, stderr = process.communicate(timeout=3)
    finally:
        # Also covers Ctrl+C and SIGTERM propagated through the parent handler.
        finish_process(process)
    (output / "codex-events.jsonl").write_text(redact(stdout, sensitive), encoding="utf-8")
    (output / "codex-stderr.txt").write_text(redact(stderr, sensitive), encoding="utf-8")
    last = temporary / "codex-last.json"
    final_text = redact(last.read_text(encoding="utf-8"), sensitive) if last.exists() else ""
    (output / "codex-final.txt").write_text(final_text, encoding="utf-8")
    try:
        final = json.loads(final_text)
    except ValueError:
        final = None
    return {"status": "TIMEOUT" if timed_out else ("COMPLETED" if process.returncode == 0 else "FAILED"), "client": version,
            "exit_code": process.returncode, "timed_out": timed_out, "final": final,
            "configuration": {"transport": "HTTP", "endpoint": f"http://127.0.0.1:{port}/mcp",
                              "bearer_token_env_var": "FX007_SYNTHETIC_BEARER", "enabled_tools": READ_TOOLS,
                              "required": True, "startup_timeout_sec": 20, "tool_timeout_sec": 20,
                              "ignore_user_config": True, "ephemeral": True, "sandbox": "read-only",
                              "per_tool_approval_mode": {name: "approve" for name in READ_TOOLS}}}


async def legacy_sdk_probe(port: int, token: str) -> dict:
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        return {"status": "UNAVAILABLE", "reason": "Python mcp SDK is not installed in this environment"}
    version = importlib.metadata.version("mcp")
    try:
        async with asyncio.timeout(25):
            async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp",
                                            headers={"Authorization": f"Bearer {token}"}) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    initialized = await session.initialize()
                    discovery = await session.list_tools()
        return {"status": "CONNECTED", "client": f"mcp-python {version}",
                "protocol": initialized.protocolVersion, "tools": [t.name for t in discovery.tools]}
    except Exception as exc:
        def leaves(error):
            children = getattr(error, "exceptions", None)
            return [item for child in children for item in leaves(child)] if children else [f"{type(error).__name__}: {error}"]
        return {"status": "INCOMPATIBLE_OR_FAILED", "client": f"mcp-python {version}",
                "error_type": type(exc).__name__, "errors": leaves(exc)}


def synthetic_reporter_claims(case_id: str, job_id: str, expires_at: int) -> dict:
    return {
        "sub": "synthetic-reporter",
        "roles": ["reporter"],
        "organization": ORGANIZATION,
        "report_case_ids": [case_id],
        "report_job_ids": [job_id],
        "exp": expires_at,
    }


def run(args) -> int:
    import jwt

    upstream = args.upstream.resolve(strict=True)
    provenance = verify_upstream(upstream, args.upstream_commit)
    output = args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("--output must be a new or empty directory; existing evidence is never overwritten.")
    output.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "product/fixtures/completed-hit.json"
    report = {"schema_version": 1, "task": "FX-007", "started_at": datetime.now(timezone.utc).isoformat(),
              "upstream": provenance, "python": sys.version.split()[0], "fixture_sha256": digest(fixture.read_bytes()),
              "harness_sha256": digest(Path(__file__).read_bytes()), "checks": [],
              "protocol": {"requested": PROTOCOL, "mode": "per-request HTTP; no legacy initialization required"},
              "not_tested": ["forensic analysis execution/Docker", "original artifact authenticity",
                             "hash or signature verification", "generated forensic report quality",
                             "report-only server authorization", "production deployment", "real case data"],
              "codex": {"status": "NOT_REQUESTED"}, "legacy_sdk": {"status": "NOT_REQUESTED"}}
    report["dependencies"] = {}
    for package in ["fastapi", "uvicorn", "pydantic", "pydantic-settings", "httpx", "pyjwt", "cryptography", "mcp"]:
        try:
            report["dependencies"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["dependencies"][package] = "NOT_INSTALLED"
    sensitive: list[str] = []
    server = None
    with tempfile.TemporaryDirectory(prefix="forenzx-fx007-") as temp_name:
        temporary = Path(temp_name)
        (temporary / "phase.txt").write_text("startup", encoding="utf-8")
        with socket.socket() as allocation:
            allocation.bind(("127.0.0.1", 0))
            port = allocation.getsockname()[1]
        secret, signing, admin, analyst = [secrets.token_urlsafe(48) for _ in range(4)]
        sensitive.extend([secret, signing, admin, analyst])
        claims = {"sub": OWNER, "roles": ["analyst"], "organization": ORGANIZATION, "exp": int(time.time()) + 600}
        token = jwt.encode(claims, secret, algorithm="HS256")
        expired = jwt.encode({**claims, "exp": int(time.time()) - 60}, secret, algorithm="HS256")
        other = jwt.encode({**claims, "sub": "fx007-other", "organization": "fx007-other-org"}, secret, algorithm="HS256")
        sensitive.extend([token, expired, other])
        environment = dict(os.environ, ENVIRONMENT="production", DATA_DIR=str(temporary / "data"),
                           DATABASE_PATH=str(temporary / "data/forenzx.db"), BACKUPS_DIR=str(temporary / "backups"),
                           PACKS_DIR=str(upstream / "packs"), VAULT_BASE_DIR=str(temporary / "vault"),
                           SCRATCH_BASE_DIR=str(temporary / "scratch"), THREAT_INTEL_DIR=str(temporary / "intel"),
                           MCP_AUTO_HEALTH_ENABLED="false", JWT_SECRET_KEY=secret, SERVER_HMAC_SIGNING_KEY=signing,
                           ADMIN_API_KEYS=json.dumps([admin]), API_KEYS=json.dumps([analyst]),
                           ALLOWED_ORIGINS="[]", PYTHONDONTWRITEBYTECODE="1")

        def phase(name: str) -> None:
            (temporary / "phase.txt").write_text(name, encoding="utf-8")

        def check(name: str, passed: bool, **details) -> None:
            report["checks"].append({"name": name, "passed": bool(passed), **details})

        sequence = 0

        def rpc(method: str, params: dict | None = None, *, auth=token, extra_headers=None, protocol=PROTOCOL):
            nonlocal sequence
            sequence += 1
            headers = {"MCP-Protocol-Version": protocol, "Mcp-Method": method}
            arguments = dict(params or {})
            arguments["_meta"] = {"io.modelcontextprotocol/protocolVersion": protocol,
                                  "io.modelcontextprotocol/clientInfo": {"name": "forenzx-fx007-probe", "version": "0.1.0"},
                                  "io.modelcontextprotocol/clientCapabilities": {}}
            if method == "tools/call":
                headers["Mcp-Name"] = arguments["name"]
            if auth is not None:
                headers["Authorization"] = f"Bearer {auth}"
            headers.update(extra_headers or {})
            return http_request(port, "POST", "/mcp", {"jsonrpc": "2.0", "id": sequence,
                                "method": method, "params": arguments}, headers)

        try:
            with (temporary / "server.log").open("w", encoding="utf-8") as log:
                server = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve",
                                           "--upstream", str(upstream), "--temporary", str(temporary), "--port", str(port)],
                                          cwd=upstream, env=environment, stdout=log, stderr=log, stdin=subprocess.PIPE,
                                          text=True, start_new_session=True)
            if server.stdin:
                server.stdin.write(f"analyst:{token}\n")
                server.stdin.flush()
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f"Upstream process exited during startup ({server.returncode}).")
                try:
                    status, health, _ = http_request(port, "GET", "/health/live")
                    if status == 200 and (temporary / "seeded-result.json").exists():
                        break
                except (OSError, http.client.HTTPException):
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("Upstream did not start within 30 seconds.")
                time.sleep(0.1)
            expected = json.loads((temporary / "seeded-result.json").read_text(encoding="utf-8"))
            job_id = expected["job_id"]
            report["synthetic_job_id"] = job_id
            json_write(output / "seeded-result.json", expected)
            reporter_claims = synthetic_reporter_claims(expected["case_id"], job_id, int(time.time()) + 600)
            reporter_token = jwt.encode(reporter_claims, secret, algorithm="HS256")
            sensitive.append(reporter_token)
            if server and server.stdin:
                server.stdin.write(f"reporter:{reporter_token}\n")
                server.stdin.flush()
            status, health, _ = http_request(port, "GET", "/health/ready")
            report["engine_readiness"] = {"http_status": status, **{k: health.get(k) for k in ["status", "packs_enabled", "pack_errors"]}}

            phase("http_probe")
            for name, credential, extras in [
                ("missing_auth_rejected", None, {}), ("invalid_jwt_rejected", "invalid-synthetic-token", {}),
                ("expired_jwt_rejected", expired, {}), ("dev_bypass_rejected_in_production", None, {"X-Dev-Bypass": "allowed"}),
            ]:
                status, response, _ = rpc("tools/list", auth=credential, extra_headers=extras)
                check(name, status == 401 and "result" not in response, http_status=status)
            status, response, _ = rpc("tools/list", auth=None, extra_headers={"X-API-Key": analyst})
            check("api_key_discovery", status == 200 and isinstance(response.get("result", {}).get("tools"), list), http_status=status)
            status, response, _ = rpc("tools/list")
            names = [t.get("name") for t in response.get("result", {}).get("tools", [])]
            check("jwt_tool_discovery", status == 200 and all(t in names for t in READ_TOOLS), tools=names)
            status, response, _ = rpc("tools/list", protocol="2025-11-25")
            check("unsupported_protocol_rejected", status == 400 and "result" not in response, http_status=status)
            report["protocol"]["unsupported_response"] = {"http_status": status, "response": response,
                "note": "Rejection alone does not establish the modern -32022 error and supported-version-list semantics."}
            status, response, _ = rpc("server/discover")
            report["server_discover_diagnostic"] = {"http_status": status, "response": response,
                "note": "Separate current-spec discovery diagnostic; direct requests pin the supported protocol explicitly."}
            status, response, _ = rpc("tools/call", {"name": READ_TOOLS[0], "arguments": {"job_id": job_id}})
            job_status = unwrap(response)
            check("completed_status", status == 200 and job_status is not None and job_status.get("job_id") == job_id
                  and job_status.get("state") == "COMPLETED" and job_status.get("case_id") == expected["case_id"]
                  and job_status.get("evidence_id") == expected["evidence_id"], http_status=status)
            status, response, response_hash = rpc("tools/call", {"name": READ_TOOLS[1], "arguments": {"job_id": job_id}})
            retrieved = unwrap(response)
            check("exact_result_roundtrip", status == 200 and retrieved == expected, response_sha256=response_hash,
                  canonical_result_sha256=digest(canonical(retrieved)))
            check("warnings_and_limitations_preserved", isinstance(retrieved, dict)
                  and retrieved.get("warnings") == expected["warnings"] and retrieved.get("limitations") == expected["limitations"])
            json_write(output / "retrieved-result.json", retrieved)
            for name, credential, requested_id, expected_error in [
                ("cross_organization_denied", other, job_id, -32603),
                ("missing_job_rejected", token, "fx007-deliberately-missing-job", -32602),
            ]:
                status, response, _ = rpc("tools/call", {"name": READ_TOOLS[1], "arguments": {"job_id": requested_id}}, auth=credential)
                check(name, status == 200 and response.get("error", {}).get("code") == expected_error and "result" not in response,
                      http_status=status, rpc_error_code=response.get("error", {}).get("code"))

            validator = subprocess.run([sys.executable, str(ROOT / "product/validate_input.py"), "--input", str(output / "retrieved-result.json"),
                                        "--profile", "forenzx-analysis-result-0e4c7fae", "--expected-job-id", job_id,
                                        "--expected-case-id", expected["case_id"], "--expected-evidence-id", expected["evidence_id"]],
                                       capture_output=True, text=True, timeout=20)
            (output / "input-validation.json").write_text(validator.stdout, encoding="utf-8")
            check("retrieved_input_passes_structural_validator", validator.returncode == 0,
                  note="Explicit post-retrieval check; not a client-side pre-LLM enforcement mechanism.")
            if args.with_legacy_sdk:
                phase("legacy_sdk")
                report["legacy_sdk"] = asyncio.run(legacy_sdk_probe(port, token))
            if args.with_codex:
                phase("codex")
                codex_token = reporter_token if args.codex_role == "reporter" else token
                codex_meta = run_codex(port, codex_token, job_id, temporary, output, sensitive, args.codex_timeout)
                traffic = [json.loads(line) for line in (temporary / "traffic.jsonl").read_text(encoding="utf-8").splitlines()]
                calls = [e for e in traffic if e.get("phase") == "codex" and e.get("rpc_method") == "tools/call"]
                expected_hashes = {READ_TOOLS[0]: digest(canonical(job_status)), READ_TOOLS[1]: digest(canonical(expected))}
                expected_final = {"job_id": job_id, "state": "COMPLETED", "classification": expected["summary_classification"],
                                  "finding_count": len(expected["findings"]), "warnings": expected["warnings"], "limitations": expected["limitations"]}
                evaluation = evaluate_codex_events(
                    calls=calls,
                    job_id=job_id,
                    expected_hashes=expected_hashes,
                    expected_final=expected_final,
                    final_response=codex_meta.get("final"),
                    codex_meta=codex_meta,
                    expected_role=args.codex_role,
                )
                codex = {**codex_meta, **evaluation}
                report["codex"] = codex
        except (KeyboardInterrupt, ProbeTerminated) as exc:
            report["run_error"] = {"type": type(exc).__name__, "message": "Probe interrupted; owned processes stopped."}
            report["interrupted_exit_code"] = 130 if isinstance(exc, KeyboardInterrupt) else exc.exit_code
        except Exception as exc:
            report["run_error"] = {"type": type(exc).__name__, "message": redact(str(exc), sensitive)}
        finally:
            if server is not None:
                if server.stdin:
                    try:
                        server.stdin.close()
                    except Exception:
                        pass
                finish_process(server)
            for temporary_name, output_name in [("traffic.jsonl", "http-traffic.jsonl"), ("server.log", "server-log.txt")]:
                source = temporary / temporary_name
                if source.exists():
                    (output / output_name).write_text(redact(source.read_text(encoding="utf-8"), sensitive), encoding="utf-8")
    report["upstream_clean_after"] = verify_upstream(upstream, args.upstream_commit)["clean"]
    report["http_acceptance"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"]) and "run_error" not in report
    report["requested_acceptance"] = report["http_acceptance"] and (not args.with_codex or report["codex"].get("accepted", False))
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["artifacts_sha256"] = {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
    report = json.loads(redact(json.dumps(report, ensure_ascii=False), sensitive))
    json_write(output / "report.json", report)
    print(json.dumps({"report": str(output / "report.json"), "http_checks_passed": sum(c["passed"] for c in report["checks"]),
                      "http_checks_total": len(report["checks"]), "codex_status": report["codex"]["status"],
                      "requested_acceptance": report["requested_acceptance"]}))
    return report.get("interrupted_exit_code", 0 if report["requested_acceptance"] else 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--upstream-commit", default=BASELINE, help="Explicit reviewed upstream commit; historical baseline remains the default")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--with-codex", action="store_true")
    parser.add_argument("--codex-role", choices=["analyst", "reporter"], default="analyst",
                        help="Synthetic role token provided to Codex (default: analyst, historical FX-007 behavior)")
    parser.add_argument("--with-legacy-sdk", action="store_true")
    parser.add_argument("--codex-timeout", type=int, default=120)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--temporary", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.upstream, args.temporary, args.port)
        return 0
    install_signal_handlers()
    if args.output is None:
        parser.error("--output is required")
    if not 20 <= args.codex_timeout <= 300:
        parser.error("--codex-timeout must be between 20 and 300 seconds")
    try:
        return run(args)
    except Exception as exc:
        print(f"FX-007 could not start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
