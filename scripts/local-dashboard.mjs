#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import http from "node:http";
import net from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const projectRoot = fileURLToPath(new URL("../", import.meta.url));
export const localIdentity = Object.freeze({
  userId: "forenzx_local_synthetic_user",
  email: "local-demo@forenzx.invalid",
  fullName: "ForenZX Local Demo",
});
const localAddress = "127.0.0.1";
const trustedHeaderPrefix = "oai-authenticated-user-";
const hopHeaders = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailer", "transfer-encoding", "upgrade",
]);
const children = new Set();
let stopping = false;

function errorResponse(response, status, message) {
  response.writeHead(status, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
  response.end(`${message}\n`);
}

function filteredHeaders(headers) {
  const connectionHeaders = new Set(String(headers.connection ?? "").toLowerCase().split(",").map((value) => value.trim()));
  return Object.fromEntries(Object.entries(headers).filter(([name]) =>
    !hopHeaders.has(name) && !connectionHeaders.has(name)));
}

/** Development adapter only. Never bind this server to a public interface. */
export function createLocalGateway({ workerPort, port = 5173 }) {
  if (!Number.isInteger(workerPort) || workerPort < 1 || workerPort > 65535) throw new Error("Invalid Worker port.");
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error("Invalid dashboard port.");
  const backendOrigin = `http://${localAddress}:${workerPort}`;
  const server = http.createServer((request, response) => {
    const actualPort = server.address()?.port;
    const host = request.headers.host;
    const hosts = new Set([`${localAddress}:${actualPort}`, `localhost:${actualPort}`]);
    const hostCount = request.rawHeaders.filter((name, index) => index % 2 === 0 && name.toLowerCase() === "host").length;
    if (request.socket.remoteAddress !== localAddress || hostCount !== 1 || !hosts.has(host)) {
      errorResponse(response, 403, "Only this loopback dashboard host is allowed.");
      return;
    }
    // Do not allow absolute-form proxy requests, authority-form requests or a
    // network-path URL to turn this development server into an open proxy.
    if (!request.url?.startsWith("/") || request.url.startsWith("//") || request.url.includes("\\")) {
      errorResponse(response, 400, "Expected a local relative request path.");
      return;
    }
    if (!["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"].includes(request.method)) {
      errorResponse(response, 405, "Unsupported local request method.");
      return;
    }
    const origin = request.headers.origin;
    const safeMethod = ["GET", "HEAD", "OPTIONS"].includes(request.method);
    const expectedOrigin = `http://${host}`;
    if (request.headers["sec-fetch-site"] === "cross-site" ||
        (origin !== undefined && origin !== expectedOrigin) || (!safeMethod && origin !== expectedOrigin)) {
      errorResponse(response, 403, "Request origin must match this local dashboard.");
      return;
    }
    const pathname = request.url.split("?")[0];
    if (["/signin-with-chatgpt", "/signout-with-chatgpt", "/callback"].includes(pathname)) {
      errorResponse(response, 200, "Local synthetic account: no ChatGPT session is used. Return to / to continue; stop the launcher with Ctrl+C.");
      return;
    }
    const headers = filteredHeaders(request.headers);
    for (const name of Object.keys(headers)) {
      if (name.startsWith(trustedHeaderPrefix) || name === "forwarded" || name.startsWith("x-forwarded-") ||
          name === "x-real-ip" || name === "authorization" || name === "cookie") delete headers[name];
    }
    headers.host = `${localAddress}:${workerPort}`;
    // Only a validated same-origin Origin is mapped to the internal Worker.
    if (origin !== undefined) headers.origin = backendOrigin;
    headers[`${trustedHeaderPrefix}id`] = localIdentity.userId;
    headers[`${trustedHeaderPrefix}email`] = localIdentity.email;
    headers[`${trustedHeaderPrefix}full-name`] = encodeURIComponent(localIdentity.fullName);
    headers[`${trustedHeaderPrefix}full-name-encoding`] = "percent-encoded-utf-8";
    const upstream = http.request({
      hostname: localAddress, port: workerPort, path: request.url,
      method: request.method, headers, timeout: 30_000,
    }, (upstreamResponse) => {
      const responseHeaders = filteredHeaders(upstreamResponse.headers);
      responseHeaders["x-forenzx-local-mode"] = "synthetic-account";
      responseHeaders["cache-control"] = "no-store";
      const location = responseHeaders.location;
      if (typeof location === "string" && location.startsWith(`${backendOrigin}/`)) {
        responseHeaders.location = `${expectedOrigin}${location.slice(backendOrigin.length)}`;
      }
      response.writeHead(upstreamResponse.statusCode ?? 502, responseHeaders);
      upstreamResponse.pipe(response);
      upstreamResponse.on("error", () => response.destroy());
    });
    upstream.on("timeout", () => upstream.destroy(new Error("Local Worker timeout.")));
    upstream.on("error", () => {
      if (!response.headersSent) errorResponse(response, 502, "Local Worker is not ready or has stopped.");
      else response.destroy();
    });
    request.on("aborted", () => upstream.destroy());
    response.on("close", () => { if (!response.writableEnded) upstream.destroy(); });
    request.pipe(upstream);
  });
  server.on("connect", (_request, socket) => socket.end("HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n"));
  server.on("upgrade", (_request, socket) => socket.end("HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n"));
  server.requestTimeout = 30_000;
  server.headersTimeout = 10_000;
  return { server, port };
}

export function makeLocalConfig(root, directory) {
  const sourceDirectory = path.join(root, "dist", "server");
  const source = JSON.parse(readFileSync(path.join(sourceDirectory, "wrangler.json"), "utf8"));
  if (source.d1_databases?.length !== 1 || source.d1_databases[0].binding !== "DB") {
    throw new Error("The local launcher expects this project's single D1 binding, DB.");
  }
  const main = path.resolve(sourceDirectory, source.main);
  const assets = path.resolve(sourceDirectory, source.assets.directory);
  if (!existsSync(main) || !existsSync(assets)) throw new Error("Build output is incomplete. Run npm run build.");
  // Construct a minimal local config; never copy remote resources, secrets,
  // routes, services or production database IDs into the development runtime.
  const config = {
    name: "forenzx-analysis-brief-local",
    main,
    compatibility_date: source.compatibility_date,
    compatibility_flags: source.compatibility_flags,
    no_bundle: true,
    rules: source.rules,
    assets: { directory: assets },
    d1_databases: [{
      binding: "DB", database_name: "forenzx-local-d1",
      database_id: "00000000-0000-4000-8000-000000000000",
      migrations_dir: path.join(root, "drizzle"),
    }],
    dev: { ip: localAddress, local_protocol: "http" },
  };
  mkdirSync(directory, { recursive: true });
  const configPath = path.join(directory, "wrangler.local.json");
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  return configPath;
}

function childEnvironment(directory) {
  return {
    ...process.env,
    WRANGLER_SEND_METRICS: "false", WRANGLER_WRITE_LOGS: "false", CLOUDFLARE_CF_FETCH_ENABLED: "false",
    WRANGLER_LOG_PATH: path.join(directory, "logs"),
    WRANGLER_REGISTRY_PATH: path.join(directory, "dev-registry"),
    MINIFLARE_REGISTRY_PATH: path.join(directory, "registry"),
  };
}

function startChild(command, args, options = {}) {
  if (stopping) throw new Error("Local launcher is stopping.");
  const child = spawn(command, args, {
    cwd: projectRoot, stdio: ["ignore", "inherit", "inherit"],
    detached: process.platform !== "win32", ...options,
  });
  children.add(child);
  child.once("exit", () => children.delete(child));
  child.once("error", () => children.delete(child));
  return child;
}

async function run(command, args, options) {
  const child = startChild(command, args, options);
  const [code, signal] = await once(child, "exit");
  if (code !== 0) throw new Error(`${command} ${args.join(" ")} failed (${signal ?? code}).`);
}

async function stopChild(child) {
  if (!child?.pid || !children.has(child)) return;
  const terminate = (signal) => {
    try {
      if (process.platform === "win32") child.kill(signal);
      else process.kill(-child.pid, signal); // only the process group we created
    } catch (error) { if (error.code !== "ESRCH") throw error; }
  };
  const exited = once(child, "exit");
  terminate("SIGTERM");
  const timeout = setTimeout(() => terminate("SIGKILL"), 3000);
  timeout.unref();
  try { await exited; } finally { clearTimeout(timeout); }
}

async function reservePort(excludedPort) {
  const reservation = net.createServer((socket) => socket.destroy());
  reservation.listen(0, localAddress);
  await once(reservation, "listening");
  const port = reservation.address().port;
  const release = async () => {
    if (reservation.listening) await new Promise((resolve, reject) => reservation.close((error) => error ? reject(error) : resolve()));
  };
  if (port === excludedPort) { await release(); return reservePort(excludedPort); }
  return { port, release };
}

async function closeServer(server) {
  if (!server?.listening) return;
  server.closeAllConnections();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}

async function startDashboard({ directory, port }) {
  const configPath = makeLocalConfig(projectRoot, directory);
  const persist = path.join(directory, "state");
  const wrangler = path.join(projectRoot, "node_modules", "wrangler", "bin", "wrangler.js");
  const env = childEnvironment(directory);
  // Hold the internal port while binding the external one and migrating D1.
  // This also prevents two independently selected automatic ports colliding.
  const reservation = await reservePort(port);
  const workerPort = reservation.port;
  const { server } = createLocalGateway({ workerPort, port });
  let worker;
  try {
    // Reserve the user-facing port before touching the local DB. Occupied
    // ports fail; the launcher never terminates another process to free them.
    server.listen(port, localAddress);
    await once(server, "listening");
    const origin = `http://${localAddress}:${server.address().port}`;
    console.log(`Local D1: ${persist}`);
    await run(process.execPath, [wrangler, "d1", "migrations", "apply", "DB", "--local", "--config", configPath, "--persist-to", persist], { env });
    await reservation.release();
    worker = startChild(process.execPath, [
      wrangler, "dev", "--config", configPath, "--local", "--persist-to", persist,
      "--ip", localAddress, "--port", String(workerPort), "--inspector-port", "0", "--inspector-ip", localAddress,
      "--no-show-interactive-dev-session", "--log-level", "warn",
    ], { env });
    let workerFailure;
    worker.once("error", (error) => { workerFailure = error; });
    worker.once("exit", (code, signal) => { workerFailure = new Error(`Local Worker stopped (${signal ?? code}).`); });
    const deadline = Date.now() + 60_000;
    let ready = false;
    while (Date.now() < deadline) {
      if (workerFailure) throw workerFailure;
      if (stopping) throw new Error("Local launcher is stopping.");
      try {
        const response = await fetch(`${origin}/api/tasks`, { signal: AbortSignal.timeout(2000) });
        if (response.ok) {
          const result = await response.json();
          if (Array.isArray(result.tasks) && result.tasks.length > 0) { ready = true; break; }
        } else await response.body?.cancel();
      } catch { /* Worker is still starting. */ }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    if (!ready) throw new Error("Local Worker did not return a working task API within 60 seconds.");
    return { server, worker, origin, stop: async () => { await closeServer(server); await stopChild(worker); } };
  } catch (error) {
    await reservation.release();
    await closeServer(server);
    await stopChild(worker);
    throw error;
  }
}

async function smokeTest() {
  const directory = mkdtempSync(path.join(tmpdir(), "forenzx-local-smoke-"));
  let dashboard;
  try {
    dashboard = await startDashboard({ directory, port: 0 });
    const { origin } = dashboard;
    const page = await fetch(origin);
    assert.equal(page.status, 200, "Dashboard HTML must load.");
    assert.match(await page.text(), /ForenZX/);
    const initial = await (await fetch(`${origin}/api/tasks`)).json();
    const task = initial.tasks.find((item) => item.status !== "done");
    assert.ok(task, "Need an unfinished synthetic task for the local save test.");
    const evidence = "Synthetic local HTTP smoke test; no hosted data was used.";
    const patch = { status: task.status, evidence, checks: task.checks, revision: task.revision, definitionKey: task.definitionKey };
    const save = (value) => fetch(`${origin}/api/tasks/${encodeURIComponent(task.id)}`, {
      method: "PATCH", headers: { Origin: origin, "Content-Type": "application/json" }, body: JSON.stringify(value),
    });
    const contenders = [patch, { ...patch, evidence: "Concurrent synthetic review note." }];
    const initialExport = await (await fetch(`${origin}/api/export`)).json();
    const responses = await Promise.all(contenders.map(save));
    assert.deepEqual(responses.map((item) => item.status).sort(), [200, 409]);
    const accepted = contenders[responses.findIndex((item) => item.status === 200)];
    for (const item of responses) await item.arrayBuffer();
    const retry = await save(accepted);
    assert.equal(retry.status, 409, "Retrying a committed old revision must preserve the winner.");
    await retry.arrayBuffer();
    const snapshotResponse = await fetch(`${origin}/api/export`);
    assert.equal(snapshotResponse.status, 200);
    const snapshot = await snapshotResponse.json();
    const saved = snapshot.tasks.find((item) => item.id === task.id);
    assert.equal(saved?.evidence, accepted.evidence);
    assert.equal(saved.revision, task.revision + 1);
    assert.equal(snapshot.events.length, initialExport.events.length + 1);
    assert.equal(snapshot.events.filter((event) => event.taskId === task.id && event.revision === saved.revision
      && event.evidence === accepted.evidence).length, 1);
    const foreign = await fetch(`${origin}/api/tasks/${encodeURIComponent(task.id)}`, {
      method: "PATCH", headers: { Origin: "https://foreign.example", "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    assert.equal(foreign.status, 403, "Foreign Origin must be rejected by the gateway.");
    await foreign.body?.cancel();
    await dashboard.stop();
    dashboard = await startDashboard({ directory, port: 0 });
    const restarted = await (await fetch(`${dashboard.origin}/api/tasks`)).json();
    assert.equal(restarted.tasks.find((item) => item.id === task.id)?.evidence, accepted.evidence, "Local D1 state must survive a restart.");
    console.log(`PASS: local HTML, ${initial.tasks.length} seeded tasks, concurrent save/409, stale retry, export/history, foreign-Origin rejection and D1 restart persistence.`);
  } finally {
    await dashboard?.stop();
    rmSync(directory, { recursive: true, force: true }); // only our mkdtemp directory
  }
}

function prerequisites() {
  const node = process.versions.node.split(".").map(Number);
  if (node[0] < 22 || (node[0] === 22 && (node[1] < 13))) throw new Error("Node.js 22.13.0 or newer is required.");
  const packageJson = JSON.parse(readFileSync(path.join(projectRoot, "package.json"), "utf8"));
  if (packageJson.name !== "forenzx-analysis-brief-board") throw new Error("This is not the ForenZX dashboard checkout.");
  if (!existsSync(path.join(projectRoot, "package-lock.json"))) throw new Error("package-lock.json is required; restore it from your clone.");
  const python = spawnSync("python3", ["-c", "import sys; print('.'.join(map(str, sys.version_info[:3]))); sys.exit(0 if sys.version_info >= (3, 10) else 1)"], { encoding: "utf8" });
  if (python.error || python.status !== 0) throw new Error("Python 3.10 or newer must be available as python3.");
  const npm = spawnSync("npm", ["--version"], { encoding: "utf8" });
  if (npm.error || npm.status !== 0) throw new Error("npm is required; install it with Node.js.");
  console.log(`Prerequisites: Node ${process.versions.node}, npm ${npm.stdout.trim()}, Python ${python.stdout.trim()}.`);
}

function dependenciesReady() {
  try {
    const expected = JSON.parse(readFileSync(path.join(projectRoot, "package-lock.json"), "utf8"));
    const installed = JSON.parse(readFileSync(path.join(projectRoot, "node_modules", ".package-lock.json"), "utf8"));
    const direct = { ...expected.packages[""].dependencies, ...expected.packages[""].devDependencies };
    for (const name of Object.keys(direct)) {
      const key = `node_modules/${name}`;
      if (expected.packages[key]?.version !== installed.packages[key]?.version || !existsSync(path.join(projectRoot, key, "package.json"))) return false;
    }
    return ["vinext/dist/cli.js", "wrangler/bin/wrangler.js", "typescript/bin/tsc"].every((name) => existsSync(path.join(projectRoot, "node_modules", name)));
  } catch { return false; }
}

function argumentsFrom(argv) {
  const options = { bootstrap: false, checkOnly: false, smoke: false, install: false, port: 5173, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--bootstrap") options.bootstrap = true;
    else if (argument === "--check-only") { options.checkOnly = true; options.bootstrap = true; }
    else if (argument === "--smoke") options.smoke = true;
    else if (argument === "--install") options.install = true;
    else if (argument === "--help" || argument === "-h") options.help = true;
    else if (argument === "--port") {
      const value = argv[++index];
      if (!/^(0|[1-9]\d*)$/.test(value ?? "")) throw new Error("--port requires 0 (automatic) or a port from 1 to 65535.");
      options.port = Number(value);
      if (options.port > 65535) throw new Error("--port must not exceed 65535.");
    } else throw new Error(`Unknown option: ${argument}. Use --help.`);
  }
  if (options.install && !options.bootstrap) throw new Error("Use --install with scripts/local-bootstrap.sh.");
  if (options.smoke && options.bootstrap) throw new Error("Use --check-only for full verification, or node scripts/local-dashboard.mjs --smoke for an existing build.");
  return options;
}

async function main() {
  const options = argumentsFrom(process.argv.slice(2));
  if (options.help) {
    console.log("Usage: bash scripts/local-bootstrap.sh [--check-only] [--install] [--port 5173|0]\n\nBootstrap verifies prerequisites, installs missing dependencies, runs tests and a build,\nthen checks the local HTTP flow in a temporary DB before starting the local dashboard.\n--check-only  Run all verification, including the build and local HTTP smoke test, then exit.\n--install     Run npm ci even if the existing direct dependency versions match.\n--port 0      Let the OS choose a free user-facing port (default: 5173).\n\nAdvanced: node scripts/local-dashboard.mjs [--port N] uses an existing build;\n          node scripts/local-dashboard.mjs --smoke tests that build and exits.");
    return;
  }
  prerequisites();
  if (options.bootstrap) {
    if (options.install || !dependenciesReady()) await run("npm", ["ci"]);
    else console.log("Existing direct dependency versions match package-lock.json; use --install to reinstall the complete locked tree.");
    for (const args of [["test"], ["run", "test:product"], ["run", "test:reference"], ["run", "typecheck"]]) await run("npm", args);
    await run(process.execPath, ["--test", "tests/local-dashboard.test.mjs"]);
    await run("npm", ["run", "build"]);
    await smokeTest();
    if (options.checkOnly) { console.log("All local checks passed. No dashboard remains running."); return; }
  } else if (options.smoke) { await smokeTest(); return; }
  const directory = path.join(projectRoot, ".wrangler", "forenzx-local");
  const dashboard = await startDashboard({ directory, port: options.port });
  console.log(`\nForenZX local dashboard: ${dashboard.origin}\nSynthetic account: ${localIdentity.fullName} <${localIdentity.email}>\nState is local to this checkout and seeded from git. Hosted D1 is not synchronized.\nBoth gateway and Worker listen only on 127.0.0.1. Stop with Ctrl+C.\n`);
  try {
    const [code, signal] = await once(dashboard.worker, "exit");
    if (!stopping) throw new Error(`Local Worker exited (${signal ?? code}).`);
  } finally { await dashboard.stop(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  for (const [signal, code] of [["SIGINT", 130], ["SIGTERM", 143]]) {
    process.once(signal, () => {
      stopping = true;
      Promise.allSettled([...children].map(stopChild)).finally(() => process.exit(code));
    });
  }
  main().catch(async (error) => {
    stopping = true;
    console.error(`ForenZX local setup failed: ${error.message}`);
    await Promise.allSettled([...children].map(stopChild));
    process.exitCode = 1;
  });
}
