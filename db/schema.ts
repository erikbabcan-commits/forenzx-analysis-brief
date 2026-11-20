import { index, integer, primaryKey, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

export const taskState = sqliteTable(
  "task_state",
  {
    userId: text("user_id").notNull(),
    taskId: text("task_id").notNull(),
    status: text("status", { enum: ["todo", "in_progress", "blocked", "done"] }).notNull(),
    evidence: text("evidence").notNull().default(""),
    checksJson: text("checks_json").notNull().default("[]"),
    revision: integer("revision").notNull().default(0),
    updatedAt: text("updated_at"),
    lastMutationId: text("last_mutation_id"),
  },
  (table) => [primaryKey({ columns: [table.userId, table.taskId] })],
);

// Application routes only append events. There is intentionally no history
// modification or deletion route. This is change history, not a WORM audit log.
export const taskEvents = sqliteTable(
  "task_events",
  {
    id: text("id").primaryKey(),
    userId: text("user_id").notNull(),
    taskId: text("task_id").notNull(),
    fromStatus: text("from_status").notNull(),
    toStatus: text("to_status").notNull(),
    evidence: text("evidence").notNull(),
    checksJson: text("checks_json").notNull(),
    revision: integer("revision").notNull(),
    createdAt: text("created_at").notNull(),
  },
  (table) => [
    index("task_events_user_time").on(table.userId, table.createdAt),
    uniqueIndex("task_events_user_task_revision").on(table.userId, table.taskId, table.revision),
  ],
);
