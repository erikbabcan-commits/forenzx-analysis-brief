import { env } from "cloudflare:workers";
import { getChatGPTUser } from "@/app/chatgpt-auth";
import { initialTasks, meta, sources } from "@/lib/catalog";
import { exportTaskState, privateJson, taskErrorResponse } from "@/lib/task-state";

export async function GET() {
  try {
    const user = await getChatGPTUser();
    if (!user) return privateJson({ error: "Na export backlogu sa prihlás cez ChatGPT." }, 401);
    if (!env.DB) throw new Error("D1 binding unavailable");
    const snapshot = await exportTaskState(env.DB, user.userId, initialTasks);
    const exportedAt = new Date().toISOString();
    return privateJson({ formatVersion: 1, exportedAt, syncedAt: exportedAt, meta, sources, ...snapshot }, 200, {
      "Content-Disposition": `attachment; filename="forenzx-backlog-${exportedAt.slice(0, 10)}.json"`,
    });
  } catch (error) {
    return taskErrorResponse(error);
  }
}
