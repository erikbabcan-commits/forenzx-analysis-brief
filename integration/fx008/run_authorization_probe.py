#!/usr/bin/env python3
"""Characterize pinned Hub authorization using synthetic, in-process ASGI calls.

This is a baseline experiment, not a passing report-only authorization gate.
No auth/ACL function is patched. The only sentinel replaces pack lookup AFTER
case authorization and BEFORE job creation, adapters, workers or downloads.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import copy
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import patch

BASELINE = "0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f"
PROTOCOL = "2026-07-28"
ROOT = Path(__file__).resolve().parents[2]
SENTINEL = "FX008_AFTER_CASE_AUTHORIZATION_BEFORE_EXECUTION"
SOURCE_PATHS = ["core/acl.py", "core/main.py", "core/server.py", "core/jobs.py",
                "core/config.py", "core/db.py", "core/pack_registry.py",
                "core/models/forensic.py", "workers/pool.py", "poetry.lock"]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def verify_source(upstream: Path) -> dict:
    commit = git(upstream, "rev-parse", "HEAD")
    if commit != BASELINE:
        raise ValueError("Unexpected upstream commit; update reviewed expectations before testing.")
    if git(upstream, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("The upstream checkout must be completely clean.")
    return {"commit": commit, "clean": True,
            "files_sha256": {p: sha((upstream / p).read_bytes()) for p in SOURCE_PATHS}}


def unwrap(body: dict) -> dict | None:
    value = body.get("result")
    if not isinstance(value, dict) or value.get("isError") is not False:
        return None
    content = value.get("content")
    if not isinstance(content, list) or len(content) != 1 or content[0].get("type") != "text":
        return None
    decoded = json.loads(content[0]["text"])
    return decoded if isinstance(decoded, dict) else None


async def exercise(upstream: Path, temporary: Path, report: dict) -> None:
    # Imports happen ONLY after environment and cwd isolation in main().
    import httpx
    import jwt
    sys.path.insert(0, str(upstream))
    from core.acl import case_access_provider
    from core.config import config
    from core.db import db
    from core.jobs import job_manager
    from core.main import AuthConfig, app, worker_pool
    from core.models.forensic import AnalysisResult
    from core.pack_registry import pack_registry
    from core.server import MCPError

    assert config.environment == "production"
    assert not config.mcp_auto_health_enabled
    assert not app.dependency_overrides
    assert not pack_registry.list_packs()
    for name in ["data_dir", "database_path", "backups_dir", "vault_base_dir",
                 "scratch_base_dir", "threat_intel_dir", "packs_dir"]:
        assert Path(getattr(config, name)).resolve().is_relative_to(temporary)

    fixture_path = ROOT / "product/fixtures/completed-hit.json"
    original_fixture = json.loads(fixture_path.read_bytes())
    assert original_fixture["input_integrity"]["synthetic"] is True
    assert "SYNTHETIC" in original_fixture["warnings"][0]
    report["fixture"] = {"path": "product/fixtures/completed-hit.json",
                         "sha256": sha(fixture_path.read_bytes()), "synthetic": True}
    report["runtime"] = {"python": platform.python_version(), "implementation": platform.python_implementation(),
                         "dependencies": {p: importlib.metadata.version(p) for p in
                                          ["httpx", "fastapi", "starlette", "pydantic", "pydantic-settings", "PyJWT", "cryptography"]},
                         "transport": "httpx.ASGITransport in-process; no network listener; no lifespan",
                         "environment": config.environment, "database_schema_version": db.schema_version()}

    secret = config.jwt_secret_key
    key_a, key_b = config.api_keys
    api_a_user = AuthConfig.api_key_user(key_a)
    assert api_a_user is not None
    assert "admin" not in api_a_user.roles
    def bearer(user: str, org: str, roles: list[str], *, expired: bool = False) -> dict:
        return {"Authorization": "Bearer " + jwt.encode(
            {"sub": user, "organization": org, "roles": roles,
             "exp": int(time.time()) + (-60 if expired else 600)}, secret, algorithm="HS256")}

    credentials = {
        "owner": bearer("fx008-owner", "fx008-org-a", ["analyst"]),
        "same_org": bearer("fx008-colleague", "fx008-org-a", ["analyst"]),
        "cross_org": bearer("fx008-outsider", "fx008-org-b", ["analyst"]),
        "owner_other_org": bearer("fx008-owner", "fx008-org-b", ["analyst"]),
        "case_grant": bearer("fx008-case-grantee", "fx008-org-c", ["analyst"]),
        "empty_roles": bearer("fx008-no-role", "fx008-org-a", []),
        "reporter_label": bearer("fx008-report-reader", "fx008-org-a", ["reporter"]),
        "api_owner": {"X-API-Key": key_a},
        "api_other_key": {"Authorization": "APIKey " + key_b},
    }
    report["principal_definitions"] = {
        "owner": "Job owner, org-a, analyst JWT",
        "same_org": "Different user, org-a, analyst JWT; no individual case grant",
        "cross_org": "Different user, org-b, analyst JWT; no matching case access",
        "owner_other_org": "Same owner user_id with org-b, analyst JWT",
        "case_grant": "Different job owner and org; registered case belongs to org-c",
        "empty_roles": "Different user, org-a, signed JWT with roles=[]",
        "reporter_label": "Different user, org-a, signed JWT with roles=['reporter']; this role is not implemented by Hub",
        "api_owner": "Regular API key A; actual derived user_id owns synthetic default_org job",
        "api_other_key": "Different regular API key B; default_org shared by Hub auth mapping",
    }

    def make_job(label: str, actor: str, completed: bool) -> tuple[str, dict | None]:
        owner = api_a_user.user_id if actor.startswith("api_") else "fx008-owner"
        org = "default_org" if actor.startswith("api_") else "fx008-org-a"
        case_id = "FX008-" + label
        case_org = "fx008-org-c" if actor == "case_grant" else org
        case_access_provider.register_case(case_id, "fx008-case-owner", case_org)
        job_id, _, created = job_manager.create_job_ex(
            case_id=case_id, evidence_id="FX008-SYNTHETIC-EVIDENCE", pack_id="synthetic-triage",
            owner_id=owner, organization_id=org)
        assert created
        if not completed:
            return job_id, None
        payload = copy.deepcopy(original_fixture)
        payload.update(job_id=job_id, case_id=case_id, evidence_id="FX008-SYNTHETIC-EVIDENCE")
        payload["execution_record"].update(case_id=case_id, evidence_id=payload["evidence_id"])
        model = AnalysisResult.model_validate(payload)
        job_manager.store_result(job_id, model)
        return job_id, model.model_dump(mode="json")

    def snapshot() -> str:
        return sha(canonical({"jobs": db.fetchall("SELECT * FROM jobs ORDER BY job_id"),
                              "results": db.fetchall("SELECT * FROM job_results ORDER BY job_id")}))

    sequence = 0
    checks = report["checks"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                base_url="http://fx008.invalid", trust_env=False) as client:
        async def rpc(method: str, params: dict, headers: dict, route: str = "/mcp"):
            nonlocal sequence
            sequence += 1
            params = {**params, "_meta": {"io.modelcontextprotocol/protocolVersion": PROTOCOL,
                       "io.modelcontextprotocol/clientInfo": {"name": "fx008-authorization-probe", "version": "1"},
                       "io.modelcontextprotocol/clientCapabilities": {}}}
            request_headers = {"MCP-Protocol-Version": PROTOCOL, "Mcp-Method": method, **headers}
            if method == "tools/call":
                request_headers["Mcp-Name"] = params["name"]
            response = await client.post(route, json={"jsonrpc": "2.0", "id": sequence,
                                                      "method": method, "params": params}, headers=request_headers)
            return response, response.json()

        def record(identifier: str, actor: str, route: str, tool: str, expected: str,
                   response, body: dict, observed: str, passed: bool, policy: str, **details):
            checks.append({"id": identifier, "principal": actor, "route": route, "tool": tool,
                           "expected_baseline": expected, "observation": observed,
                           "baseline_match": bool(passed), "reporting_policy_status": policy,
                           "http_status": response.status_code,
                           "rpc_error_code": body.get("error", {}).get("code"),
                           "response_sha256": sha(response.content), **details})

        auth_controls = [
            ("no_auth", {}), ("invalid_api_key", {"X-API-Key": "fx008-unconfigured-invalid-key"}),
            ("development_bypass", {"X-Dev-Bypass": "allowed"}),
            ("expired_jwt", bearer("fx008-owner", "fx008-org-a", ["analyst"], expired=True)),
            ("api_key_as_bearer", {"Authorization": "Bearer " + key_a}),
            ("invalid_key_over_valid_jwt", {**credentials["owner"], "X-API-Key": "fx008-unconfigured-invalid-key"}),
        ]
        for label, headers in auth_controls:
            before = snapshot()
            response, body = await rpc("tools/list", {}, headers)
            passed = response.status_code == 401 and "result" not in body and snapshot() == before
            record("auth_" + label, label, "/mcp", "tools/list", "HTTP_401", response, body,
                   "HTTP_401" if response.status_code == 401 else "UNEXPECTED", passed,
                   "PASS" if passed else "FAIL", database_unchanged=snapshot() == before)

        for actor in ["owner", "empty_roles", "reporter_label", "api_owner", "api_other_key"]:
            response, body = await rpc("tools/list", {}, credentials[actor])
            names = [t["name"] for t in body.get("result", {}).get("tools", [])]
            writes_visible = all(t in names for t in ["forenzx_analysis_start", "forenzx_analysis_cancel"])
            record("discovery_" + actor, actor, "/mcp", "tools/list", "ALL_TOOLS_VISIBLE",
                   response, body, "ALL_TOOLS_VISIBLE" if writes_visible else "OTHER", writes_visible,
                   "NOT_TESTED", tool_names=names,
                   policy_note="Discovery visibility alone neither grants nor denies invocation permission.")

        reads = {}
        for actor in credentials:
            job_id, payload = make_job("READ-" + actor.replace("_", "-"), actor, True)
            reads[actor] = (job_id, payload)
            for suffix in ["status", "results"]:
                name = "forenzx_analysis_" + suffix
                before = snapshot()
                response, body = await rpc("tools/call", {"name": name, "arguments": {"job_id": job_id}}, credentials[actor])
                value = unwrap(body)
                denied = response.status_code == 200 and body.get("error", {}).get("code") == -32603 and "result" not in body
                allowed = response.status_code == 200 and value is not None
                identity_matches = bool(value and all(value.get(k) == payload[k] for k in ["job_id", "case_id", "evidence_id"]))
                payload_matches = value == payload if suffix == "results" else identity_matches
                expected_allowed = actor != "cross_org"
                baseline_match = (allowed and payload_matches if expected_allowed else denied) and snapshot() == before
                policy = "PASS" if actor in {"owner", "api_owner", "cross_org"} else "REVIEW_REQUIRED"
                record("read_" + actor + "_" + suffix, actor, "/mcp", name,
                       "ALLOW" if expected_allowed else "DENY", response, body, "ALLOW" if allowed else "DENY",
                       baseline_match, policy if baseline_match else "FAIL", identity_matches=identity_matches,
                       exact_result_matches=payload_matches if suffix == "results" else None,
                       database_unchanged=snapshot() == before)

        # Both deprecated tool aliases and the legacy HTTP route retain the same ACL.
        for actor, name in [("owner", "mcp_get_results"), ("cross_org", "mcp_get_results"),
                            ("owner", "mcp_get_job_status"), ("cross_org", "mcp_get_job_status")]:
            job_id, payload = reads[actor]
            before = snapshot()
            response, body = await rpc("tools/call", {"name": name, "arguments": {"job_id": job_id}},
                                       credentials[actor], "/mcp/jsonrpc")
            value = unwrap(body)
            allowed = value is not None
            correct = (value == payload if name == "mcp_get_results" else
                       bool(value and all(value.get(k) == payload[k] for k in ["job_id", "case_id", "evidence_id"])))
            passed = response.status_code == 200 and snapshot() == before and (
                correct if actor == "owner" else body.get("error", {}).get("code") == -32603 and "result" not in body)
            record("legacy_" + actor + "_" + name, actor, "/mcp/jsonrpc", name,
                   "ALLOW" if actor == "owner" else "DENY", response, body,
                   "ALLOW" if allowed else "DENY", passed, "PASS" if passed else "FAIL",
                   database_unchanged=snapshot() == before)

        for actor, route in [(a, "/mcp") for a in credentials] + [
            ("cross_org", "/mcp/jsonrpc"), ("reporter_label", "/mcp/jsonrpc")]:
            label = "CANCEL-" + actor.replace("_", "-") + ("-LEGACY" if route.endswith("jsonrpc") else "")
            job_id, _ = make_job(label, actor, False)
            before = snapshot()
            response, body = await rpc("tools/call", {"name": "forenzx_analysis_cancel", "arguments": {"job_id": job_id}}, credentials[actor], route)
            value = unwrap(body)
            state = job_manager.get_status(job_id).state.value
            cancelled = value == {"job_id": job_id, "cancelled": True} and state == "CANCELLED"
            denied = body.get("error", {}).get("code") == -32603 and "result" not in body and state == "QUEUED" and snapshot() == before
            expected_allowed = actor != "cross_org"
            passed = response.status_code == 200 and (cancelled if expected_allowed else denied)
            record(label.lower(), actor, route, "forenzx_analysis_cancel",
                   "CANCELLED" if expected_allowed else "DENY_UNCHANGED", response, body,
                   "CANCELLED" if cancelled else "DENY_UNCHANGED" if denied else "UNEXPECTED", passed,
                   "FAIL" if cancelled else "PASS" if denied else "FAIL", state_before="QUEUED", state_after=state,
                   database_unchanged=snapshot() == before,
                   policy_note="A reporting-flow credential must reject cancellation before state mutation; existing analyst semantics may intentionally allow it.")

        # Only this downstream pack lookup is replaced; the real case ACL executes first.
        sentinel_calls = []
        def stop_before_execution(pack_id):
            sentinel_calls.append(pack_id)
            raise MCPError(SENTINEL)

        for actor, route, name in [("owner", "/mcp", "forenzx_analysis_start"),
                                  ("empty_roles", "/mcp", "forenzx_analysis_start"),
                                  ("reporter_label", "/mcp", "forenzx_analysis_start"),
                                  ("cross_org", "/mcp", "forenzx_analysis_start"),
                                  ("reporter_label", "/mcp/jsonrpc", "mcp_start_analysis"),
                                  ("cross_org", "/mcp/jsonrpc", "mcp_start_analysis")]:
            case_id = "FX008-START-ORG-A"
            case_access_provider.register_case(case_id, "fx008-owner", "fx008-org-a")
            before = snapshot()
            count_before = len(sentinel_calls)
            with patch.object(pack_registry, "get_pack", side_effect=stop_before_execution):
                response, body = await rpc("tools/call", {"name": name, "arguments": {
                    "case_id": case_id, "evidence_id": "FX008-SYNTHETIC-EVIDENCE",
                    "pack_id": "synthetic-sentinel", "input_type": "file_generic"}}, credentials[actor], route)
            reached = len(sentinel_calls) == count_before + 1
            error = body.get("error", {})
            expected_reached = actor != "cross_org"
            expected_error = error.get("code") == (-32602 if expected_reached else -32603)
            expected_message = error.get("message") == SENTINEL if expected_reached else not reached
            passed = response.status_code == 200 and reached == expected_reached and expected_error and expected_message and snapshot() == before and not job_manager._tasks
            record("start_" + actor + ("_legacy" if route.endswith("jsonrpc") else ""), actor, route, name,
                   "POST_ACL_SENTINEL" if expected_reached else "DENY_BEFORE_SENTINEL", response, body,
                   "POST_ACL_SENTINEL" if reached else "DENY_BEFORE_SENTINEL", passed,
                   "FAIL" if reached else "PASS" if passed else "FAIL", sentinel_reached=reached,
                   database_unchanged=snapshot() == before, actual_analysis_started=False,
                   policy_note="Sentinel proves only passage through real case ACL; execution and later pack checks were deliberately not tested.")

        for actor in ["owner", "cross_org"]:
            job_id, payload = reads[actor]
            before = snapshot()
            response = await client.get("/api/v1/jobs/" + job_id + "/events", headers=credentials[actor])
            if actor == "owner":
                line = response.text.removeprefix("data: ").strip()
                value = json.loads(line)
                passed = response.status_code == 200 and all(value.get(k) == payload[k] for k in ["job_id", "case_id", "evidence_id"])
            else:
                passed = response.status_code == 403 and "data:" not in response.text
            checks.append({"id": "sse_" + actor, "principal": actor, "route": "/api/v1/jobs/{job_id}/events",
                           "expected_baseline": "ALLOW" if actor == "owner" else "HTTP_403_NO_STREAM",
                           "observation": "ALLOW" if response.status_code == 200 else "HTTP_403_NO_STREAM",
                           "baseline_match": bool(passed and snapshot() == before), "reporting_policy_status": "PASS" if passed else "FAIL",
                           "http_status": response.status_code, "response_sha256": sha(response.content),
                           "database_unchanged": snapshot() == before})

        response, body = await rpc("tools/call", {"name": "forenzx_analysis_results", "arguments": {"job_id": "FX008-MISSING-JOB"}}, credentials["owner"])
        missing = response.status_code == 200 and body.get("error", {}).get("code") == -32602 and "result" not in body
        record("missing_job", "owner", "/mcp", "forenzx_analysis_results", "NO_RESULT_-32602",
               response, body, "NO_RESULT_-32602" if missing else "UNEXPECTED", missing, "PASS" if missing else "FAIL")

    assert not job_manager._tasks
    assert worker_pool._client is None
    report["isolation_observations"] = {"task_handles_at_end": len(job_manager._tasks),
                                         "docker_client_initialized": worker_pool._client is not None,
                                         "auth_dependency_overrides": len(app.dependency_overrides),
                                         "sentinel_reached_count": len(sentinel_calls),
                                         "network_server_started": False,
                                         "model_invoked": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New JSON file; existing evidence is not overwritten")
    args = parser.parse_args()
    upstream, output = args.upstream.resolve(), args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new file.")
    source_before = verify_source(upstream)
    sys.dont_write_bytecode = True
    report = {"schema": "forenzx.fx008.authorization-observations/1", "started_at": datetime.now(timezone.utc).isoformat(),
              "upstream": source_before, "coordinator_base_commit": git(ROOT, "rev-parse", "HEAD"),
              "probe_sha256": sha(Path(__file__).read_bytes()), "checks": [],
              "report_generation_allowed": False,
              "sentinel": {"target": "core.pack_registry.pack_registry.get_pack", "scope": "start probes only",
                           "position": "after CaseAccessController.enforce; before manifest validation/job creation/worker", "changes_auth_or_acl": False},
              "not_tested": ["real or paid model", "AI client compatibility", "network/TLS transport", "ASGI lifespan",
                             "forensic engine/Docker/download", "production deployment", "evidence-level ACL",
                             "JWT issuer/audience policy", "strict case-membership policy", "admin semantics",
                             "restart persistence of case grants", "stdlib stdio runtime", "rendering", "signatures"]}
    original_env, original_cwd = dict(os.environ), Path.cwd()
    # Isolate all settings, including inherited aliases; no shell config or .env is loaded.
    settings = {"ENVIRONMENT", "DATA_DIR", "DATABASE_PATH", "BACKUPS_DIR", "PACKS_DIR", "VAULT_BASE_DIR",
                "SCRATCH_BASE_DIR", "THREAT_INTEL_DIR", "JWT_SECRET_KEY", "JWT_SECRET", "SERVER_HMAC_SIGNING_KEY",
                "HMAC_SECRET_KEY", "API_KEYS", "ADMIN_API_KEYS", "MCP_AUTO_HEALTH_ENABLED", "DASHBOARD_ENABLED", "ALLOWED_ORIGINS"}
    logs = io.StringIO()
    try:
        with tempfile.TemporaryDirectory(prefix="forenzx-fx008-") as tmp:
            temporary = Path(tmp).resolve()
            os.chmod(temporary, 0o700)
            for key in list(os.environ):
                if key.upper() in settings:
                    del os.environ[key]
            for name in ["data", "backups", "packs", "vault", "scratch", "intel"]:
                (temporary / name).mkdir()
            os.environ.update(ENVIRONMENT="production", DATA_DIR=str(temporary / "data"),
                              DATABASE_PATH=str(temporary / "data/forenzx.db"), BACKUPS_DIR=str(temporary / "backups"),
                              PACKS_DIR=str(temporary / "packs"), VAULT_BASE_DIR=str(temporary / "vault"),
                              SCRATCH_BASE_DIR=str(temporary / "scratch"), THREAT_INTEL_DIR=str(temporary / "intel"),
                              MCP_AUTO_HEALTH_ENABLED="false", DASHBOARD_ENABLED="false", ALLOWED_ORIGINS="[]",
                              JWT_SECRET_KEY=secrets.token_urlsafe(48), SERVER_HMAC_SIGNING_KEY=secrets.token_urlsafe(48),
                              ADMIN_API_KEYS=json.dumps([secrets.token_urlsafe(48)]),
                              API_KEYS=json.dumps([secrets.token_urlsafe(48), secrets.token_urlsafe(48)]))
            os.chdir(temporary)
            # Upstream logs are intentionally not persisted. Evidence contains only allowlisted fields.
            with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
                asyncio.run(exercise(upstream, temporary, report))
            os.chdir(original_cwd)
        report["temporary_data_removed"] = not temporary.exists()
    finally:
        os.chdir(original_cwd)
        os.environ.clear()
        os.environ.update(original_env)
        logs.close()
    source_after = verify_source(upstream)
    report["upstream_unchanged"] = source_after == source_before
    matched = sum(c["baseline_match"] for c in report["checks"])
    failures = [c["id"] for c in report["checks"] if not c["baseline_match"]]
    policy_failures = [c["id"] for c in report["checks"] if c["reporting_policy_status"] == "FAIL"]
    report["summary"] = {"checks": len(report["checks"]), "baseline_matches": matched,
                         "baseline_status": "PASS" if not failures and report["upstream_unchanged"] else "FAIL",
                         "baseline_mismatches": failures, "reporting_policy_gate": "FAIL" if policy_failures else "NOT_TESTED",
                         "reporting_policy_failures": policy_failures,
                         "meaning": "Matching source-predicted baseline is not release approval; report-only enforcement is absent."}
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(report["summary"], ensure_ascii=False))
    # 0 characterizes baseline successfully, including known failing product policy.
    return 0 if report["summary"]["baseline_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
