// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The follow-up of background tasks, a piece of the shell (WF-IHM-0080): a long action gives
 * the hand back at once (WF-ARC-0090), and the screen that started it hands its reference to
 * the tracker, with the command that started it. The tracker asks where each task stands while
 * it runs, shows how far it has gone, and announces its end — success, or failure with its
 * motive, which the same command can run again — whatever screen the user went to meanwhile. Once a
 * task has ended, the screen shown is read anew if the task concerns it — of the same project, or the
 * screen it was started from (#3103) —; the button that started it waits until then
 * (`useTaskRunning`), mounted anew too, finding it by what it aims at (`useRunningTask`, #3404).
 *
 * One tracker for every kind of task, in the root layout: a navigation within the application
 * keeps it, and nothing of it blocks the screen while its panel is closed — no control disabled;
 * open, the panel is a modal dialog, which the person closes when they will. A full
 * reload follows again the tasks that still ran, from the storage of the tab (`storage.ts`),
 * with what the user named them after — a session found ended is not followed again: it wipes the
 * storage (`session-end.tsx`); and, for a session, the tracker follows the tasks of its
 * user that still run, which the root layout reads and streams apart from the document
 * (`listBackgroundTasks`), and those the API lists each time the tab shows again, which it did
 * not follow — started from another tab, another workstation —, without their command: failed,
 * such a task is run again from the screen of its object. A list the API does not give leaves
 * the tracker as it is. A task started elsewhere that ended between two readings is not found,
 * nor announced. A screen the download of a result came back to, refused (#416), names the task and
 * the refusal in its address: the tracker reads the task, follows it, tells the refusal by its entry,
 * and takes it away from the address (`result-refusal.ts`).
 *
 * Its panel is a sheet along the right edge of the window, which carries the history of the
 * messages of the session too (`message-history.ts`, #1043): a modal dialog, titled, which holds the
 * focus while open, and which Escape, its close button or a click outside it close, the focus given
 * back to the button of the bar. The button opens it, naming the number of the tasks followed and of the
 * refusals not read yet, which its badges show. Nothing opens it by itself but the refusal of a
 * result the browser came back with, whose download left from it. A task handed over, or ended, is
 * said under the bar, in the flow of the page, on whatever screen the user is: the last of them, in
 * a short line that stays until the next — a confirmation in place, the panel being closed —, and
 * noted in the history. Closed, the tasks are still followed — the shell asks where they stand
 * (`TaskPolling`) —, and the log of their ends still speaks, outside the panel, or within it while
 * it is open, where the focus is held.
 */
"use client";

import { CircleAlert, ListChecks, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  createContext,
  type Dispatch,
  type ReactNode,
  type RefObject,
  Suspense,
  use,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import type { BackgroundTask } from "@/api/problem";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { noteMessage, shownScreen, unreadRefusals } from "@/components/notices/message-history";
import { MessageList, useMessageHistory } from "@/components/notices/message-list";
import { useShownProjectLabel } from "@/components/shell/shown-project";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { listRunningTasks, readBackgroundTask } from "@/api/actions/tasks";

import { downloadWhenThere } from "./result-download";
import { readRefusal, withoutRefusal } from "./result-refusal";
import { isOwner, keepOwner, wipeStores } from "./session-end";
import { restoreTasks, saveTasks } from "./storage";
import { EndLog, TaskEntry, taskName, TaskPolling, useTaskNaming } from "./task-entry";
import {
  type EndCardLine,
  type EndLine,
  isPolled,
  type Launch,
  NOTHING_TRACKED,
  readsAnew,
  type Tracking,
  tracking,
  type TrackingEvent,
} from "./tracking";

/** Hand a task over to the tracker, with what started it. */
export type TrackTask = (task: BackgroundTask, launch?: Launch) => void;

/** The last task handed over or ended, which the shell says under its bar. */
type TaskNews =
  | {
      readonly kind: "started";
      readonly task: BackgroundTask;
      readonly subject: string | undefined;
    }
  | { readonly kind: "ended"; readonly line: EndLine };

/** What the tracker holds: what it follows, whether the panel is open, and the last news. */
interface Held {
  readonly tracking: Tracking;
  readonly shown: boolean;
  readonly news: TaskNews | undefined;
}

/** What the tracker holds before the browser has read anything, the server's too. */
const NOTHING_HELD: Held = { tracking: NOTHING_TRACKED, shown: false, news: undefined };

/**
 * What the tracker holds, outside React: the panel and its button read it by subscribing to it,
 * and nothing else is rendered again when it changes. A context above the page that changed
 * instead — tasks restored, streamed, read again while a page streamed by the server is not
 * revealed yet — would make React render that page anew in the browser, beside the one the
 * server sent (#173, #180).
 */
interface TrackerStore {
  readonly subscribe: (listener: () => void) => () => void;
  readonly read: () => Held;
  readonly dispatch: Dispatch<TrackingEvent>;
  readonly show: (shown: boolean) => void;
  /** Say a news under the bar — none, and the line is closed. */
  readonly tell: (news: TaskNews | undefined) => void;
  /**
   * Read the screen anew for an end, once: the shell and a screen that waits for the end of its task
   * both read it anew, and the page is read once (`ReadAnew`, `useReadAnewWhenTaskEnds`).
   */
  readonly readAnew: (line: EndLine, refresh: () => void) => void;
}

/**
 * The news once an event has changed what the tracker follows: an end logged is the last. A success
 * or a failure has its floating card (`EndCards`), which stays and carries what follows: the line
 * under the bar does not say it a second time, and says nothing more of the task handed over before
 * it (#3292). A follow-up interrupted, which has no card, is said by the line.
 */
function newsAfter(before: Held, after: Tracking, event: TrackingEvent): TaskNews | undefined {
  if (event.type === "forget") {
    return undefined;
  }
  const ended = after.log.at(-1);
  if (ended === undefined || ended === before.tracking.log.at(-1)) {
    return before.news;
  }
  return ended.end === "interrupted" ? { kind: "ended", line: ended } : undefined;
}

/** A store of the tracker, holding nothing yet; a change that changes nothing tells no one. */
function trackerStore(): TrackerStore {
  let held = NOTHING_HELD;
  const listeners = new Set<() => void>();
  const readAnew = new WeakSet<EndLine>();
  const hold = (next: Held) => {
    if (next.tracking === held.tracking && next.shown === held.shown && next.news === held.news) {
      return;
    }
    held = next;
    for (const listener of listeners) {
      listener();
    }
  };
  return {
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    read: () => held,
    dispatch: (event) => {
      const next = tracking(held.tracking, event);
      hold({ ...held, tracking: next, news: newsAfter(held, next, event) });
    },
    show: (shown) => {
      hold({ ...held, shown });
    },
    tell: (news) => {
      hold({ ...held, news });
    },
    readAnew: (line, refresh) => {
      if (!readAnew.has(line)) {
        readAnew.add(line);
        refresh();
      }
    },
  };
}

/**
 * What the panel and its button share: the store, the identifier the button controls, and the
 * button, which the focus goes back to as the panel closes.
 */
interface TrackerState {
  readonly store: TrackerStore;
  readonly panelId: string;
  readonly button: RefObject<HTMLButtonElement | null>;
}

/** What the server renders of the tracker, and what hydration starts from. */
function nothingHeld(): Held {
  return NOTHING_HELD;
}

/** What the panel and its button read of the tracker, rendered again only when it changes. */
function useTracker() {
  const { store, panelId, button } = inTracker(useContext(StateContext));
  const {
    tracking: state,
    shown,
    news,
  } = useSyncExternalStore(store.subscribe, store.read, nothingHeld);
  return {
    tasks: state.tasks,
    log: state.log,
    refusedResult: state.refusedResult,
    dispatch: store.dispatch,
    open: shown,
    setOpen: store.show,
    news,
    tell: store.tell,
    panelId,
    button,
  };
}

/** What the screens and the shell ask of the tracker: to follow a task, to forget them all. */
interface TrackerCommands {
  readonly track: TrackTask;
  readonly forget: () => void;
}

// Two contexts, neither of which changes: the screens that hand a task over read functions, the
// panel and its button the store they subscribe to.
const TrackContext = createContext<TrackerCommands | undefined>(undefined);
const StateContext = createContext<TrackerState | undefined>(undefined);

/** What a context of the tracker holds; a component outside the tracker is a defect. */
function inTracker<T>(value: T | undefined): T {
  if (value === undefined) {
    throw new Error("a background task is followed within the TaskTracker of the shell only");
  }
  return value;
}

/**
 * The function that hands a task the screen started over to the tracker of the shell, with the
 * screen it was started from: said under the bar, and noted in the history of the messages.
 */
export function useTrackTask(): TrackTask {
  const { track } = inTracker(useContext(TrackContext));
  const t = useTranslations("tasks");
  const naming = useTaskNaming();
  const project = useShownProjectLabel();
  return useCallback(
    (task: BackgroundTask, launch: Launch = {}) => {
      const from = shownScreen(project());
      track(task, { ...launch, from });
      const name = taskName(naming, { task, subject: launch.subject });
      const sentence = t("started", { task: name });
      noteMessage({}, { tone: "success", sentence, object: name, screen: from });
    },
    [track, t, naming, project],
  );
}

/**
 * Run `then` once the task named has ended in the way asked (`succeeded`, or `unsuccessful`: failed,
 * or its follow-up interrupted), whether it is the task as it was handed over or the one a relaunch
 * put in its place. `task_id` is none until a task was started.
 */
function useWhenTaskEnded(
  taskId: string | undefined,
  way: "succeeded" | "unsuccessful",
  then: (line: EndLine) => void,
): void {
  const { log, tasks } = useTracker();
  const done = useRef<string>(undefined);
  // A relaunch puts a new task in the place of the one handed over, which keeps its key: the end
  // of the task named is the end of the one now in its place too.
  const current = tasks.find((tracked) => tracked.key === taskId)?.task.task_id;
  const ended =
    taskId === undefined
      ? undefined
      : log.find(
          // Any end but a success — a failure, an interrupted follow-up — is the unsuccessful way.
          (line) =>
            (line.task.task_id === taskId || line.task.task_id === current) &&
            (line.end === "succeeded") === (way === "succeeded"),
        );
  useEffect(() => {
    if (ended !== undefined && done.current !== taskId) {
      done.current = taskId;
      then(ended);
    }
  }, [ended, taskId, then]);
}

/**
 * Run `then` once, when the task named has succeeded — a relaunch of it included, never when it
 * failed or its follow-up was interrupted —, for the screen that started it and still shows: a
 * task that ends while the user is elsewhere leads nowhere. `task_id` is none until a task was
 * started.
 */
export function useWhenTaskSucceeds(
  taskId: string | undefined,
  then: (line: EndLine) => void,
): void {
  useWhenTaskEnded(taskId, "succeeded", then);
}

/**
 * Run `then` once, when the task named has failed or its follow-up was interrupted — never when it
 * succeeded: what waited for its end is freed. `task_id` is none until a task was started. The
 * line of the end carries the motive of the failure (`problem`).
 */
export function useWhenTaskFails(taskId: string | undefined, then: (line: EndLine) => void): void {
  useWhenTaskEnded(taskId, "unsuccessful", then);
}

/**
 * Whether the task named still runs in the tracker — the task as it was handed over, or the one a
 * relaunch put in its place —: the button that started it waits until then (WF-IHM-0080, #3103).
 * Ended, failed, its follow-up interrupted, or dismissed from the tracker, it no longer runs, and the
 * button is given back. `task_id` is none until a task was started. Read from the store of the
 * tracker, the button is rendered again only when the answer changes (#180); a command rendered
 * outside the tracker has started none.
 */
export function useTaskRunning(taskId: string | undefined): boolean {
  // Outside the tracker no task was ever handed over (`useTrackTask` would have thrown): none runs.
  const store = useContext(StateContext)?.store;
  return useSyncExternalStore(
    store?.subscribe ?? subscribeToNothing,
    () => {
      const entry = store?.read().tracking.tasks.find((tracked) => tracked.key === taskId);
      return entry !== undefined && isPolled(entry);
    },
    () => false,
  );
}

/**
 * The task that runs for what a button aims at (`taskAim`), by the key it is followed under — the
 * last one handed over, when several were —; none when none runs. The button that started a task
 * forgets it once mounted anew — the tab reloaded, the screen left and come back to —: it waits on
 * the task it has just started or, failing it, on the one it finds so, and is given back at its end
 * as at the end of its own (#3404). Only in the tab: a task started from another tab or another
 * workstation comes without its aim (`listBackgroundTasks`), and no button finds it.
 */
export function useRunningTask(aim: string): string | undefined {
  const store = useContext(StateContext)?.store;
  return useSyncExternalStore(
    store?.subscribe ?? subscribeToNothing,
    () =>
      store?.read().tracking.tasks.findLast((tracked) => tracked.aim === aim && isPolled(tracked))
        ?.key,
    () => undefined,
  );
}

/** A subscription to nothing: nothing ever changes. */
function subscribeToNothing(): () => void {
  return () => undefined;
}

/**
 * Read the screen anew once the task named has ended, whichever way — the task as it was handed over,
 * or the one a relaunch put in its place —, even when the tracker does not know the screen it was
 * started from: found again after a reload, or read by the screen from its object (an import
 * analysing). An end the shell has read the screen anew for already reads nothing more. `task_id`
 * is none until a task was started.
 */
export function useReadAnewWhenTaskEnds(taskId: string | undefined): void {
  const { store } = inTracker(useContext(StateContext));
  const router = useRouter();
  // Only the line of this task: the screen is not rendered again for the rest of the tracker (#180).
  const line = useSyncExternalStore(
    store.subscribe,
    () => {
      const { log, tasks } = store.read().tracking;
      const current = tasks.find((tracked) => tracked.key === taskId)?.task.task_id;
      return taskId === undefined
        ? undefined
        : log.findLast(
            (end) =>
              end.end !== "interrupted" &&
              (end.task.task_id === taskId || end.task.task_id === current),
          );
    },
    () => undefined,
  );
  useEffect(() => {
    if (line !== undefined) {
      store.readAnew(line, () => {
        router.refresh();
      });
    }
  }, [line, store, router]);
}

/**
 * Download the result of the export named once its task has succeeded — a relaunch of it included
 * —, while the screen that asked for it still shows (#3103): once, for the task named, read anew
 * first, and left only if the screen is still there once the read has answered. `task_id` is none
 * until an export was asked.
 */
export function useDownloadWhenTaskSucceeds(taskId: string | undefined): void {
  const { dispatch } = inTracker(useContext(StateContext)).store;
  const shown = useRef(true);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
  const download = useCallback(
    (line: EndLine) => {
      downloadWhenThere(line, dispatch, () => shown.current);
    },
    [dispatch],
  );
  useWhenTaskSucceeds(taskId, download);
}

/** The function that changes what the tracker follows: an answer to a task, a card closed. */
export function useTrackerDispatch(): Dispatch<TrackingEvent> {
  return inTracker(useContext(StateContext)).store.dispatch;
}

/**
 * The cards of the ends the shell shows, the last first, and the button of the bar, which the focus
 * goes to once the last card is closed (`EndCards`).
 */
export function useEndCards(): {
  readonly cards: readonly EndCardLine[];
  readonly button: RefObject<HTMLButtonElement | null>;
} {
  const { store, button } = inTracker(useContext(StateContext));
  const cards = useSyncExternalStore(
    store.subscribe,
    () => store.read().tracking.cards,
    () => NOTHING_TRACKED.cards,
  );
  return { cards, button };
}

/**
 * The function that forgets every task the tracker follows, what the tab kept of them for a
 * reload, and the history of the messages: signing out leaves nothing of the session to the next
 * user of the tab.
 */
export function useForgetTasks(): () => void {
  return inTracker(useContext(TrackContext)).forget;
}

/** What the tracker follows the tasks of, and within what. */
export interface TaskTrackerProps {
  /** Whether a session is open: its user's tasks that still run are read again as the tab shows. */
  readonly signedIn?: boolean;
  /**
   * The identifier of the account of the session: what the tab kept of another account's — or of
   * none — is wiped before it is read back (`session-end.tsx`).
   */
  readonly accountId?: string | undefined;
  /**
   * The tasks of the user that still run, which the server of Next reads apart from the document
   * (`listBackgroundTasks`), and streams: the shell dispatches no server action as it mounts, and
   * nothing of the page waits for them. None without a session.
   */
  readonly running?: Promise<readonly BackgroundTask[]> | undefined;
  readonly children: ReactNode;
}

/**
 * Follow the tasks of the user the server streams, once they come: nothing is rendered, and
 * nothing waits for them but this (`Suspense`).
 */
function StreamedTasks({
  running,
  dispatch,
}: {
  readonly running: Promise<readonly BackgroundTask[]>;
  readonly dispatch: Dispatch<TrackingEvent>;
}) {
  const tasks = use(running);
  useEffect(() => {
    dispatch({ type: "found", tasks });
  }, [tasks, dispatch]);
  return null;
}

/**
 * How long after the document has loaded the page it streamed is revealed at the latest: React
 * holds back the reveal of a boundary the server streamed by a few hundred milliseconds.
 */
const REVEALED_AFTER = 1000;

/**
 * Run a change of the address once the page the document streamed is revealed: once the document
 * has loaded, and a while after. What it gives back cancels it — for the refusal of the result of a
 * task, as for that of the download of a backup (`backup-commands.tsx`).
 */
export function afterReveal(change: () => void): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const loaded = () => {
    timer = setTimeout(change, REVEALED_AFTER);
  };
  if (document.readyState === "complete") {
    loaded();
  } else {
    window.addEventListener("load", loaded, { once: true });
  }
  return () => {
    window.removeEventListener("load", loaded);
    clearTimeout(timer);
  };
}

/**
 * Read the screen shown anew once a task that concerns it ends (`readsAnew`, #3103): its project
 * — the list of the revisions after a marking, the imports after an import —, whatever the screen
 * of the project the user went to meanwhile. The page is read again under what the screen holds —
 * the router keeps the state of its components, what the user is typing included. The ends already
 * logged when it mounts read nothing anew.
 */
function ReadAnew({ store }: { readonly store: TrackerStore }) {
  const router = useRouter();
  // The last end the render saw: an end logged between the render and the effect is read anew too.
  const [seen] = useState(() => store.read().tracking.log.at(-1));
  useEffect(() => {
    let last = seen;
    const check = () => {
      const { log } = store.read().tracking;
      if (log.at(-1) === last) {
        return;
      }
      // The ends logged since the last one seen: all of them when it is gone from the log — out of
      // its last lines, or forgotten on signing out.
      const fresh = log.slice(last === undefined ? 0 : log.indexOf(last) + 1);
      last = log.at(-1);
      const concerned = fresh.filter((line) => readsAnew(line, window.location.pathname));
      // One read for all the ends of a same notification.
      const asked: EndLine[] = [];
      for (const line of concerned) {
        store.readAnew(line, () => asked.push(line));
      }
      if (asked.length > 0) {
        router.refresh();
      }
    };
    const unsubscribe = store.subscribe(check);
    check();
    return unsubscribe;
  }, [store, router, seen]);
  return null;
}

/** Follow the background tasks the screens within it start, and those of its user that run. */
export function TaskTracker({ signedIn = false, accountId, running, children }: TaskTrackerProps) {
  const [store] = useState(trackerStore);
  const { dispatch } = store;
  const restored = useSyncExternalStore(
    store.subscribe,
    () => store.read().tracking.restored,
    () => false,
  );
  const panelId = useId();
  // Signing out: the tasks followed leave the page, and what the session left in the tab is wiped
  // (`wipeStores`, the one place that does, #1180).
  const forget = useCallback(() => {
    dispatch({ type: "forget" });
    store.show(false);
    wipeStores();
  }, [store, dispatch]);
  // The storage of the tab is the browser's: read once mounted, never while rendering on the
  // server, and written only once read, lest an empty list erase it.
  useEffect(() => {
    if (accountId !== undefined && !isOwner(accountId)) {
      // Another account wrote what the tab kept, or none: nothing of it is read back (#1180).
      wipeStores();
      keepOwner(accountId);
    }
    dispatch({ type: "restore", tasks: restoreTasks() });
  }, [dispatch, accountId]);
  // The refusal of a result the browser came back with, once: the task is read, followed — an
  // ended task is not kept across the load —, and its entry tells the refusal; a task that cannot
  // be read again, the panel tells it itself. The address no longer carries it once the page is
  // revealed, so that a reload does not tell it again — not before: the router of Next renders
  // the page anew on a change of the address, which a page still pending would show twice (#173).
  useEffect(() => {
    const refused = readRefusal(new URLSearchParams(window.location.search));
    if (refused === undefined) {
      return undefined;
    }
    const { id: taskId, refusal } = refused;
    // The download left from the panel: it opens again, where the refusal is told.
    const told = () => {
      dispatch({ type: "result_refused", refusal });
      store.show(true);
    };
    void readBackgroundTask(taskId).then((outcome) => {
      if (outcome.kind !== "done") {
        told();
        return;
      }
      // Followed under the identifier the API gives it, which the answer is applied to.
      const read = outcome.data.task_id;
      dispatch({ type: "found", tasks: [outcome.data] });
      dispatch({ type: "answer", source: "download", key: read, taskId: read, outcome: refusal });
      store.show(true);
    }, told);
    return afterReveal(() => {
      if (readRefusal(new URLSearchParams(window.location.search))?.id === taskId) {
        window.history.replaceState(window.history.state, "", withoutRefusal(window.location));
      }
    });
  }, [dispatch, store]);
  // The tasks of the user that still run, followed once those the tab kept are back, as the
  // server streams them (`StreamedTasks`) — a data of the page, read on the server, rather than a
  // server action as the shell mounts —; and again, read by a server action, each time the tab
  // shows once more — the user may have started one from another tab meanwhile: what the API
  // does not give, refused or out of reach, the tracker does without.
  const streamed =
    restored && running !== undefined ? (
      <Suspense fallback={null}>
        <StreamedTasks running={running} dispatch={dispatch} />
      </Suspense>
    ) : null;
  useEffect(() => {
    if (!signedIn) {
      return undefined;
    }
    let live = true;
    const shown = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void listRunningTasks().then(
        (outcome) => {
          if (live && outcome.kind === "done") {
            dispatch({ type: "found", tasks: outcome.data });
          }
        },
        () => undefined,
      );
    };
    document.addEventListener("visibilitychange", shown);
    return () => {
      live = false;
      document.removeEventListener("visibilitychange", shown);
    };
  }, [signedIn, dispatch]);
  // The tasks followed, kept in the tab each time they change, once those it kept are back.
  useEffect(() => {
    let saved: Tracking["tasks"] | undefined;
    const save = () => {
      const { tasks, restored: back } = store.read().tracking;
      // Once the session is found ended (`SignIn`), the stores are wiped and own no account: the
      // tasks of that session are not written again.
      if (accountId !== undefined && !isOwner(accountId)) {
        return;
      }
      if (back && tasks !== saved) {
        saved = tasks;
        saveTasks(tasks);
      }
    };
    save();
    return store.subscribe(save);
  }, [store, accountId]);
  const commands = useMemo<TrackerCommands>(
    () => ({
      track: (task, launch = {}) => {
        store.tell({ kind: "started", task, subject: launch.subject });
        dispatch({ type: "track", task, launch });
      },
      forget,
    }),
    [store, dispatch, forget],
  );
  const button = useRef<HTMLButtonElement>(null);
  const value = useMemo(() => ({ store, panelId, button }), [store, panelId]);
  return (
    <TrackContext value={commands}>
      <StateContext value={value}>
        {children}
        {streamed}
        <ReadAnew store={store} />
      </StateContext>
    </TrackContext>
  );
}

/**
 * The button of the bar of the shell that opens or closes the panel of the tasks and the messages,
 * with the number of the tasks followed and of the refusals not read yet, which its name says too.
 */
export function TasksButton() {
  const t = useTranslations("tasks");
  const { tasks, open, setOpen, panelId, button } = useTracker();
  const unread = unreadRefusals(useMessageHistory());
  const count = tasks.length;
  return (
    <Button
      ref={button}
      type="button"
      variant="outline"
      size="sm"
      aria-label={t("toggle", { count, unread })}
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-controls={open ? panelId : undefined}
      onClick={() => {
        setOpen(!open);
      }}
    >
      <ListChecks aria-hidden="true" />
      <span className="hidden lg:inline">{t("panel")}</span>
      {count === 0 ? null : <Badge aria-hidden="true">{count}</Badge>}
      {unread === 0 ? null : (
        <Badge aria-hidden="true" variant="outline" className="text-destructive">
          <CircleAlert />
          {unread}
        </Badge>
      )}
    </Button>
  );
}

/** The sentence of each end, by how it ended. */
const END_SENTENCE = {
  succeeded: "succeeded",
  failed: "failed",
  interrupted: "interruptedLine",
} as const;

/**
 * The last task handed over, or whose follow-up was interrupted, under the bar, in the flow of the
 * page: a short line that stays until the next, not announced — the log of the ends speaks, and a
 * task handed over follows a command the user just gave —, or until it is closed (#1179), by its
 * button, reached by the keyboard; the focus goes then to the button of the bar, where the task is
 * still followed. A success or a failure is said by its card alone, which closes the line (#3292).
 */
function News({
  news,
  onClose,
}: {
  readonly news: TaskNews | undefined;
  readonly onClose: () => void;
}) {
  const t = useTranslations("tasks");
  const commands = useTranslations("commands");
  const naming = useTaskNaming();
  if (news === undefined) {
    return null;
  }
  const sentence =
    news.kind === "started"
      ? t("started", { task: taskName(naming, news) })
      : t(END_SENTENCE[news.line.end], { task: taskName(naming, news.line) });
  return (
    <div className="flex items-center gap-2 border-b px-4 py-1 text-sm">
      <p className="flex-1">{sentence}</p>
      <CommandTooltip label={t("closeNews")} help={commands("dismissNews.help")}>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t("closeNews")}
          className="size-6"
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </CommandTooltip>
    </div>
  );
}

/**
 * The panel of the tasks and the messages, a sheet along the right edge of the window, opened by
 * the button of the bar; the tasks followed whether it is open or not, the log of their ends, and
 * the last of them said under the bar. The focus taken from a task dismissed goes to the next task,
 * else the one before, else the region of the tasks — never out of the panel, which holds it.
 */
export function TaskPanel() {
  const t = useTranslations("tasks");
  const { tasks, log, refusedResult, dispatch, open, setOpen, news, tell, panelId, button } =
    useTracker();
  const region = useRef<HTMLElement>(null);
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const heading = useId();
  const dismissRef = useCallback((key: string, element: HTMLButtonElement | null) => {
    if (element === null) {
      buttons.current.delete(key);
    } else {
      buttons.current.set(key, element);
    }
  }, []);
  const dismiss = (key: string) => {
    const index = tasks.findIndex((entry) => entry.key === key);
    const neighbour = tasks[index + 1] ?? tasks[index - 1];
    const target = neighbour === undefined ? undefined : buttons.current.get(neighbour.key);
    (target ?? region.current)?.focus();
    dispatch({ type: "dismiss", key });
  };
  return (
    <>
      {tasks.map((entry) => (
        <TaskPolling key={entry.key} entry={entry} dispatch={dispatch} />
      ))}
      {open ? null : <EndLog log={log} />}
      <News
        news={news}
        onClose={() => {
          button.current?.focus();
          tell(undefined);
        }}
      />
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          id={panelId}
          aria-describedby={undefined}
          className="w-full max-w-md sm:w-96"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            button.current?.focus();
          }}
        >
          <SheetHeader className="flex-row items-center justify-between border-b">
            <SheetTitle>{t("panel")}</SheetTitle>
            <SheetClose asChild>
              <Button type="button" variant="ghost" size="sm" aria-label={t("close")}>
                <X aria-hidden="true" />
              </Button>
            </SheetClose>
          </SheetHeader>
          <div className="flex-1 space-y-6 overflow-y-auto p-4">
            <EndLog log={log} />
            <section
              ref={region}
              tabIndex={-1}
              aria-labelledby={heading}
              className="space-y-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <h3 id={heading} className="font-medium">
                {t("label")}
              </h3>
              {refusedResult === undefined ? null : (
                <div className="space-y-1 text-sm">
                  <p className="font-medium">{t("resultRefused")}</p>
                  <OutcomeNotice
                    outcome={refusedResult}
                    dismissible
                    onClear={() => {
                      dispatch({ type: "result_refusal_cleared" });
                    }}
                  />
                </div>
              )}
              {tasks.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("none")}</p>
              ) : (
                <ul className="space-y-3">
                  {tasks.map((entry) => (
                    <li key={entry.key}>
                      <TaskEntry
                        entry={entry}
                        dispatch={dispatch}
                        onDismiss={dismiss}
                        dismissRef={dismissRef}
                        onScreenShown={() => {
                          setOpen(false);
                        }}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <MessageList
              onFollow={() => {
                setOpen(false);
              }}
            />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
