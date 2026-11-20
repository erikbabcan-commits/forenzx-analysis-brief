import { env } from "cloudflare:workers";
import { getChatGPTUser } from "@/app/chatgpt-auth";
import { initialTasks } from "@/lib/catalog";
import {
  loadTaskStates,
  privateJson,
  readTaskBody,
  requireSameOrigin,
  saveTaskState,
  taskErrorResponse,
  validateTaskUpdate,
} from "@/lib/task-state";

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const user = await getChatGPTUser();
    if (!user) return privateJson({ error: "Na uloženie zmeny sa prihlás cez ChatGPT." }, 401);
    requireSameOrigin(request);
    const { id } = await context.params;
    if (!initialTasks.some((task) => task.id === id)) return privateJson({ error: "Úloha neexistuje." }, 404);
    const body = await readTaskBody(request);
    if (!env.DB) throw new Error("D1 binding unavailable");
    const tasks = await loadTaskStates(env.DB, user.userId, initialTasks);
    const task = tasks.find((item) => item.id === id)!;
    const result = validateTaskUpdate(task, tasks, body);
    if (!result.ok) return privateJson({ error: result.error }, result.status);
    return privateJson({ task: await saveTaskState(env.DB, user.userId, task, tasks, result.patch) });
  } catch (error) {
    return taskErrorResponse(error);
  }
}
