// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The follow-up of background tasks, a piece of the shell (WF-IHM-0080): a long action gives
 * the hand back at once (WF-ARC-0090), and the screen that started it hands its reference to
 * the tracker, with the command that started it. The tracker asks where each task stands while
 * it runs, shows how far it has gone, and announces its end — success, or failure with its
 * motive, which the same command can run again — whatever screen the user went to meanwhile.
 *
 * One tracker for every kind of task, in the root layout: a navigation within the application
 * keeps it, and nothing of it blocks the screen while its panel is closed — no control disabled;
 * open, the panel is a modal dialog, which the person closes when they will. A full
 * reload follows again the tasks that still ran, from the storage of the tab (`storage.ts`),
 * with what the user named them after; and, for a session, the tracker follows the tasks of its
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
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import {
  forgetMessages,
  noteMessage,
  shownScreen,
  unreadRefusals,
} from "@/components/notices/message-history";
import { MessageList, useMessageHistory } from "@/components/notices/message-list";
import { useShownProjectLabel } from "@/components/shell/shown-project";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { listRunningTasks, readBackgroundTask } from "@/api/actions/tasks";

import { readRefusal, withoutRefusal } from "./result-refusal";
import { forgetTasks, restoreTasks, saveTasks } from "./storage";
import { EndLog, TaskEntry, taskName, TaskPolling, useTaskNaming } from "./task-entry";
import {
  type EndLine,
  type Launch,
  NOTHING_TRACKED,
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
  readonly tell: (news: TaskNews) => void;
}

/** The news once an event has changed what the tracker follows: an end logged is the last. */
function newsAfter(before: Held, after: Tracking, event: TrackingEvent): TaskNews | undefined {
  if (event.type === "forget") {
    return undefined;
  }
  const ended = after.log.at(-1);
  return ended !== undefined && ended !== before.tracking.log.at(-1)
    ? { kind: "ended", line: ended }
    : before.news;
}

/** A store of the tracker, holding nothing yet; a change that changes nothing tells no one. */
function trackerStore(): TrackerStore {
  let held = NOTHING_HELD;
  const listeners = new Set<() => void>();
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

/** Follow the background tasks the screens within it start, and those of its user that run. */
export function TaskTracker({ signedIn = false, running, children }: TaskTrackerProps) {
  const [store] = useState(trackerStore);
  const { dispatch } = store;
  const restored = useSyncExternalStore(
    store.subscribe,
    () => store.read().tracking.restored,
    () => false,
  );
  const panelId = useId();
  // The storage of the tab is the browser's: read once mounted, never while rendering on the
  // server, and written only once read, lest an empty list erase it.
  useEffect(() => {
    dispatch({ type: "restore", tasks: restoreTasks() });
  }, [dispatch]);
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
      if (back && tasks !== saved) {
        saved = tasks;
        saveTasks(tasks);
      }
    };
    save();
    return store.subscribe(save);
  }, [store]);
  const commands = useMemo<TrackerCommands>(
    () => ({
      track: (task, launch = {}) => {
        store.tell({ kind: "started", task, subject: launch.subject });
        dispatch({ type: "track", task, launch });
      },
      forget: () => {
        dispatch({ type: "forget" });
        store.show(false);
        forgetTasks();
        forgetMessages();
      },
    }),
    [store, dispatch],
  );
  const button = useRef<HTMLButtonElement>(null);
  const value = useMemo(() => ({ store, panelId, button }), [store, panelId]);
  return (
    <TrackContext value={commands}>
      <StateContext value={value}>
        {children}
        {streamed}
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
 * The last task handed over or ended, under the bar, in the flow of the page: a short line that
 * stays until the next, not announced — the log of the ends speaks, and a task handed over follows
 * a command the user just gave.
 */
function News({ news }: { readonly news: TaskNews | undefined }) {
  const t = useTranslations("tasks");
  const naming = useTaskNaming();
  if (news === undefined) {
    return null;
  }
  const sentence =
    news.kind === "started"
      ? t("started", { task: taskName(naming, news) })
      : t(END_SENTENCE[news.line.end], { task: taskName(naming, news.line) });
  return <p className="border-b px-4 py-1.5 text-sm">{sentence}</p>;
}

/**
 * The panel of the tasks and the messages, a sheet along the right edge of the window, opened by
 * the button of the bar; the tasks followed whether it is open or not, the log of their ends, and
 * the last of them said under the bar. The focus taken from a task dismissed goes to the next task,
 * else the one before, else the region of the tasks — never out of the panel, which holds it.
 */
export function TaskPanel() {
  const t = useTranslations("tasks");
  const { tasks, log, refusedResult, dispatch, open, setOpen, news, panelId, button } =
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
      <News news={news} />
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
