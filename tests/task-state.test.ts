import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import { readFileSync } from "node:fs";
import type { Task } from "../lib/types";
import { definitionKey, serializeDefinition } from "../lib/task-definition";
import { legacyTaskDefinitions } from "../lib/legacy-task-definitions";
import {
  buildCatalogReconciliation,
  buildTaskMutation,
  completedDependents,
  exportTaskState,
  loadTaskStates,
  MAX_EVIDENCE_LENGTH,
  mergeTaskStates,
  planCatalogReconciliation,
  readTaskBody,
  requireSameOrigin,
  TaskRequestError,
  validateTaskUpdate as validateRawTaskUpdate,
  type TaskStateRow,
  type SqlStatement,
  type TaskPatch,
} from "../lib/task-state";

const now = "2026-11-20T22:00:00.000Z";
function makeTask(id = "FX-001", override: Partial<Task> = {}): Task {
  const task: Task = {
    id, title: id, phase: "Kvalita", priority: "P0", description: "Synthetic test task",
    acceptance: ["A", "B"], dependencies: [], estimate: "1 h", gate: true,
    sourceIds: [], status: "todo", evidence: "", checks: [], revision: 0, updatedAt: null,
    definitionKey: "",
    ...override,
  };
  return { ...task, definitionKey: definitionKey(task) };
}
const donePatch: TaskPatch = { status: "done", evidence: "Synthetic test log", checks: [0, 1], revision: 0 };

// Existing mutation tests use the freshly loaded definition. Separate tests
// below exercise omitted/stale client keys directly through the production API.
function validateTaskUpdate(task: Task, tasks: Task[], input: unknown) {
  return validateRawTaskUpdate(task, tasks, input && typeof input === "object" && !Array.isArray(input)
    ? { definitionKey: definitionKey(task), ...input } : input);
}

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
  db.exec(readFileSync("drizzle/0001_thick_human_fly.sql", "utf8"));
  const insert = db.prepare("INSERT INTO task_state (user_id, task_id, status, evidence, checks_json, revision, updated_at, definition_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
  for (const user of users) for (const task of tasks) {
    insert.run(user, task.id, task.status, task.evidence, JSON.stringify(task.checks), task.revision, task.updatedAt, serializeDefinition(task));
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
  const [result] = mergeTaskStates([task], [{ task_id: task.id, status: "in_progress", evidence: "Working", checks_json: "[0]", revision: 4, updated_at: now, definition_json: serializeDefinition(task) }]);
  assert.equal(result.title, task.title);
  assert.deepEqual(result.acceptance, task.acceptance);
  assert.equal(result.revision, 4);
  assert.deepEqual(result.checks, [0]);
  assert.equal(result.definitionKey, definitionKey(task));
  assert.throws(() => mergeTaskStates([task], [{ task_id: task.id, status: "todo", evidence: "", checks_json: '["bad"]', revision: 0, updated_at: null, definition_json: serializeDefinition(task) }]));
});

function rows(db: DatabaseSync, user = "owner"): TaskStateRow[] {
  return db.prepare("SELECT task_id, status, evidence, checks_json, revision, updated_at, definition_json FROM task_state WHERE user_id = ?").all(user) as TaskStateRow[];
}

test("old tabs cannot save against changed criteria, even with a current row revision", () => {
  const before = makeTask("A");
  const after = makeTask("A", { acceptance: ["A", "B", "New requirement"] });
  for (const input of [donePatch, { ...donePatch, definitionKey: definitionKey(before) }]) {
    const result = validateRawTaskUpdate(after, [after], input);
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.status, 409);
  }
  assert.equal(validateRawTaskUpdate(after, [after], { ...donePatch, checks: [0, 1, 2], definitionKey: definitionKey(after) }).ok, true);
});

test("append-only catalog changes preserve evidence and old checks while reopening done", () => {
  const before = makeTask("A", { status: "done", checks: [0, 1], evidence: "Original independent log", revision: 7 });
  const after = makeTask("A", { acceptance: ["A", "B", "New requirement"] });
  const db = database([before], ["owner", "another-owner"]);
  try {
    const plan = planCatalogReconciliation([after], rows(db));
    assert.equal(plan[0].reason, "catalog_changed");
    batch(db, buildCatalogReconciliation("owner", plan, now, "catalog"));
    const [result] = mergeTaskStates([after], rows(db));
    assert.equal(result.status, "in_progress");
    assert.deepEqual(result.checks, [0, 1]);
    assert.equal(result.evidence, "Original independent log");
    assert.equal(result.revision, 8);
    assert.equal(rows(db, "another-owner")[0].status, "done");
    assert.equal(rows(db, "another-owner")[0].revision, 7);
    const event = db.prepare("SELECT from_status, to_status, evidence, change_reason, definition_json FROM task_events").get();
    assert.equal(event?.from_status, "done");
    assert.equal(event?.to_status, "in_progress");
    assert.equal(event?.change_reason, "catalog_changed");
    assert.equal(event?.definition_json, serializeDefinition(after));
    assert.equal(event?.evidence, before.evidence);
    assert.equal(planCatalogReconciliation([after], rows(db)).length, 0);
    batch(db, buildCatalogReconciliation("owner", plan, now, "stale-catalog"));
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events").get()?.count, 1);
  } finally { db.close(); }
});

test("reordered or rewritten criteria never inherit unrelated index checks", () => {
  const before = makeTask("A", { acceptance: ["First", "Second", "Third"], checks: [0, 2], evidence: "Keep me", status: "in_progress" });
  const after = makeTask("A", { acceptance: ["Third", "Changed First", "Second", "New"] });
  const db = database([before]);
  try {
    const [change] = planCatalogReconciliation([after], rows(db));
    assert.deepEqual(change.checks, [0]);
    batch(db, buildCatalogReconciliation("owner", [change], now, "reorder"));
    const [result] = mergeTaskStates([after], rows(db));
    assert.deepEqual(result.checks, [0]);
    assert.equal(result.evidence, "Keep me");
  } finally { db.close(); }
});

test("legacy rows use the immutable prior catalog and preserve unchanged completed tasks", () => {
  const a = makeTask("FX-001", { ...legacyTaskDefinitions["FX-001"], status: "done", checks: [0, 1, 2], evidence: "Verified before migration", revision: 2 });
  const b = makeTask("FX-003", { ...legacyTaskDefinitions["FX-003"], status: "done", checks: [0, 1, 2], evidence: "License decision", revision: 3 });
  const updatedB = makeTask("FX-003", { ...b, acceptance: [...b.acceptance, "New terms review"] });
  const db = database([a, b]);
  try {
    db.exec("UPDATE task_state SET definition_json = NULL");
    const plan = planCatalogReconciliation([a, updatedB], rows(db));
    assert.equal(plan.find((change) => change.task.id === a.id)?.reason, null);
    batch(db, buildCatalogReconciliation("owner", plan, now, "legacy"));
    const result = mergeTaskStates([a, updatedB], rows(db));
    assert.equal(result[0].status, "done");
    assert.equal(result[0].revision, 2);
    assert.equal(result[0].evidence, a.evidence);
    assert.deepEqual(result[0].checks, [0, 1, 2]);
    assert.equal(result[1].status, "in_progress");
    assert.equal(result[1].revision, 4);
    assert.deepEqual(result[1].checks, [0, 1, 2]);
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events").get()?.count, 1);
  } finally { db.close(); }
});

test("catalog change reopens completed transitive dependents in its atomic batch", () => {
  const a = makeTask("A", { status: "done", checks: [0, 1], evidence: "A proof" });
  const b = makeTask("B", { dependencies: ["A"], status: "done", checks: [0, 1], evidence: "B proof" });
  const c = makeTask("C", { dependencies: ["B"], status: "done", checks: [0, 1], evidence: "C proof" });
  const changed = makeTask("A", { ...a, acceptance: [...a.acceptance, "New"] });
  const current = [changed, b, c];
  const db = database([a, b, c]);
  try {
    batch(db, buildCatalogReconciliation("owner", planCatalogReconciliation(current, rows(db)), now, "dependency"));
    const result = mergeTaskStates(current, rows(db));
    assert.deepEqual(result.map((task) => task.status), ["in_progress", "in_progress", "in_progress"]);
    assert.deepEqual(result.map((task) => task.evidence), ["A proof", "B proof", "C proof"]);
    assert.deepEqual(result[2].checks, [0, 1]);
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events WHERE change_reason = 'dependency_reopened'").get()?.count, 2);
  } finally { db.close(); }
});

test("catalog reconciliation CAS preserves a concurrent edit and rechecks dependencies", () => {
  const a = makeTask("A", { status: "done", checks: [0, 1], evidence: "A proof" });
  const b = makeTask("B", { dependencies: ["A"], status: "done", checks: [0, 1], evidence: "B old proof" });
  const current = [makeTask("A", { ...a, acceptance: [...a.acceptance, "New"] }), b];
  const db = database([a, b]);
  try {
    const stale = planCatalogReconciliation(current, rows(db));
    batch(db, buildTaskMutation("owner", b, [a, b], { ...donePatch, evidence: "Concurrent newer proof" }, now, "user-write"));
    batch(db, buildCatalogReconciliation("owner", stale, now, "stale-plan"));
    assert.equal(rows(db).find((row) => row.task_id === "B")?.evidence, "Concurrent newer proof");
    const retry = planCatalogReconciliation(current, rows(db));
    assert.equal(retry.length, 1);
    batch(db, buildCatalogReconciliation("owner", retry, now, "fresh-plan"));
    const result = mergeTaskStates(current, rows(db));
    assert.equal(result[1].status, "in_progress");
    assert.equal(result[1].evidence, "Concurrent newer proof");
    assert.equal(planCatalogReconciliation(current, rows(db)).length, 0);
  } finally { db.close(); }
});

test("definition snapshots participate in SQL CAS and dependency guards", () => {
  const a = makeTask("A", { status: "done", checks: [0, 1], evidence: "A proof" });
  const b = makeTask("B", { dependencies: ["A"] });
  const db = database([a, b]);
  try {
    const changedA = makeTask("A", { ...a, acceptance: [...a.acceptance, "New"] });
    // Equal row revision cannot make a different definition compatible.
    const wrongOwn = batch(db, buildTaskMutation("owner", changedA, [changedA, b], { ...donePatch, checks: [0, 1, 2] }, now, "own-schema"));
    assert.equal(wrongOwn[0].length, 0);
    const wrongDependency = batch(db, buildTaskMutation("owner", b, [changedA, b], donePatch, now, "dependency-schema"));
    assert.equal(wrongDependency[0].length, 0);
    assert.equal(db.prepare("SELECT COUNT(*) AS count FROM task_events").get()?.count, 0);
  } finally { db.close(); }
});

test("unknown legacy definitions fail closed instead of assigning new criteria to old checks", () => {
  const task = makeTask("UNKNOWN");
  const db = database([task]);
  try {
    db.exec("UPDATE task_state SET definition_json = NULL");
    assert.throws(() => planCatalogReconciliation([task], rows(db)), (error) => error instanceof TaskRequestError && error.status === 409);
  } finally { db.close(); }
});

// A small adapter executes the actual asynchronous D1 call sequence on SQLite;
// SQL is neither mocked nor reimplemented by this test.
function d1Database(db: DatabaseSync): D1Database {
  function execute(statement: SqlStatement) {
    const results = db.prepare(statement.sql).all(...statement.values);
    return { success: true, results, meta: { changes: db.prepare("SELECT changes() AS count").get()?.count ?? 0 } };
  }
  function prepare(sql: string, values: SqlStatement["values"] = []) {
    return {
      sql, values,
      bind(...bound: SqlStatement["values"]) { return prepare(sql, bound); },
      async all() { return execute({ sql, values }); },
    };
  }
  return {
    prepare,
    async batch(statements: SqlStatement[]) {
      db.exec("BEGIN");
      try {
        const results = statements.map(execute);
        db.exec("COMMIT");
        return results;
      } catch (error) { db.exec("ROLLBACK"); throw error; }
    },
  } as unknown as D1Database;
}

test("load and export reconcile legacy rows once while keeping original event meanings", async () => {
  const a = makeTask("FX-001", { ...legacyTaskDefinitions["FX-001"], status: "done", checks: [0, 1, 2], evidence: "Original source review", revision: 2 });
  const b = makeTask("FX-003", { ...legacyTaskDefinitions["FX-003"], status: "done", checks: [0, 1, 2], evidence: "Original license proof", revision: 3 });
  const updated = makeTask("FX-003", { ...b, acceptance: [...b.acceptance, "Additional terms review"] });
  const db = database([a, b]);
  try {
    db.exec("UPDATE task_state SET definition_json = NULL");
    db.prepare("INSERT INTO task_events (id,user_id,task_id,from_status,to_status,evidence,checks_json,revision,created_at) VALUES (?,?,?,?,?,?,?,?,?)")
      .run("original", "owner", b.id, "todo", "done", b.evidence, "[0,1,2]", 3, now);
    const adapter = d1Database(db);
    const tasks = await loadTaskStates(adapter, "owner", [a, updated]);
    assert.equal(tasks[0].status, "done");
    assert.equal(tasks[0].revision, 2);
    assert.equal(tasks[1].status, "in_progress");
    assert.equal(tasks[1].revision, 4);
    const exported = await exportTaskState(adapter, "owner", [a, updated]);
    assert.equal(exported.events.length, 2);
    const original = exported.events.find((event) => event.id === "original");
    assert.equal(original?.evidence, b.evidence);
    assert.equal(original?.definitionSource, "legacy-baseline");
    assert.deepEqual(original?.definition?.acceptance, b.acceptance);
    const revised = exported.events.find((event) => event.changeReason === "catalog_changed");
    assert.equal(revised?.definitionSource, "stored");
    assert.deepEqual(revised?.definition?.acceptance, updated.acceptance);
    assert.deepEqual(exported.tasks[1].checks, [0, 1, 2]);
    assert.equal(exported.tasks[1].evidence, b.evidence);
  } finally { db.close(); }
});
