"""Optional FX-009 regression using the pinned Hub and a synthetic SQLite job."""
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from provider_probe import FIXTURE, endpoint

HUB_TREE = "8c9c9aa9846b3627f7008999f3170f041871df1d"
CLIENT = Path(__file__).with_name("report_client.py")

SEED = """
import json
import os
from pathlib import Path
from core.acl import case_access_provider
from core.jobs import job_manager
from core.models.forensic import AnalysisResult
from core.reporter_credentials import issue_reporter, write_private_token

root = Path(os.environ["FX009_TEST_ROOT"])
payload = json.loads(Path(os.environ["FX009_FIXTURE"]).read_bytes())
case_access_provider.register_case("demo-case", "owner", "org")
job, _ = job_manager.create_job("demo-case", "demo-evidence", "synthetic", "owner", "org")
payload["job_id"] = job
result = AnalysisResult.model_validate(payload)
job_manager.store_result(job, result)
(root / "job").write_text(job)
(root / "expected").write_bytes(json.dumps(result.model_dump(mode="json"), ensure_ascii=False).encode())
write_private_token(root / "token", issue_reporter(
    subject="reader", organization="org", case_id="demo-case", job_ids=[job],
))
"""

SERVER = """
import os
from pathlib import Path
import socket
import sys
import uvicorn
from core.db import db
from core.main import app

fetchone = db.fetchone
def count_result_reads(query, params=()):
    if query.startswith("SELECT result_json FROM job_results"):
        with (Path(os.environ["FX009_TEST_ROOT"]) / "reads").open("a") as log:
            log.write("1\\n")
    return fetchone(query, params)
db.fetchone = count_result_reads
sock = socket.socket(fileno=int(sys.argv[1]))
uvicorn.Server(uvicorn.Config(app, lifespan="off", access_log=False)).run(sockets=[sock])
"""


@contextmanager
def hub_server(hub, env, log_path):
    with socket.socket() as listener, log_path.open("wb") as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        fd = listener.fileno()
        process = subprocess.Popen(
            [sys.executable, "-c", SERVER, str(fd)], cwd=hub, env=env, pass_fds=(fd,),
            stdout=log, stderr=log,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("synthetic Hub exited before readiness")
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.2)
                try:
                    connection.request("GET", "/health")
                    with connection.getresponse() as response:
                        if response.status == 200:
                            break
                except (OSError, http.client.HTTPException):
                    pass
                finally:
                    connection.close()
                time.sleep(0.05)
            else:
                raise RuntimeError("synthetic Hub readiness timed out")
            yield port
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


@unittest.skipUnless(os.environ.get("FX009_HUB_CHECKOUT"), "set FX009_HUB_CHECKOUT for the live regression")
class LiveHubTests(unittest.TestCase):
    def test_profile_validation_and_revocation_precede_dispatch(self):
        hub = Path(os.environ["FX009_HUB_CHECKOUT"]).resolve()
        status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=hub, text=True)
        self.assertTrue(all(line.startswith(("M  ", "A  ")) for line in status.splitlines()))
        self.assertEqual(subprocess.check_output(["git", "write-tree"], cwd=hub, text=True).strip(), HUB_TREE)

        with tempfile.TemporaryDirectory(prefix="fx009-live-") as directory:
            root = Path(directory)
            env = dict(os.environ, ENVIRONMENT="production",
                       JWT_SECRET_KEY=secrets.token_urlsafe(48), SERVER_HMAC_SIGNING_KEY=secrets.token_urlsafe(48),
                       ADMIN_API_KEYS=json.dumps([secrets.token_urlsafe(48)]), API_KEYS="[]",
                       FX009_TEST_ROOT=directory, FX009_FIXTURE=str(FIXTURE))
            env.pop("PYTHONPATH", None)
            for key in ("DATA_DIR", "DATABASE_PATH", "BACKUPS_DIR", "VAULT_BASE_DIR", "SCRATCH_BASE_DIR", "THREAT_INTEL_DIR"):
                env[key] = str(root / key.lower())
            seeded = subprocess.run([sys.executable, "-c", SEED], cwd=hub, env=env, capture_output=True, timeout=30)
            self.assertEqual(seeded.returncode, 0, "synthetic fixture initialization failed")
            calls = []
            reads = root / "reads"
            reads.touch()

            def receiver(path, body):
                calls.append((path, body))
                return 200, b""

            def fallback_receiver(path, body):
                calls.append(("fallback", body))
                return 200, b""

            with hub_server(hub, env, root / "hub.log") as source, endpoint(receiver) as primary, endpoint(fallback_receiver) as fallback:
                args = [sys.executable, str(CLIENT), "--hub-port", str(source), "--approved-model-port", str(primary),
                        "--job-id", (root / "job").read_text(), "--token-file", str(root / "token")]

                def check(extra, code, stdout, stderr):
                    result = subprocess.run(args + extra, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, code)
                    self.assertEqual(result.stdout, stdout)
                    self.assertEqual(result.stderr, stderr)

                check(["--model-port", str(fallback)], 2, b"", b"UNAPPROVED_PROFILE\n")
                self.assertEqual((reads.read_text(), calls), ("", []))
                check([], 0, b"OK\n", b"")
                self.assertEqual(reads.read_text(), "1\n")
                self.assertEqual(calls, [("/model", (root / "expected").read_bytes())])
                revoked = subprocess.run(
                    [sys.executable, "-m", "core.reporter_credentials", "revoke", "--token-file", str(root / "token")],
                    cwd=hub, env=env, capture_output=True, timeout=30,
                )
                self.assertEqual(revoked.returncode, 0)
                check([], 2, b"", b"SOURCE_AUTH_DENIED\n")
                self.assertEqual(reads.read_text(), "1\n")
                self.assertEqual(len(calls), 1)
            self.assertNotIn((root / "token").read_bytes().strip(), (root / "hub.log").read_bytes())
