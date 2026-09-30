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
 * keeps it, and nothing of it blocks the screen — no dialog, no control disabled. A full
 * reload follows again the tasks that still ran, from the storage of the tab (`storage.ts`),
 * with what the user named them after; and, for a session, the tracker follows the tasks of its
 * user that still run, which the root layout reads and streams apart from the document
 * (`listBackgroundTasks`), and those the API lists each time the tab shows again, which it did
 * not follow — started from another tab, another workstation —, without their command: failed,
 * such a task is run again from the screen of its object. A list the API does not give leaves
 * the tracker as it is. A task started elsewhere that ended between two readings is not found,
 * nor announced.
 *
 * Its panel lies under the bar of the shell, in the flow of the page, and a button of the bar
 * shows or hides it, with the number of the tasks followed. Until the user decides, it shows
 * while tasks are followed — a task handed over, or found again after a reload —; a task handed
 * over shows it again. Hidden, the tasks are still followed — their entries stay mounted and
 * ask where they stand —, and the log of their ends, outside what hides, still speaks.
 */
"use client";

import { ListChecks } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  createContext,
  type Dispatch,
  type ReactNode,
  Suspense,
  use,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";

import type { BackgroundTask } from "@/api/problem";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { listRunningTasks } from "@/api/actions/tasks";

import { forgetTasks, restoreTasks, saveTasks } from "./storage";
import { EndLog, TaskEntry } from "./task-entry";
import {
  type Launch,
  NOTHING_TRACKED,
  type Tracking,
  tracking,
  type TrackingEvent,
} from "./tracking";

/** Hand a task over to the tracker, with what started it. */
export type TrackTask = (task: BackgroundTask, launch?: Launch) => void;

/** What the panel and its button read of the tracker: the tasks followed and the log of their ends. */
interface TrackerState {
  readonly tasks: Tracking["tasks"];
  readonly log: Tracking["log"];
  readonly dispatch: Dispatch<TrackingEvent>;
  /** Whether the panel shows the tasks followed, and the identifier the button controls. */
  readonly open: boolean;
  readonly setOpen: (open: boolean) => void;
  readonly panelId: string;
}

/** What the screens and the shell ask of the tracker: to follow a task, to forget them all. */
interface TrackerCommands {
  readonly track: TrackTask;
  readonly forget: () => void;
}

// Two contexts: the screens that hand a task over read functions that never change, and are
// not rendered again at each read of a task; the panel alone reads what changes.
const TrackContext = createContext<TrackerCommands | undefined>(undefined);
const StateContext = createContext<TrackerState | undefined>(undefined);

/** What a context of the tracker holds; a component outside the tracker is a defect. */
function inTracker<T>(value: T | undefined): T {
  if (value === undefined) {
    throw new Error("a background task is followed within the TaskTracker of the shell only");
  }
  return value;
}

/** The function that hands a task the screen started over to the tracker of the shell. */
export function useTrackTask(): TrackTask {
  return inTracker(useContext(TrackContext)).track;
}

/**
 * The function that forgets every task the tracker follows, and what the tab kept of them for a
 * reload: signing out leaves nothing of the session to the next user of the tab.
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

/** Follow the background tasks the screens within it start, and those of its user that run. */
export function TaskTracker({ signedIn = false, running, children }: TaskTrackerProps) {
  const [state, dispatch] = useReducer(tracking, NOTHING_TRACKED);
  // Whether the user showed or hid the panel; `undefined` while it follows the tasks.
  const [shown, setShown] = useState<boolean>();
  const open = shown ?? state.tasks.length > 0;
  const panelId = useId();
  // The storage of the tab is the browser's: read once mounted, never while rendering on the
  // server, and written only once read, lest an empty list erase it.
  useEffect(() => {
    dispatch({ type: "restore", tasks: restoreTasks() });
  }, []);
  // The tasks of the user that still run, followed once those the tab kept are back, as the
  // server streams them (`StreamedTasks`) — a data of the page, read on the server, rather than a
  // server action as the shell mounts —; and again, read by a server action, each time the tab
  // shows once more — the user may have started one from another tab meanwhile: what the API
  // does not give, refused or out of reach, the tracker does without.
  const streamed =
    state.restored && running !== undefined ? (
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
  }, [signedIn]);
  useEffect(() => {
    if (state.restored) {
      saveTasks(state.tasks);
    }
  }, [state.restored, state.tasks]);
  const commands = useMemo<TrackerCommands>(
    () => ({
      track: (task, launch = {}) => {
        dispatch({ type: "track", task, launch });
        setShown(undefined);
      },
      forget: () => {
        dispatch({ type: "forget" });
        forgetTasks();
      },
    }),
    [],
  );
  // Built anew only when what the panel shows changes: not when the tab has nothing to restore,
  // nor when the API lists no task it did not follow. The shell sits above every page, and a
  // context that changes while a page streamed by the server is not revealed yet makes React
  // render that page anew in the browser, beside the one the server sent (#173).
  const { tasks, log } = state;
  const value = useMemo(
    () => ({ tasks, log, dispatch, open, setOpen: setShown, panelId }),
    [tasks, log, open, panelId],
  );
  return (
    <TrackContext value={commands}>
      <StateContext value={value}>
        {children}
        {streamed}
      </StateContext>
    </TrackContext>
  );
}

const PANEL = "border-b bg-card px-4 py-2 text-card-foreground";

/**
 * The button of the bar of the shell that shows or hides the panel of the tasks, with the
 * number of the tasks followed, which its name says too.
 */
export function TasksButton() {
  const t = useTranslations("tasks");
  const { tasks, open, setOpen, panelId } = inTracker(useContext(StateContext));
  const count = tasks.length;
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-label={t("toggle", { count })}
      aria-expanded={open}
      aria-controls={panelId}
      onClick={() => {
        setOpen(!open);
      }}
    >
      <ListChecks aria-hidden="true" />
      <span className="hidden lg:inline">{t("label")}</span>
      {count === 0 ? null : <Badge aria-hidden="true">{count}</Badge>}
    </Button>
  );
}

/**
 * The main content of the page, made a target of the focus — outside the order of the
 * keyboard — when it is not one already. The page is not the shell's: it is found in the
 * document, where every screen has its `<main>`.
 */
function mainContent(): HTMLElement | null {
  const main = document.querySelector("main");
  if (main !== null && !main.hasAttribute("tabindex")) {
    main.tabIndex = -1;
  }
  return main;
}

/**
 * The tasks followed, where the shell places them — in the flow of the page, where they hide
 * nothing —, and the log of their ends. The region stays mounted, empty while no task is
 * followed: its log is in place before it speaks, and it takes the focus when the last task is
 * dismissed.
 */
export function TaskPanel() {
  const t = useTranslations("tasks");
  const { tasks, log, dispatch, open, panelId } = inTracker(useContext(StateContext));
  const region = useRef<HTMLElement>(null);
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const dismissRef = useCallback((key: string, button: HTMLButtonElement | null) => {
    if (button === null) {
      buttons.current.delete(key);
    } else {
      buttons.current.set(key, button);
    }
  }, []);
  // The focus leaves the button dismissed before it goes: to the dismissal of the next task,
  // else of the one before, else to the main content of the page — the region, empty then,
  // has no height to show a focus —, never to the document.
  const dismiss = (key: string) => {
    const index = tasks.findIndex((entry) => entry.key === key);
    const neighbour = tasks[index + 1] ?? tasks[index - 1];
    const target = neighbour === undefined ? undefined : buttons.current.get(neighbour.key);
    (target ?? mainContent() ?? region.current)?.focus();
    dispatch({ type: "dismiss", key });
  };
  const followed = tasks.length > 0;
  return (
    <section
      ref={region}
      id={panelId}
      tabIndex={-1}
      aria-label={t("label")}
      className={open ? PANEL : undefined}
    >
      <EndLog log={log} />
      {open && !followed ? <p className="text-sm text-muted-foreground">{t("none")}</p> : null}
      {followed ? (
        <ul hidden={!open} className="flex flex-wrap gap-x-8 gap-y-2">
          {tasks.map((entry) => (
            <li key={entry.key} className="min-w-64 flex-1">
              <TaskEntry
                entry={entry}
                dispatch={dispatch}
                onDismiss={dismiss}
                dismissRef={dismissRef}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
