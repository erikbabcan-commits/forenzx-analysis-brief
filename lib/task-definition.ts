import { createHash } from "node:crypto";
import type { Task } from "./types";

export type TaskDefinition = Pick<Task, "acceptance" | "dependencies">;

export function serializeDefinition(definition: TaskDefinition): string {
  if (!definition.acceptance.length || new Set(definition.acceptance).size !== definition.acceptance.length) {
    throw new Error("Acceptance criteria must be nonempty and unique");
  }
  return JSON.stringify({ acceptance: definition.acceptance, dependencies: [...definition.dependencies].sort() });
}

export function parseDefinition(value: string): TaskDefinition {
  const definition: unknown = JSON.parse(value);
  if (!definition || typeof definition !== "object" || Array.isArray(definition)) throw new Error("Invalid stored task definition");
  const record = definition as Record<string, unknown>;
  if (
    Object.keys(record).some((key) => !["acceptance", "dependencies"].includes(key)) ||
    !Array.isArray(record.acceptance) || !record.acceptance.length ||
    record.acceptance.some((item) => typeof item !== "string") ||
    new Set(record.acceptance).size !== record.acceptance.length ||
    !Array.isArray(record.dependencies) || record.dependencies.some((item) => typeof item !== "string") ||
    new Set(record.dependencies).size !== record.dependencies.length
  ) throw new Error("Invalid stored task definition");
  return record as TaskDefinition;
}

// Identifies requirements, not an authorization credential. Only the API needs
// node:crypto; the browser echoes the key returned with its loaded task.
export function definitionKey(definition: TaskDefinition): string {
  return createHash("sha256").update(serializeDefinition(definition)).digest("hex");
}
