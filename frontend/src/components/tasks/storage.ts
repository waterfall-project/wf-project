// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the tab keeps of the tasks it follows across a full reload: the reference of each task
 * that still runs, with what the user named it after — which the list of the tasks of a user
 * (`listBackgroundTasks`) does not say —, kept in the storage of the session of the tab
 * (`sessionStorage`), and read back when the shell mounts.
 *
 * Kept with care: only what names a running task still followed — its identifier, its kind, its status and
 * the subject the user typed —, read back only when it has that shape, and nothing is lost
 * but the follow-up when the storage is refused (a private window, a quota). A task that
 * ended is not kept: its end was announced. The command that started a task does not survive
 * a reload — a function is no data —: a task followed again after one cannot be relaunched
 * from the tracker, and the user starts it again from its screen. Signing out forgets them.
 */
import { RUNNING, type TaskKind, type TaskStatus, type TrackedTask } from "./tracking";

/** The key of the storage of the tab under which the tasks are kept. */
export const STORAGE_KEY = "wf_background_tasks";

/**
 * Every kind of task of the contract, to recognise one read back: a kind the contract adds
 * fails the type check until it is named here.
 */
const KINDS: Readonly<Record<TaskKind, true>> = {
  import_analysis: true,
  import_apply: true,
  revision_mark: true,
  structure_merge: true,
  risk_occurrence: true,
  export: true,
  backup: true,
  restore: true,
  directory_sync: true,
};

/** What is kept of a task. */
interface KeptTask {
  readonly key: string;
  readonly task_id: string;
  readonly kind: TaskKind;
  readonly status: TaskStatus;
  readonly subject?: string | undefined;
}

/** Whether a value read back is a task kept here, still running. */
function isKept(value: unknown): value is KeptTask {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const kept = value as Partial<Record<keyof KeptTask, unknown>>;
  return (
    typeof kept.key === "string" &&
    typeof kept.task_id === "string" &&
    typeof kept.kind === "string" &&
    Object.hasOwn(KINDS, kept.kind) &&
    typeof kept.status === "string" &&
    Object.hasOwn(RUNNING, kept.status) &&
    RUNNING[kept.status as TaskStatus] &&
    (kept.subject === undefined || typeof kept.subject === "string")
  );
}

/**
 * What the storage of the tab holds, as a list; nothing when the browser refuses the storage,
 * or when what it holds is not a list.
 */
function readKept(): unknown[] {
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

/** The tasks the tab followed before a reload, still running when it was left. */
export function restoreTasks(): TrackedTask[] {
  return readKept()
    .filter(isKept)
    .map(({ key, task_id, kind, status, subject }) => ({
      key,
      task: { task_id, kind, status },
      subject,
      command: undefined,
      outcome: undefined,
      interrupted: undefined,
    }));
}

/**
 * Whether a task is worth following again after a reload: it still runs, and the API has not
 * said it does not know it (404). One interrupted for want of a session (401) is kept: once
 * signed in again, a reload follows it on, and announces its end.
 */
function isResumable({ task, interrupted }: TrackedTask): boolean {
  return RUNNING[task.status] && interrupted?.problem.status !== 404;
}

/**
 * Forget the tasks kept for a reload: they are the session's that ends, not the tab's, and the
 * next user of the tab is to follow none of them.
 */
export function forgetTasks(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Refused — a private window —: nothing was kept.
  }
}

/** Keep the tasks worth following again, for a reload of the tab to follow them on. */
export function saveTasks(tasks: readonly TrackedTask[]): void {
  const kept: KeptTask[] = tasks.filter(isResumable).map(({ key, task, subject }) => ({
    key,
    task_id: task.task_id,
    kind: task.kind,
    status: task.status,
    subject,
  }));
  try {
    if (kept.length === 0) {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } else {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(kept));
    }
  } catch {
    // Refused — a quota, a private window —: the follow-up goes on, a reload loses it.
  }
}
