import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import type { Task } from "../lib/types";
import {
  buildTaskMutation,
  completedDependents,
  MAX_EVIDENCE_LENGTH,
  mergeTaskStates,
  readTaskBody,
  requireSameOrigin,
  TaskRequestError,
  validateTaskUpdate,
  type SqlStatement,
  type TaskPatch,
} from "../lib/task-state";

const now = "2026-11-20T22:00:00.000Z";
function makeTask(id = "FX-001", override: Partial<Task> = {}): Task {
  return {
    id, title: id, phase: "Kvalita", priority: "P0", description: "Synthetic test task",
    acceptance: ["A", "B"], dependencies: [], estimate: "1 h", gate: true,
    sourceIds: [], status: "todo", evidence: "", checks: [], revision: 0, updatedAt: null,
    ...override,
  };
}
const donePatch: TaskPatch = { status: "done", evidence: "Synthetic test log", checks: [0, 1], revision: 0 };

function database(tasks: Task[], users = ["owner"]): DatabaseSync {
  const db = new DatabaseSync(":memory:");
  db.exec(`
    CREATE TABLE task_state (
      user_id TEXT NOT NULL, task_id TEXT NOT NULL, status TEXT NOT NULL,
      evidence TEXT NOT NULL, checks_json TEXT NOT NULL, revision INTEGER NOT NULL,
      updated_at TEXT, last_mutation_id TEXT, PRIMARY KEY (user_id, task_id)
    );
    CREATE TABLE task_events (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL, task_id TEXT NOT NULL,
      from_status TEXT NOT NULL, to_status TEXT NOT NULL, evidence TEXT NOT NULL,
      checks_json TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL,
      UNIQUE (user_id, task_id, revision)
    );
  `);
  const insert = db.prepare("INSERT INTO task_state (user_id, task_id, status, evidence, checks_json, revision, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)");
  for (const user of users) for (const task of tasks) {
    insert.run(user, task.id, task.status, task.evidence, JSON.stringify(task.checks), task.revision, task.updatedAt);
  }
  return db;
}

// D1 batch is transactional. Exercise production SQL against actual SQLite,
// including races caused by snapshots loaded before a competing mutation.
function batch(db: DatabaseSync, statements: SqlStatement[]) {
  db.exec("BEGIN");
  try {
    const results = statements.map((statement) => db.prepare(statement.sql).all(...statement.values));
    db.exec("COMMIT");
    return results;
  } catch (error) {
    db.exec("ROLLBACK");
    throw error;
  }
}

test("completion requires every acceptance condition and nonempty evidence", () => {
  const task = makeTask();
  assert.equal(validateTaskUpdate(task, [task], donePatch).ok, true);
  assert.equal(validateTaskUpdate(task, [task], { ...donePatch, checks: [0] }).ok, false);
  assert.equal(validateTaskUpdate(task, [task], { ...donePatch, evidence: " \n " }).ok, false);
});

test("completion rejects unfinished and unknown dependencies", () => {
  const prerequisite = makeTask("FX-A");
  const task = makeTask("FX-B", { dependencies: [prerequisite.id] });
  const result = validateTaskUpdate(task, [prerequisite, task], donePatch);
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.status, 409);
  assert.equal(validateTaskUpdate(task, [task], donePatch).ok, false);
  assert.equal(validateTaskUpdate(task, [{ ...prerequisite, status: "done" }, task], donePatch).ok, true);
});

test("stale revision fails without silently overwriting a newer edit", () => {
  const task = makeTask("FX-A", { revision: 3 });
  const result = validateTaskUpdate(task, [task], { ...donePatch, revision: 2 });
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.status, 409);
});

test("malformed acceptance, unknown fields and oversized evidence are rejected", () => {
  const task = makeTask();
  for (const checks of [[0, 0], [-1], [2], [0.5], ["0"], null]) {
    assert.equal(validateTaskUpdate(task, [task], { ...donePatch, checks }).ok, false);
  }
  assert.equal(validateTaskUpdate(task, [task], { ...donePatch, admin: true }).ok, false);
  assert.equal(validateTaskUpdate(task, [task], { ...donePatch, evidence: "x".repeat(MAX_EVIDENCE_LENGTH + 1) }).ok, false);
  assert.equal(validateTaskUpdate(task, [task], { ...donePatch, revision: Number.MAX_SAFE_INTEGER + 1 }).ok, false);
  assert.equal(validateTaskUpdate(task, [task], []).ok, false);
});

test("reopening a prerequisite checks transitive completed dependents", () => {
  const a = makeTask("A", { status: "done" });
  const b = makeTask("B", { dependencies: ["A"] });
  const c = makeTask("C", { dependencies: ["B"], status: "done" });
  assert.deepEqual(completedDependents("A", [a, b, c]).map((task) => task.id), ["C"]);
  assert.equal(validateTaskUpdate(a, [a, b, c], { ...donePatch, status: "in_progress" }).ok, false);
});

test("a successful CAS creates exactly one history event; stale retries create none", () => {
  const task = makeTask();
  const db = database([task]);
  try {
    const first = batch(db, buildTaskMutation("owner", task, [task], donePatch, now, "first"));
    assert.equal(first[0].length, 1);
    assert.equal(first[0][0].revision, 1);
    const retry = batch(db, buildTaskMutation("owner", task, [task], donePatch, now, "stale"));
    assert.equal(retry[0].length, 0);
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events").get()?.count, 1);
    assert.equal(db.prepare("SELECT last_mutation_id FROM task_state").get()?.last_mutation_id, "first");
  } finally { db.close(); }
});

test("SQL closes the race where a dependency reopens after initial validation", () => {
  const a = makeTask("A", { status: "done", evidence: "Verified", checks: [0, 1] });
  const b = makeTask("B", { dependencies: ["A"] });
  const snapshot = [a, b];
  const db = database(snapshot);
  try {
    assert.equal(validateTaskUpdate(b, snapshot, donePatch).ok, true);
    batch(db, buildTaskMutation("owner", a, snapshot, { ...donePatch, status: "in_progress" }, now, "reopen-a"));
    const raced = batch(db, buildTaskMutation("owner", b, snapshot, donePatch, now, "finish-b"));
    assert.equal(raced[0].length, 0);
    assert.equal(db.prepare("SELECT status FROM task_state WHERE task_id = 'B'").get()?.status, "todo");
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events").get()?.count, 1);
  } finally { db.close(); }
});

test("SQL blocks reopening when a dependent completes after initial validation", () => {
  const a = makeTask("A", { status: "done", evidence: "Verified", checks: [0, 1] });
  const b = makeTask("B", { dependencies: ["A"] });
  const snapshot = [a, b];
  const db = database(snapshot);
  try {
    assert.equal(validateTaskUpdate(a, snapshot, { ...donePatch, status: "todo" }).ok, true);
    batch(db, buildTaskMutation("owner", b, snapshot, donePatch, now, "finish-b"));
    const raced = batch(db, buildTaskMutation("owner", a, snapshot, { ...donePatch, status: "todo" }, now, "reopen-a"));
    assert.equal(raced[0].length, 0);
    assert.equal(db.prepare("SELECT status FROM task_state WHERE task_id = 'A'").get()?.status, "done");
  } finally { db.close(); }
});

test("owner namespaces isolate mutations and dependency completion", () => {
  const a = makeTask("A");
  const b = makeTask("B", { dependencies: ["A"] });
  const tasks = [a, b];
  const db = database(tasks, ["alice", "bob"]);
  try {
    batch(db, buildTaskMutation("alice", a, tasks, donePatch, now, "alice-a"));
    const bob = batch(db, buildTaskMutation("bob", b, tasks, donePatch, now, "bob-b"));
    assert.equal(bob[0].length, 0);
    assert.equal(db.prepare("SELECT status FROM task_state WHERE user_id = 'bob' AND task_id = 'A'").get()?.status, "todo");
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events WHERE user_id = 'bob'").get()?.count, 0);
  } finally { db.close(); }
});

test("history-write failure rolls back its associated task update", () => {
  const a = makeTask("A");
  const b = makeTask("B");
  const tasks = [a, b];
  const db = database(tasks);
  try {
    batch(db, buildTaskMutation("owner", a, tasks, donePatch, now, "duplicate-id"));
    assert.throws(() => batch(db, buildTaskMutation("owner", b, tasks, donePatch, now, "duplicate-id")));
    const row = db.prepare("SELECT status, revision FROM task_state WHERE task_id = 'B'").get();
    assert.equal(row?.status, "todo");
    assert.equal(row?.revision, 0);
  } finally { db.close(); }
});

test("writes require a matching origin, including scheme and port", () => {
  const request = (origin?: string, site = "same-origin") => new Request("https://brief.example/api/tasks/A", {
    method: "PATCH", headers: { ...(origin ? { Origin: origin } : {}), "Sec-Fetch-Site": site },
  });
  assert.doesNotThrow(() => requireSameOrigin(request("https://brief.example")));
  for (const origin of [undefined, "null", "https://evil.example", "http://brief.example", "https://brief.example:444"]) {
    assert.throws(() => requireSameOrigin(request(origin)), (error) => error instanceof TaskRequestError && error.status === 403);
  }
  assert.throws(() => requireSameOrigin(request("https://brief.example", "cross-site")));
});

test("body parser enforces JSON and a byte limit even without Content-Length", async () => {
  const req = (body: string, contentType = "application/json") => new Request("https://brief.example/api/tasks/A", {
    method: "PATCH", headers: { "Content-Type": contentType }, body,
  });
  assert.deepEqual(await readTaskBody(req(JSON.stringify(donePatch))), donePatch);
  await assert.rejects(readTaskBody(req("{")), (error) => error instanceof TaskRequestError && error.status === 400);
  await assert.rejects(readTaskBody(req("{}", "text/plain")), (error) => error instanceof TaskRequestError && error.status === 415);
  await assert.rejects(readTaskBody(req(JSON.stringify({ evidence: "é".repeat(20_000) }))), (error) => error instanceof TaskRequestError && error.status === 413);
});

test("state overlay preserves catalog definitions and rejects corrupt stored checks", () => {
  const task = makeTask();
  const [result] = mergeTaskStates([task], [{ task_id: task.id, status: "in_progress", evidence: "Working", checks_json: "[0]", revision: 4, updated_at: now }]);
  assert.equal(result.title, task.title);
  assert.deepEqual(result.acceptance, task.acceptance);
  assert.equal(result.revision, 4);
  assert.deepEqual(result.checks, [0]);
  assert.throws(() => mergeTaskStates([task], [{ task_id: task.id, status: "todo", evidence: "", checks_json: '["bad"]', revision: 0, updated_at: null }]));
});
