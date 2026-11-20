import type { Task } from "./types";
import { definitionKey, parseDefinition, serializeDefinition, type TaskDefinition } from "./task-definition";
import { legacyTaskDefinitions } from "./legacy-task-definitions";

export const MAX_EVIDENCE_LENGTH = 4_000;
export const MAX_BODY_BYTES = 32_768;
const statuses = new Set(["todo", "in_progress", "blocked", "done"]);

export type TaskPatch = Pick<Task, "status" | "evidence" | "checks" | "revision">;
export type ValidationResult =
  | { ok: true; patch: TaskPatch }
  | { ok: false; status: number; error: string };

export type TaskStateRow = {
  task_id: string;
  status: Task["status"];
  evidence: string;
  checks_json: string;
  revision: number;
  updated_at: string | null;
  definition_json: string | null;
};

type EventRow = {
  id: string;
  task_id: string;
  from_status: Task["status"];
  to_status: Task["status"];
  evidence: string;
  checks_json: string;
  revision: number;
  created_at: string;
  definition_json: string | null;
  change_reason: string;
};

export type SqlStatement = { sql: string; values: (string | number | null)[] };

export class TaskRequestError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "TaskRequestError";
  }
}

export function completedDependents(taskId: string, tasks: Task[]): Task[] {
  const dependentIds = new Set<string>();
  const queue = [taskId];
  while (queue.length) {
    const prerequisite = queue.shift()!;
    for (const task of tasks) {
      if (task.id !== taskId && task.dependencies.includes(prerequisite) && !dependentIds.has(task.id)) {
        dependentIds.add(task.id);
        queue.push(task.id);
      }
    }
  }
  return tasks.filter((task) => dependentIds.has(task.id) && task.status === "done");
}

function allDependentIds(taskId: string, tasks: Task[]): string[] {
  return completedDependents(taskId, tasks.map((task) => ({ ...task, status: "done" }))).map((task) => task.id);
}

export function validateTaskUpdate(task: Task, tasks: Task[], input: unknown): ValidationResult {
  const invalid = (error: string, status = 400): ValidationResult => ({ ok: false, status, error });
  if (!input || typeof input !== "object" || Array.isArray(input)) return invalid("Neplatné údaje úlohy.");
  const body = input as Record<string, unknown>;
  if (Object.keys(body).some((key) => !["status", "evidence", "checks", "revision", "definitionKey"].includes(key))) {
    return invalid("Požiadavka obsahuje nepodporované polia.");
  }
  if (body.definitionKey !== definitionKey(task)) {
    return invalid("Podmienky úlohy sa zmenili. Obnov údaje a skontroluj aktuálne kritériá.", 409);
  }
  if (typeof body.status !== "string" || !statuses.has(body.status)) return invalid("Neplatný stav úlohy.");
  if (typeof body.evidence !== "string" || body.evidence.length > MAX_EVIDENCE_LENGTH) {
    return invalid(`Dôkaz musí byť text s najviac ${MAX_EVIDENCE_LENGTH} znakmi.`);
  }
  if (!Number.isSafeInteger(body.revision) || (body.revision as number) < 0) return invalid("Neplatná revízia úlohy.");
  if (body.revision !== task.revision) {
    return invalid("Úloha sa medzitým zmenila. Obnov údaje a skús uloženie znova.", 409);
  }
  if (
    !Array.isArray(body.checks) ||
    body.checks.length > task.acceptance.length ||
    body.checks.some((item) => !Number.isInteger(item) || item < 0 || item >= task.acceptance.length) ||
    new Set(body.checks).size !== body.checks.length
  ) {
    return invalid("Neplatný zoznam splnených podmienok.");
  }

  const patch: TaskPatch = {
    status: body.status as Task["status"],
    evidence: body.evidence.trim(),
    checks: [...body.checks].sort((a, b) => a - b),
    revision: body.revision as number,
  };
  if (patch.status === "done") {
    if (patch.checks.length !== task.acceptance.length) return invalid("Najprv potvrď všetky podmienky dokončenia.");
    if (!patch.evidence) return invalid("Dokončená úloha potrebuje odkaz alebo poznámku s dôkazom.");
    const missing = task.dependencies.filter((id) => tasks.find((candidate) => candidate.id === id)?.status !== "done");
    if (missing.length) return invalid(`Najprv dokonči závislosti: ${missing.join(", ")}.`, 409);
  }
  if (patch.status !== "done") {
    const dependents = completedDependents(task.id, tasks);
    if (dependents.length) {
      return invalid(`Najprv znovu otvor nadväzujúce dokončené úlohy: ${dependents.map((item) => item.id).join(", ")}.`, 409);
    }
  }
  return { ok: true, patch };
}

export function requireSameOrigin(request: Request): void {
  const origin = request.headers.get("origin");
  let validOrigin = false;
  try {
    validOrigin = origin !== null && new URL(origin).origin === new URL(request.url).origin;
  } catch {
    validOrigin = false;
  }
  if (!validOrigin || request.headers.get("sec-fetch-site") === "cross-site") {
    throw new TaskRequestError(403, "Zmeny povoľujeme iba z tohto dashboardu. Obnov stránku a skús znova.");
  }
}

export async function readTaskBody(request: Request): Promise<unknown> {
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    throw new TaskRequestError(415, "Požiadavka musí obsahovať JSON.");
  }
  if (Number(request.headers.get("content-length") || 0) > MAX_BODY_BYTES) {
    throw new TaskRequestError(413, "Požiadavka je príliš veľká.");
  }
  const reader = request.body?.getReader();
  if (!reader) throw new TaskRequestError(400, "Chýbajú údaje úlohy.");
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_BODY_BYTES) {
        await reader.cancel();
        throw new TaskRequestError(413, "Požiadavka je príliš veľká.");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new TaskRequestError(400, "Neplatný JSON v požiadavke.");
  }
}

export function mergeTaskStates(initialTasks: Task[], rows: TaskStateRow[]): Task[] {
  const states = new Map(rows.map((row) => [row.task_id, row]));
  return initialTasks.map((task) => {
    const row = states.get(task.id);
    if (!row) return { ...task, checks: [...task.checks], definitionKey: definitionKey(task) };
    if (row.definition_json !== serializeDefinition(task)) {
      throw new TaskRequestError(409, "Katalóg sa medzitým zmenil. Obnov údaje pred ďalším uložením.");
    }
    const checks: unknown = JSON.parse(row.checks_json);
    if (!Array.isArray(checks) || checks.some((value) => !Number.isInteger(value) || value < 0 || value >= task.acceptance.length) || new Set(checks).size !== checks.length) {
      throw new Error("Invalid stored acceptance state");
    }
    return {
      ...task,
      status: row.status,
      evidence: row.evidence,
      checks: checks as number[],
      revision: row.revision,
      updatedAt: row.updated_at,
      definitionKey: definitionKey(task),
    };
  });
}

export async function seedTaskStates(database: D1Database, userId: string, initialTasks: Task[]): Promise<void> {
  const statements = initialTasks.map((task) => database.prepare(
    "INSERT OR IGNORE INTO task_state (user_id, task_id, status, evidence, checks_json, revision, updated_at, definition_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
  ).bind(userId, task.id, task.status, task.evidence, JSON.stringify(task.checks), task.revision, task.updatedAt, serializeDefinition(task)));
  if (statements.length) await database.batch(statements);
}

const stateQuery = "SELECT task_id, status, evidence, checks_json, revision, updated_at, definition_json FROM task_state WHERE user_id = ?";
const legacyDefinitions: Record<string, TaskDefinition> = legacyTaskDefinitions;

export type CatalogChange = {
  row: TaskStateRow;
  task: Task;
  checks: number[];
  status: Task["status"];
  reason: "catalog_changed" | "dependency_reopened" | "state_revalidation" | null;
};

// Build a plan without changing user data. Legacy indices are interpreted only
// against the immutable definitions actually shipped before snapshots existed.
export function planCatalogReconciliation(initialTasks: Task[], rows: TaskStateRow[]): CatalogChange[] {
  const byId = new Map(rows.map((row) => [row.task_id, row]));
  const candidates = initialTasks.map((task): CatalogChange => {
    const row = byId.get(task.id);
    if (!row) throw new Error("Missing seeded task state");
    const previous = row.definition_json === null ? legacyDefinitions[task.id] : parseDefinition(row.definition_json);
    if (!previous) throw new TaskRequestError(409, "Pôvodné kritériá úlohy sa nedajú overiť. Je potrebné posúdenie histórie katalógu.");
    const previousChecks: unknown = JSON.parse(row.checks_json);
    if (!Array.isArray(previousChecks) || previousChecks.some((index) => !Number.isInteger(index) || index < 0 || index >= previous.acceptance.length) || new Set(previousChecks).size !== previousChecks.length) {
      throw new Error("Invalid stored acceptance state");
    }
    const changed = serializeDefinition(previous) !== serializeDefinition(task);
    const checkedText = new Set(previousChecks.map((index) => previous.acceptance[index]));
    const checks = task.acceptance.flatMap((text, index) => checkedText.has(text) ? [index] : []);
    let status = row.status;
    let reason: CatalogChange["reason"] = changed ? "catalog_changed" : null;
    if (status === "done" && (changed || checks.length !== task.acceptance.length || !row.evidence.trim())) {
      status = "in_progress";
      reason ??= "state_revalidation";
    }
    return { row, task, checks, status, reason };
  });
  // Re-open the transitive dependent closure in the same transaction. Their
  // own checkboxes and evidence stay intact, but completion needs new review.
  for (let pass = 0; pass < candidates.length; pass++) {
    let changed = false;
    for (const candidate of candidates) {
      if (candidate.status === "done" && candidate.task.dependencies.some((id) => candidates.find((item) => item.task.id === id)?.status !== "done")) {
        candidate.status = "in_progress";
        candidate.reason ??= "dependency_reopened";
        changed = true;
      }
    }
    if (!changed) break;
  }
  return candidates.filter((candidate) => candidate.reason !== null || candidate.row.definition_json !== serializeDefinition(candidate.task));
}

function historyStatement(userId: string, taskId: string, fromStatus: Task["status"], mutationId: string, reason = "user_update"): SqlStatement {
  return {
    sql: "INSERT INTO task_events (id, user_id, task_id, from_status, to_status, evidence, checks_json, revision, created_at, definition_json, change_reason) SELECT ?, user_id, task_id, ?, status, evidence, checks_json, revision, updated_at, definition_json, ? FROM task_state WHERE user_id = ? AND task_id = ? AND last_mutation_id = ?",
    values: [mutationId, fromStatus, reason, userId, taskId, mutationId],
  };
}

export function buildCatalogReconciliation(userId: string, changes: CatalogChange[], now: string, mutationPrefix: string): SqlStatement[] {
  return changes.flatMap((change, index) => {
    const serialized = serializeDefinition(change.task);
    if (change.reason === null) {
      // Attaching unchanged legacy metadata is not a new user decision: keep
      // its revision, timestamps and history untouched.
      return [{
        sql: "UPDATE task_state SET definition_json = ? WHERE user_id = ? AND task_id = ? AND revision = ? AND definition_json IS ?",
        values: [serialized, userId, change.task.id, change.row.revision, change.row.definition_json],
      }];
    }
    const mutationId = `${mutationPrefix}:${index}`;
    return [
      {
        sql: "UPDATE task_state SET status = ?, checks_json = ?, definition_json = ?, revision = revision + 1, updated_at = ?, last_mutation_id = ? WHERE user_id = ? AND task_id = ? AND revision = ? AND definition_json IS ? RETURNING task_id",
        values: [change.status, JSON.stringify(change.checks), serialized, now, mutationId, userId, change.task.id, change.row.revision, change.row.definition_json],
      },
      historyStatement(userId, change.task.id, change.row.status, mutationId, change.reason),
    ];
  });
}

export async function loadTaskStates(database: D1Database, userId: string, initialTasks: Task[]): Promise<Task[]> {
  await seedTaskStates(database, userId, initialTasks);
  for (let attempt = 0; attempt < 4; attempt++) {
    const result = await database.prepare(stateQuery).bind(userId).all<TaskStateRow>();
    const changes = planCatalogReconciliation(initialTasks, result.results);
    if (!changes.length) return mergeTaskStates(initialTasks, result.results);
    if (attempt === 3) break;
    const statements = buildCatalogReconciliation(userId, changes, new Date().toISOString(), crypto.randomUUID());
    // D1 batch is atomic. CAS protects notes/checks if another request wrote
    // after our read. A new read verifies the entire dependency graph again.
    await database.batch(statements.map((statement) => database.prepare(statement.sql).bind(...statement.values)));
  }
  throw new TaskRequestError(409, "Katalóg alebo úlohy sa súbežne menia. Obnov údaje a skús znova.");
}

// Dependency guards live in SQL as well as validation: another tab could
// change a different task between validation and this atomic mutation.
export function buildTaskMutation(
  userId: string,
  task: Task,
  tasks: Task[],
  patch: TaskPatch,
  now: string,
  mutationId: string,
): [SqlStatement, SqlStatement] {
  let sql = "UPDATE task_state SET status = ?, evidence = ?, checks_json = ?, revision = revision + 1, updated_at = ?, last_mutation_id = ? WHERE user_id = ? AND task_id = ? AND revision = ? AND definition_json = ?";
  const values: SqlStatement["values"] = [patch.status, patch.evidence, JSON.stringify(patch.checks), now, mutationId, userId, task.id, patch.revision, serializeDefinition(task)];
  if (patch.status === "done" && task.dependencies.length) {
    for (const id of task.dependencies) {
      const dependency = tasks.find((candidate) => candidate.id === id);
      if (!dependency) throw new TaskRequestError(409, "Chýba závislosť úlohy.");
      sql += " AND EXISTS (SELECT 1 FROM task_state AS dependency WHERE dependency.user_id = ? AND dependency.task_id = ? AND dependency.status = 'done' AND dependency.definition_json = ?)";
      values.push(userId, id, serializeDefinition(dependency));
    }
  }
  const dependentIds = allDependentIds(task.id, tasks);
  if (patch.status !== "done" && dependentIds.length) {
    const placeholders = dependentIds.map(() => "?").join(", ");
    sql += ` AND NOT EXISTS (SELECT 1 FROM task_state AS dependent WHERE dependent.user_id = ? AND dependent.task_id IN (${placeholders}) AND dependent.status = 'done')`;
    values.push(userId, ...dependentIds);
  }
  sql += " RETURNING task_id, status, evidence, checks_json, revision, updated_at, definition_json";
  return [
    { sql, values },
    historyStatement(userId, task.id, task.status, mutationId),
  ];
}

export async function saveTaskState(
  database: D1Database,
  userId: string,
  task: Task,
  tasks: Task[],
  patch: TaskPatch,
): Promise<Task> {
  const statements = buildTaskMutation(userId, task, tasks, patch, new Date().toISOString(), crypto.randomUUID());
  const results = await database.batch<TaskStateRow>(statements.map((statement) => database.prepare(statement.sql).bind(...statement.values)));
  const row = results[0].results[0];
  if (results[0].meta.changes !== 1 || !row) {
    throw new TaskRequestError(409, "Úloha alebo jej závislosti sa medzitým zmenili. Obnov údaje pred ďalším uložením.");
  }
  return mergeTaskStates([task], [row])[0];
}

export async function exportTaskState(database: D1Database, userId: string, initialTasks: Task[]) {
  await loadTaskStates(database, userId, initialTasks);
  const results = await database.batch([
    database.prepare(stateQuery).bind(userId),
    database.prepare("SELECT id, task_id, from_status, to_status, evidence, checks_json, revision, created_at, definition_json, change_reason FROM task_events WHERE user_id = ? ORDER BY created_at, id").bind(userId),
  ]);
  return {
    tasks: mergeTaskStates(initialTasks, results[0].results as TaskStateRow[]),
    events: (results[1].results as EventRow[]).map((event) => ({
      id: event.id,
      taskId: event.task_id,
      fromStatus: event.from_status,
      toStatus: event.to_status,
      evidence: event.evidence,
      checks: JSON.parse(event.checks_json) as number[],
      revision: event.revision,
      createdAt: event.created_at,
      definition: event.definition_json ? parseDefinition(event.definition_json) : legacyDefinitions[event.task_id] ?? null,
      definitionSource: event.definition_json ? "stored" : legacyDefinitions[event.task_id] ? "legacy-baseline" : "unavailable",
      changeReason: event.change_reason,
    })),
  };
}

export function privateJson(data: unknown, status = 200, extraHeaders: Record<string, string> = {}): Response {
  return Response.json(data, {
    status,
    headers: { "Cache-Control": "private, no-store, max-age=0", Vary: "Cookie", ...extraHeaders },
  });
}

export function taskErrorResponse(error: unknown): Response {
  if (error instanceof TaskRequestError) return privateJson({ error: error.message }, error.status);
  return privateJson({ error: "Zdieľané úložisko momentálne nie je dostupné. Zmena nebola potvrdená; obnov stránku a skús to znova." }, 503);
}
