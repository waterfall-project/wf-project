// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the tracker of the shell keeps of the background tasks it follows (WF-IHM-0080), and
 * how each event changes it: a task handed over with the command that started it, the answer
 * of a read of its progress — or of the read that checks its result is still there before it is
 * downloaded (#329) —, the answer of the command run again, the task dismissed.
 *
 * The follow-up is one for every kind of task — a marking, an import, a merge, a backup… —:
 * nothing here knows which operation started a task, only how to start it again. An answer
 * is applied to the task it was asked for, never to the one a relaunch put in its place.
 *
 * Each end — a task succeeded, failed, or whose follow-up the API interrupted — adds a line to
 * a log, which the shell reads out: the ends add up, none replaces the one before. A success or a
 * failure adds a card too, which the shell floats in the corner of the window until it is opened or
 * closed (`end-cards.tsx`): the file of an export downloaded by itself, its card no longer offers it
 * — served once (WF-DAT-0120) —; refused, its card tells why. Signing out forgets them all.
 *
 * A task is followed from the screen that started it, from what the tab kept of it across a
 * reload, or from the list of the tasks of its user the API gives — started from another tab or
 * another workstation. Found so, it comes without the command that started it: failed, it is run
 * again from the screen of its object.
 */
import type { BackgroundTask, Outcome, Problem } from "@/api/problem";
import type { MessageScreen } from "@/components/notices/message-history";

import type { ResultRefusal } from "./result-refusal";

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

/**
 * Whether the result of a task is a file to download (`getBackgroundTaskResult`), for every kind of
 * the contract: an export's alone. Another gives its result to read where its object shows — the
 * report of a reading of the accounts on the screen of the accounts, a backup in their list —, and
 * the entry offers to read the screen anew, never to download it. A kind the contract adds fails the
 * type check until it is classified here.
 */
const FILE_RESULT: Readonly<Record<TaskKind, boolean>> = {
  import_analysis: false,
  import_apply: false,
  revision_mark: false,
  structure_merge: false,
  risk_occurrence: false,
  export: true,
  backup: false,
  restore: false,
  identity_sync: false,
};

/**
 * Whether the tracker of the shell follows a kind of task, for every kind of the contract: all
 * but the restoration, which is followed by the screen of its maintenance alone — where every
 * operation answers 503 while it runs, which the shell would read again all along (#2263). A kind
 * the contract adds fails the type check until it is classified here.
 */
const FOLLOWED: Readonly<Record<TaskKind, boolean>> = {
  import_analysis: true,
  import_apply: true,
  revision_mark: true,
  structure_merge: true,
  risk_occurrence: true,
  export: true,
  backup: true,
  restore: false,
  identity_sync: true,
};

/** Whether a task has succeeded with a file to download: the entry offers it. */
export function givesFile(task: BackgroundTask): boolean {
  return task.status === "succeeded" && task.result_url != null && FILE_RESULT[task.kind];
}

/** The command that started a task, which starts the same treatment again when run. */
export type TaskCommand = () => Promise<Outcome<BackgroundTask>>;

/** What the screen that started a task hands over with it. */
export interface Launch {
  /** The command that started it; without one, a failed task cannot be run again. */
  readonly command?: TaskCommand | undefined;
  /** What the user named the task after — a version name —, shown as it was typed. */
  readonly subject?: string | undefined;
  /** The screen it was started from, which the history of the messages leads back to. */
  readonly from?: MessageScreen | undefined;
  /**
   * What the button that started it aims at, as `taskAim` composes it: the button mounted again —
   * the tab reloaded, the screen left and come back to — finds the task by it (`useRunningTask`).
   */
  readonly aim?: string | undefined;
}

/**
 * The key a button finds again the task it started by, once mounted anew (#3404): the kind of the
 * task and what it aims at — the revision marked or exported, the project of an import, the
 * installation for a backup —, which the contract does not say of a task (`BackgroundTaskRef`).
 */
export function taskAim(kind: TaskKind, ...object: readonly [string, ...string[]]): string {
  return [kind, ...object].join("/");
}

/** What a task over the whole installation aims at — a backup, a reading of the accounts. */
export const INSTALLATION = "installation";

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
  /** The screen it was started from; none for a task found again, its screen unknown. */
  readonly from?: MessageScreen | undefined;
  /** What the button that started it aims at (`taskAim`); none for a task the API listed. */
  readonly aim?: string | undefined;
  /** The last relaunch refused, or the API out of reach at the last read: told as an alert. */
  readonly outcome: Outcome<unknown> | undefined;
  /** The refusal of the API to say where the task stands: its follow-up stops there. */
  readonly interrupted: Refusal | undefined;
  /**
   * Whether the read before a download found the task without a result (`result_url` none): the
   * result is no longer available, which the entry says in place of the offer to download it.
   */
  readonly resultUnavailable?: boolean | undefined;
  /**
   * Whether the progress of `task` is a placeholder: a task found again after a reload, which
   * keeps no progress, shows a bar without a value until the first read replaces it.
   */
  readonly progressUnknown?: boolean | undefined;
}

/** A line of the log of ends. */
export interface EndLine {
  readonly id: number;
  /** The key the task is followed under: its first identifier, which a relaunch keeps. */
  readonly key: string;
  readonly end: EndKind;
  readonly task: BackgroundTask;
  readonly subject: string | undefined;
  readonly from?: MessageScreen | undefined;
  /** The motive of a failure, or the refusal that interrupted the follow-up. */
  readonly problem: Problem | undefined;
}

/** The card of an end: the line of the log, and what became of the file it offers. */
export interface EndCardLine extends EndLine {
  /** Whether the file was downloaded by itself: served once (WF-DAT-0120), the card no longer offers it. */
  readonly delivered?: boolean | undefined;
  /** What the route of the result refused when the file was to download by itself: the card tells it. */
  readonly refusal?: ResultRefusal | undefined;
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
  /**
   * The refusal of a result the browser came back with, whose task could not be read again: told
   * by the panel itself, no entry being there to tell it (#416).
   */
  readonly refusedResult?: ResultRefusal | undefined;
  /**
   * The ends the floating cards of the shell show — each success and failure, never a follow-up
   * interrupted, which says nothing of the task —, the last first: each stays until it is opened or
   * closed, whatever the log has kept since.
   */
  readonly cards: readonly EndCardLine[];
}

/** What changes what the tracker follows. */
export type TrackingEvent =
  | { readonly type: "track"; readonly task: BackgroundTask; readonly launch: Launch }
  | { readonly type: "restore"; readonly tasks: readonly TrackedTask[] }
  | { readonly type: "found"; readonly tasks: readonly BackgroundTask[] }
  | {
      readonly type: "answer";
      /**
       * A read of the task's progress; the read that checks its result before a download, or the
       * read of the result itself, whose refusal is told in place (#416); or its command run again.
       */
      readonly source: "read" | "relaunch" | "download";
      readonly key: string;
      /** The task the answer was asked for. */
      readonly taskId: string;
      readonly outcome: Outcome<BackgroundTask>;
    }
  | { readonly type: "clear" | "dismiss"; readonly key: string }
  | { readonly type: "forget" }
  | { readonly type: "result_refused"; readonly refusal: ResultRefusal }
  | { readonly type: "result_refusal_cleared" }
  /** The card of an end opened or closed, by the identifier of its line. */
  | { readonly type: "card_closed"; readonly id: number }
  /** The file of the card of an end downloaded by itself, by the identifier of its line. */
  | { readonly type: "card_delivered"; readonly id: number }
  /**
   * The file of the card of an end refused when it was to download by itself, by the identifier of
   * its line — and the task it ended, whose entry tells the refusal when the card is closed already.
   */
  | {
      readonly type: "card_refused";
      readonly id: number;
      readonly key: string;
      readonly taskId: string;
      readonly refusal: ResultRefusal;
    };

/** The events that change the cards alone. */
type CardEvent = Extract<
  TrackingEvent,
  { type: "card_closed" | "card_delivered" | "card_refused" }
>;

/** Nothing followed yet. */
export const NOTHING_TRACKED: Tracking = {
  tasks: [],
  log: [],
  dismissed: [],
  restored: false,
  cards: [],
};

/** How many ends the log keeps: the last ones, a reader has heard the others. */
const LOG_LENGTH = 10;

/**
 * Whether the tracker asks again where a task stands: while it runs, and until the API has
 * refused to say — the task unknown, the session gone. The API out of reach is asked again.
 */
export function isPolled({ task, interrupted }: TrackedTask): boolean {
  return RUNNING[task.status] && interrupted === undefined;
}

/** The project an address is of: the segment after `/projects/`, none outside a project. */
function projectOf(path: string): string | undefined {
  return /^\/projects\/([^/?#]+)/.exec(path)?.[1];
}

/**
 * Whether the screen shown — its path — is read anew once a task has ended (#3103): a task that
 * succeeded or failed, never a follow-up interrupted, which says nothing of the task; started from a
 * screen of the same project — the revisions after a marking, the imports after an import —, or,
 * outside a project, from the same screen — a backup. A task found again, its screen unknown, reads
 * nothing anew.
 */
export function readsAnew({ end, from }: Pick<EndLine, "end" | "from">, shown: string): boolean {
  if (end === "interrupted" || from === undefined) {
    return false;
  }
  const started = from.href.split(/[?#]/, 1)[0] ?? "";
  const project = projectOf(started);
  return project === undefined ? started === shown : project === projectOf(shown);
}

/** The log with one more end, kept whole: `tracking` keeps its last lines once the cards are made. */
function logged(
  log: readonly EndLine[],
  end: EndKind,
  { key, task, subject, from }: Pick<TrackedTask, "key" | "task" | "subject" | "from">,
  problem: Problem | undefined,
): readonly EndLine[] {
  const id = (log.at(-1)?.id ?? 0) + 1;
  return [...log, { id, key, end, task, subject, from, problem }];
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

/** The statuses of a refused read that stop the follow-up: the task unknown, the session gone. */
const ENDS_FOLLOW_UP: ReadonlySet<number> = new Set([401, 404]);

/** The entry once an answer that is no task has come. */
function refused(
  entry: TrackedTask,
  source: "read" | "relaunch" | "download",
  answered: Exclude<Outcome<BackgroundTask>, { kind: "done" }>,
): TrackedTask {
  // A read says the task gone or the session lost by a 404 or a 401 alone; any other refusal — a
  // 500, a 503 while the database or Redis is down, a status the contract does not declare — is a
  // passing failure, taken as the API out of reach: asked again later, told once (#2257).
  const outcome: typeof answered =
    source === "read" &&
    answered.kind !== "unreachable" &&
    !ENDS_FOLLOW_UP.has(answered.problem.status)
      ? { kind: "unreachable" }
      : answered;
  if (
    source === "read" &&
    outcome.kind === "unreachable" &&
    entry.outcome?.kind === "unreachable"
  ) {
    // Out of reach again at a read: the same refusal, the one already told and noted in the
    // history — a read every few seconds while the API is out of reach notes it once, until a read
    // is answered: the entry stays as it was, and the follow-up asks again a while later all the
    // same, as it does after any answer (`usePolling`); a relaunch the user presses is told anew.
    return entry;
  }
  if (outcome.kind === "unreachable" || source === "download") {
    // Told in place, by the notice of the entry: the follow-up of the task is not interrupted —
    // a result gone, a session lost say nothing of a task that has ended.
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

/** Whether two readings of a task say the same of it: the API gives them as plain data. */
function unchanged(before: TrackedTask, after: BackgroundTask): boolean {
  return (
    before.outcome === undefined &&
    before.interrupted === undefined &&
    before.progressUnknown !== true &&
    JSON.stringify(before.task) === JSON.stringify(after)
  );
}

/**
 * Apply the answer of a read or of a relaunch to the task it was asked for. A read that finds
 * the task where it stood changes nothing, not even the list: what the tab keeps is not written
 * again, and nothing is rendered again (#180).
 */
function answer(state: Tracking, event: Extract<TrackingEvent, { type: "answer" }>): Tracking {
  const entry = state.tasks.find((tracked) => tracked.key === event.key);
  if (entry?.task.task_id !== event.taskId) {
    // Dismissed, or replaced by a relaunch since the question was asked.
    return state;
  }
  const { outcome, source } = event;
  if (outcome.kind === "done" && unchanged(entry, outcome.data)) {
    return state;
  }
  const next: TrackedTask =
    outcome.kind === "done"
      ? {
          ...entry,
          task: outcome.data,
          outcome: undefined,
          interrupted: undefined,
          progressUnknown: false,
          resultUnavailable: source === "download" && outcome.data.result_url == null,
        }
      : refused(entry, source, outcome);
  if (next === entry) {
    return state;
  }
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
    .filter((task) => FOLLOWED[task.kind] && !known.has(task.task_id))
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

/**
 * The cards once the log has changed: one more, on top, for each success or failure logged since —
 * a follow-up interrupted has none —, then the log cut to its last lines: ends logged at once beyond
 * them each have their card all the same.
 */
function carded(before: Tracking, after: Tracking): Tracking {
  if (after.log === before.log) {
    return after;
  }
  const last = before.log.at(-1)?.id ?? 0;
  const fresh = after.log.filter((line) => line.id > last && line.end !== "interrupted");
  const log = after.log.length > LOG_LENGTH ? after.log.slice(-LOG_LENGTH) : after.log;
  return {
    ...after,
    log,
    cards: fresh.length === 0 ? after.cards : [...fresh.toReversed(), ...after.cards],
  };
}

/** The cards once one of them is changed: closed, its file delivered or refused. */
function cardChanged(state: Tracking, event: CardEvent): Tracking {
  const card = state.cards.find((each) => each.id === event.id);
  if (card === undefined) {
    // Closed already: a refusal is told by the entry of the task, as a click's would be.
    return event.type === "card_refused"
      ? answer(state, {
          type: "answer",
          source: "download",
          key: event.key,
          taskId: event.taskId,
          outcome: event.refusal,
        })
      : state;
  }
  if (event.type === "card_closed") {
    return { ...state, cards: state.cards.filter((each) => each !== card) };
  }
  const changed: EndCardLine =
    event.type === "card_delivered"
      ? { ...card, delivered: true }
      : // The file was not served: the card offers it again, as the panel does.
        { ...card, delivered: false, refusal: event.refusal };
  return { ...state, cards: state.cards.map((each) => (each === card ? changed : each)) };
}

/** Change what the tracker follows. */
export function tracking(state: Tracking, event: TrackingEvent): Tracking {
  if (
    event.type === "card_closed" ||
    event.type === "card_delivered" ||
    event.type === "card_refused"
  ) {
    return cardChanged(state, event);
  }
  return carded(state, followed(state, event));
}

/** Change what the tracker follows, but its cards. */
function followed(state: Tracking, event: Exclude<TrackingEvent, CardEvent>): Tracking {
  switch (event.type) {
    case "track": {
      const { task, launch } = event;
      const key = task.task_id;
      const entry: TrackedTask = {
        key,
        task,
        subject: launch.subject,
        from: launch.from,
        aim: launch.aim,
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
    case "result_refused":
      return { ...state, refusedResult: event.refusal };
    case "result_refusal_cleared":
      return { ...state, refusedResult: undefined };
    case "forget":
      // Signed out: nothing of the tasks of the session goes to the next user of the tab — an
      // answer still on its way finds no task to apply to.
      return { ...NOTHING_TRACKED, restored: state.restored };
  }
}
