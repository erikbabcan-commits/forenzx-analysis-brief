import { env } from "cloudflare:workers";
import { getChatGPTUser } from "@/app/chatgpt-auth";
import { initialTasks, meta, sources } from "@/lib/catalog";
import { loadTaskStates, privateJson, taskErrorResponse } from "@/lib/task-state";

export async function GET() {
  try {
    const user = await getChatGPTUser();
    if (!user) return privateJson({ error: "Na zobrazenie a ukladanie backlogu sa prihlás cez ChatGPT." }, 401);
    if (!env.DB) throw new Error("D1 binding unavailable");
    const tasks = await loadTaskStates(env.DB, user.userId, initialTasks);
    return privateJson({ tasks, sources, meta, syncedAt: new Date().toISOString() });
  } catch (error) {
    return taskErrorResponse(error);
  }
}
