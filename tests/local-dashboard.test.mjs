import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import http from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { createLocalGateway, localIdentity, makeLocalConfig } from "../scripts/local-dashboard.mjs";

async function fixture(t) {
  const requests = [];
  const backend = http.createServer((request, response) => {
    requests.push({ method: request.method, url: request.url, headers: request.headers });
    request.resume();
    response.setHeader("content-type", "application/json");
    response.end(JSON.stringify(requests.at(-1)));
  });
  backend.listen(0, "127.0.0.1");
  await once(backend, "listening");
  const workerPort = backend.address().port;
  const { server } = createLocalGateway({ workerPort, port: 0 });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port;
  t.after(async () => {
    for (const current of [server, backend]) {
      current.closeAllConnections();
      await new Promise((resolve) => current.close(resolve));
    }
  });
  const request = (options = {}) => new Promise((resolve, reject) => {
    const pending = http.request({ hostname: "127.0.0.1", port, path: "/api/tasks", ...options }, (response) => {
      let text = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => { text += chunk; });
      response.on("end", () => resolve({ status: response.statusCode, headers: response.headers, text }));
    });
    pending.on("error", reject);
    pending.end();
  });
  return { port, workerPort, requests, request, origin: `http://127.0.0.1:${port}` };
}

test("local reads get an explicit synthetic identity; supplied credentials are discarded", async (t) => {
  const { request } = await fixture(t);
  const response = await request({ headers: {
    "oai-authenticated-user-id": "external-user", "oai-authenticated-user-email": "external@example.test",
    "oai-authenticated-user-role": "admin", Authorization: "Bearer synthetic-only-test", Cookie: "session=synthetic-only-test",
    Forwarded: "host=external.example", "X-Forwarded-Host": "external.example", "X-Real-IP": "203.0.113.1",
  } });
  assert.equal(response.status, 200);
  const { headers } = JSON.parse(response.text);
  assert.equal(headers["oai-authenticated-user-id"], localIdentity.userId);
  assert.equal(headers["oai-authenticated-user-email"], localIdentity.email);
  for (const name of ["oai-authenticated-user-role", "authorization", "cookie", "forwarded", "x-forwarded-host", "x-real-ip"]) assert.equal(headers[name], undefined);
  assert.equal(response.headers["x-forenzx-local-mode"], "synthetic-account");
  assert.equal(response.headers["cache-control"], "no-store");
});

test("a valid local mutation maps only its validated Origin to the internal Worker", async (t) => {
  const { request, origin, workerPort } = await fixture(t);
  const response = await request({ method: "PATCH", headers: { Origin: origin, "Sec-Fetch-Site": "same-origin" } });
  assert.equal(response.status, 200);
  const { headers } = JSON.parse(response.text);
  assert.equal(headers.origin, `http://127.0.0.1:${workerPort}`);
  assert.equal(headers.host, `127.0.0.1:${workerPort}`);
});

test("mutations require an exact local Origin and reject foreign, null and cross-site Origins", async (t) => {
  const { request, requests, origin } = await fixture(t);
  for (const headers of [
    {}, { Origin: "null" }, { Origin: "https://external.example" }, { Origin: `${origin}/` },
    { Origin: origin.replace("http:", "https:") }, { Origin: origin, "Sec-Fetch-Site": "cross-site" },
  ]) assert.equal((await request({ method: "PATCH", headers })).status, 403);
  assert.equal(requests.length, 0, "Rejected requests must not reach the Worker.");
});

test("foreign Origins and DNS-rebinding Host values cannot read local tasks", async (t) => {
  const { request, requests, port } = await fixture(t);
  for (const headers of [
    { Origin: "https://external.example" }, { "Sec-Fetch-Site": "cross-site" },
    { Host: `external.example:${port}` }, { Host: "127.0.0.1:1" }, { Host: `127.0.0.1:${port}@external.example` },
  ]) assert.equal((await request({ headers })).status, 403);
  assert.equal(requests.length, 0);
});

test("localhost is accepted only with its own exact matching Origin", async (t) => {
  const { request, port, origin } = await fixture(t);
  const host = `localhost:${port}`;
  assert.equal((await request({ method: "PATCH", headers: { Host: host, Origin: `http://${host}` } })).status, 200);
  assert.equal((await request({ method: "PATCH", headers: { Host: host, Origin: origin } })).status, 403);
});

test("absolute and network-path proxy requests are rejected", async (t) => {
  const { request, requests } = await fixture(t);
  for (const value of ["http://external.example/api/tasks", "//external.example/api/tasks", "/\\external.example/api/tasks"]) {
    assert.equal((await request({ path: value })).status, 400);
  }
  assert.equal((await request({ method: "TRACE" })).status, 405);
  assert.equal(requests.length, 0);
});

test("connection-nominated headers are removed while synthetic identity remains fixed", async (t) => {
  const { request } = await fixture(t);
  const response = await request({ headers: { Connection: "x-extra, oai-authenticated-user-id", "X-Extra": "remove-me" } });
  const { headers } = JSON.parse(response.text);
  assert.equal(headers["x-extra"], undefined);
  assert.equal(headers["oai-authenticated-user-id"], localIdentity.userId);
});

test("local sign-in/out do not call hosted authentication", async (t) => {
  const { request, requests } = await fixture(t);
  const response = await request({ path: "/signin-with-chatgpt?return_to=https://external.example" });
  assert.equal(response.status, 200);
  assert.match(response.text, /Local synthetic account/);
  assert.equal(response.headers.location, undefined);
  assert.equal(requests.length, 0);
});

test("generated config is local, resolves build paths and excludes production bindings", () => {
  const root = mkdtempSync(path.join(tmpdir(), "forenzx-local-config-test-"));
  try {
    mkdirSync(path.join(root, "dist", "server"), { recursive: true });
    mkdirSync(path.join(root, "dist", "client"), { recursive: true });
    writeFileSync(path.join(root, "dist", "server", "index.js"), "export default {};");
    writeFileSync(path.join(root, "dist", "server", "wrangler.json"), JSON.stringify({
      main: "index.js", assets: { directory: "../client" }, compatibility_date: "2026-05-15",
      compatibility_flags: ["nodejs_compat"], d1_databases: [{ binding: "DB", database_id: "production-id", remote: true }],
      services: [{ service: "production" }], vars: { PRIVATE_VALUE: "synthetic-test-only" }, routes: ["example.test/*"],
    }));
    const config = JSON.parse(readFileSync(makeLocalConfig(root, path.join(root, "local")), "utf8"));
    assert.equal(config.dev.ip, "127.0.0.1");
    assert.equal(config.main, path.join(root, "dist", "server", "index.js"));
    assert.equal(config.assets.directory, path.join(root, "dist", "client"));
    assert.equal(config.d1_databases[0].migrations_dir, path.join(root, "drizzle"));
    assert.equal(config.d1_databases[0].database_id, "00000000-0000-4000-8000-000000000000");
    assert.equal(config.d1_databases[0].remote, undefined);
    for (const key of ["services", "vars", "routes"]) assert.equal(config[key], undefined);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
