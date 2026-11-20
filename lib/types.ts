export type TaskStatus = "todo" | "in_progress" | "blocked" | "done";
export type TaskPhase = "Základ" | "Integrácia" | "Kvalita" | "Balenie" | "Predaj";
export type Task = {
  id: string; title: string; phase: TaskPhase; priority: "P0" | "P1" | "P2";
  description: string; acceptance: string[]; dependencies: string[]; estimate: string;
  gate: boolean; sourceIds: string[]; status: TaskStatus; evidence: string;
  checks: number[]; revision: number; updatedAt: string | null;
  definitionKey: string;
};
export type Source = { id: string; title: string; organization: string; url: string; year: string; note: string };
export type TaskUpdate = { status: TaskStatus; evidence: string; checks: number[]; revision: number; definitionKey: string };

