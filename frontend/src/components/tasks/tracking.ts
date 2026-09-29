// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the tracker of the shell keeps of the background tasks it follows (WF-IHM-0080), and
 * how each event changes it: a task handed over with the command that started it, the answer
 * of a read of its progress, the answer of the command run again, the task dismissed.
 *
 * The follow-up is one for every kind of task — a marking, an import, a merge, a backup… —:
 * nothing here knows which operation started a task, only how to start it again. An answer
 * is applied to the task it was asked for, never to the one a relaunch put in its place.
 */
import type { BackgroundTask, Outcome } from "@/api/problem";

/** Where a background task stands. */
export type TaskStatus = BackgroundTask["status"];

/** What a background task does. */
export type TaskKind = BackgroundTask["kind"];

/**
 * Whether a task still runs, for every status of the contract: one the contract adds fails the
 * type check until it is classified here.
 */
export const RUNNING: Readonly<Record<TaskStatus, boolean>> = {
  queued: true,
  running: true,
  succeeded: false,
  failed: false,
};

/** The command that started a task, which starts the same treatment again when run. */
export type TaskCommand = () => Promise<Outcome<BackgroundTask>>;

/** What the screen that started a task hands over with it. */
export interface Launch {
  /** The command that started it; without one, a failed task cannot be run again. */
  readonly command?: TaskCommand | undefined;
  /** What the user named the task after — a version name —, shown as it was typed. */
  readonly subject?: string | undefined;
}

/** A task the tracker follows. */
export interface TrackedTask {
  /** The task as it was first handed over: a relaunch keeps its place. */
  readonly key: string;
  readonly task: BackgroundTask;
  readonly subject: string | undefined;
  readonly command: TaskCommand | undefined;
  /** The last read or relaunch that did not give a task back: a refusal, the API out of reach. */
  readonly outcome: Outcome<unknown> | undefined;
}

/** The tasks followed, and which one's end was last announced. */
export interface Tracking {
  readonly tasks: readonly TrackedTask[];
  readonly announced: string | undefined;
  /** Whether the tasks the tab followed before a reload are back: none is saved before. */
  readonly restored: boolean;
}

/** What changes what the tracker follows. */
export type TrackingEvent =
  | { readonly type: "track"; readonly task: BackgroundTask; readonly launch: Launch }
  | { readonly type: "restore"; readonly tasks: readonly TrackedTask[] }
  | {
      /** The answer of a read of the task's progress, or of its command run again. */
      readonly type: "answer";
      readonly key: string;
      /** The task the answer was asked for. */
      readonly taskId: string;
      readonly outcome: Outcome<BackgroundTask>;
    }
  | { readonly type: "clear" | "dismiss"; readonly key: string };

/** Nothing followed yet. */
export const NOTHING_TRACKED: Tracking = { tasks: [], announced: undefined, restored: false };

/**
 * Whether the tracker asks again where a task stands: while it runs, and until the API has
 * refused to say — the task unknown, the session gone. The API out of reach is asked again.
 */
export function isPolled({ task, outcome }: TrackedTask): boolean {
  return RUNNING[task.status] && (outcome === undefined || outcome.kind === "unreachable");
}

/**
 * The task announced once a task gets a new state: its own key when it has just ended — it ran,
 * or it is a new task, a relaunch —; nothing more of it when it runs again.
 */
function announcement(
  announced: string | undefined,
  key: string,
  before: BackgroundTask,
  after: BackgroundTask,
): string | undefined {
  if (!RUNNING[after.status]) {
    return RUNNING[before.status] || before.task_id !== after.task_id ? key : announced;
  }
  return announced === key ? undefined : announced;
}

/** Apply the answer of a read or of a relaunch to the task it was asked for. */
function answer(state: Tracking, event: Extract<TrackingEvent, { type: "answer" }>): Tracking {
  const entry = state.tasks.find((tracked) => tracked.key === event.key);
  if (entry?.task.task_id !== event.taskId) {
    // Dismissed, or replaced by a relaunch since the question was asked.
    return state;
  }
  const { outcome } = event;
  const next: TrackedTask =
    outcome.kind === "done"
      ? { ...entry, task: outcome.data, outcome: undefined }
      : { ...entry, outcome };
  return {
    ...state,
    tasks: state.tasks.map((tracked) => (tracked === entry ? next : tracked)),
    announced: announcement(state.announced, entry.key, entry.task, next.task),
  };
}

/** Change what the tracker follows. */
export function tracking(state: Tracking, event: TrackingEvent): Tracking {
  switch (event.type) {
    case "track": {
      const { task, launch } = event;
      const key = task.task_id;
      const entry = {
        key,
        task,
        subject: launch.subject,
        command: launch.command,
        outcome: undefined,
      };
      return {
        ...state,
        tasks: [...state.tasks.filter((tracked) => tracked.key !== key), entry],
        announced: RUNNING[task.status] ? state.announced : key,
      };
    }
    case "restore": {
      const known = new Set(state.tasks.map((tracked) => tracked.key));
      const back = event.tasks.filter((tracked) => !known.has(tracked.key));
      return { ...state, tasks: [...back, ...state.tasks], restored: true };
    }
    case "answer":
      return answer(state, event);
    case "clear":
      return {
        ...state,
        tasks: state.tasks.map((tracked) =>
          tracked.key === event.key ? { ...tracked, outcome: undefined } : tracked,
        ),
      };
    case "dismiss":
      return {
        ...state,
        tasks: state.tasks.filter((tracked) => tracked.key !== event.key),
        announced: state.announced === event.key ? undefined : state.announced,
      };
  }
}
