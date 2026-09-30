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
 *
 * Each end — a task succeeded, failed, or whose follow-up the API interrupted — adds a line to
 * a log, which the shell reads out: the ends add up, none replaces the one before. Signing out
 * forgets them all.
 *
 * A task is followed from the screen that started it, from what the tab kept of it across a
 * reload, or from the list of the tasks of its user the API gives — started from another tab or
 * another workstation. Found so, it comes without the command that started it: failed, it is run
 * again from the screen of its object.
 */
import type { BackgroundTask, Outcome, Problem } from "@/api/problem";

/** Where a background task stands. */
export type TaskStatus = BackgroundTask["status"];

/** What a background task does. */
export type TaskKind = BackgroundTask["kind"];

/** How the follow-up of a task ended. */
export type EndKind = "succeeded" | "failed" | "interrupted";

/**
 * Whether a task still runs, and how it ended when it no longer does, for every status of the
 * contract: one the contract adds fails the type check until it is classified here.
 */
export const RUNNING: Readonly<Record<TaskStatus, boolean>> = {
  queued: true,
  running: true,
  succeeded: false,
  failed: false,
};
const ENDING: Readonly<Record<TaskStatus, EndKind | undefined>> = {
  queued: undefined,
  running: undefined,
  succeeded: "succeeded",
  failed: "failed",
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

/** A refusal of the API, as the decoder classes it. */
export type Refusal = Exclude<Outcome<unknown>, { kind: "done" } | { kind: "unreachable" }>;

/** A task the tracker follows. */
export interface TrackedTask {
  /** The task as it was first handed over: a relaunch keeps its place. */
  readonly key: string;
  readonly task: BackgroundTask;
  readonly subject: string | undefined;
  /** The command that started it; gone when running it again is bound to be refused. */
  readonly command: TaskCommand | undefined;
  /** The last relaunch refused, or the API out of reach at the last read: told as an alert. */
  readonly outcome: Outcome<unknown> | undefined;
  /** The refusal of the API to say where the task stands: its follow-up stops there. */
  readonly interrupted: Refusal | undefined;
}

/** A line of the log of ends. */
export interface EndLine {
  readonly id: number;
  readonly end: EndKind;
  readonly task: BackgroundTask;
  readonly subject: string | undefined;
  /** The motive of a failure, or the refusal that interrupted the follow-up. */
  readonly problem: Problem | undefined;
}

/** The tasks followed, and the log of their ends. */
export interface Tracking {
  readonly tasks: readonly TrackedTask[];
  readonly log: readonly EndLine[];
  /**
   * The tasks the user dismissed, by every identifier they went by: the list of the tasks of the
   * user, read again as the tab shows, does not bring them back.
   */
  readonly dismissed: readonly string[];
  /** Whether the tasks the tab followed before a reload are back: none is saved before. */
  readonly restored: boolean;
}

/** What changes what the tracker follows. */
export type TrackingEvent =
  | { readonly type: "track"; readonly task: BackgroundTask; readonly launch: Launch }
  | { readonly type: "restore"; readonly tasks: readonly TrackedTask[] }
  | { readonly type: "found"; readonly tasks: readonly BackgroundTask[] }
  | {
      readonly type: "answer";
      /** A read of the task's progress, or its command run again. */
      readonly source: "read" | "relaunch";
      readonly key: string;
      /** The task the answer was asked for. */
      readonly taskId: string;
      readonly outcome: Outcome<BackgroundTask>;
    }
  | { readonly type: "clear" | "dismiss"; readonly key: string }
  | { readonly type: "forget" };

/** Nothing followed yet. */
export const NOTHING_TRACKED: Tracking = { tasks: [], log: [], dismissed: [], restored: false };

/** How many ends the log keeps: the last ones, a reader has heard the others. */
const LOG_LENGTH = 10;

/**
 * Whether the tracker asks again where a task stands: while it runs, and until the API has
 * refused to say — the task unknown, the session gone. The API out of reach is asked again.
 */
export function isPolled({ task, interrupted }: TrackedTask): boolean {
  return RUNNING[task.status] && interrupted === undefined;
}

/** The log with one more end. */
function logged(
  log: readonly EndLine[],
  end: EndKind,
  { task, subject }: Pick<TrackedTask, "task" | "subject">,
  problem: Problem | undefined,
): readonly EndLine[] {
  const id = (log.at(-1)?.id ?? 0) + 1;
  return [...log, { id, end, task, subject, problem }].slice(-LOG_LENGTH);
}

/**
 * The log once a task gets a new state: one more end when it has just ended — it ran, or it
 * is a new task, a relaunch.
 */
function logEnd(log: readonly EndLine[], before: BackgroundTask, after: TrackedTask) {
  const end = ENDING[after.task.status];
  const ended = RUNNING[before.status] || before.task_id !== after.task.task_id;
  return end === undefined || !ended
    ? log
    : logged(log, end, after, after.task.problem ?? undefined);
}

/** The entry once an answer that is no task has come. */
function refused(
  entry: TrackedTask,
  source: "read" | "relaunch",
  outcome: Exclude<Outcome<BackgroundTask>, { kind: "done" }>,
): TrackedTask {
  if (outcome.kind === "unreachable") {
    return { ...entry, outcome };
  }
  if (source === "read") {
    // The API answered: an earlier "out of reach" no longer holds.
    return { ...entry, outcome: undefined, interrupted: outcome };
  }
  // A relaunch refused as stale would be refused again with the same version of the object:
  // the command goes, and the user starts the treatment again from the screen of the object.
  return { ...entry, outcome, command: outcome.kind === "stale" ? undefined : entry.command };
}

/** Apply the answer of a read or of a relaunch to the task it was asked for. */
function answer(state: Tracking, event: Extract<TrackingEvent, { type: "answer" }>): Tracking {
  const entry = state.tasks.find((tracked) => tracked.key === event.key);
  if (entry?.task.task_id !== event.taskId) {
    // Dismissed, or replaced by a relaunch since the question was asked.
    return state;
  }
  const { outcome, source } = event;
  const next: TrackedTask =
    outcome.kind === "done"
      ? { ...entry, task: outcome.data, outcome: undefined, interrupted: undefined }
      : refused(entry, source, outcome);
  const tasks = state.tasks.map((tracked) => (tracked === entry ? next : tracked));
  if (next.interrupted !== undefined && entry.interrupted === undefined) {
    return {
      ...state,
      tasks,
      log: logged(state.log, "interrupted", next, next.interrupted.problem),
    };
  }
  return { ...state, tasks, log: logEnd(state.log, entry.task, next) };
}

/**
 * What the tracker follows once the API has listed the tasks of its user: those it did not follow
 * yet, without their command — neither the one it follows under their first identifier, nor the
 * one a relaunch put in its place.
 */
function found(state: Tracking, tasks: readonly BackgroundTask[]): Tracking {
  const known = new Set([
    ...state.dismissed,
    ...state.tasks.flatMap((tracked) => [tracked.key, tracked.task.task_id]),
  ]);
  const added = tasks
    .filter((task) => !known.has(task.task_id))
    .map((task): TrackedTask => ({
      key: task.task_id,
      task,
      subject: undefined,
      command: undefined,
      outcome: undefined,
      interrupted: undefined,
    }));
  return added.length === 0 ? state : { ...state, tasks: [...state.tasks, ...added] };
}

/** Change what the tracker follows. */
export function tracking(state: Tracking, event: TrackingEvent): Tracking {
  switch (event.type) {
    case "track": {
      const { task, launch } = event;
      const key = task.task_id;
      const entry: TrackedTask = {
        key,
        task,
        subject: launch.subject,
        command: launch.command,
        outcome: undefined,
        interrupted: undefined,
      };
      const end = ENDING[task.status];
      return {
        ...state,
        tasks: [...state.tasks.filter((tracked) => tracked.key !== key), entry],
        log:
          end === undefined ? state.log : logged(state.log, end, entry, task.problem ?? undefined),
      };
    }
    case "restore": {
      const known = new Set(state.tasks.map((tracked) => tracked.key));
      const back = event.tasks.filter((tracked) => !known.has(tracked.key));
      // Nothing back, the same list: the shell above the page does not change (#173).
      const tasks = back.length === 0 ? state.tasks : [...back, ...state.tasks];
      return { ...state, tasks, restored: true };
    }
    case "found":
      return found(state, event.tasks);
    case "answer":
      return answer(state, event);
    case "clear":
      return {
        ...state,
        tasks: state.tasks.map((tracked) =>
          tracked.key === event.key ? { ...tracked, outcome: undefined } : tracked,
        ),
      };
    case "dismiss": {
      const gone = state.tasks.find((tracked) => tracked.key === event.key);
      return {
        ...state,
        tasks: state.tasks.filter((tracked) => tracked !== gone),
        dismissed:
          gone === undefined ? state.dismissed : [...state.dismissed, gone.key, gone.task.task_id],
      };
    }
    case "forget":
      // Signed out: nothing of the tasks of the session goes to the next user of the tab — an
      // answer still on its way finds no task to apply to.
      return { ...NOTHING_TRACKED, restored: state.restored };
  }
}
