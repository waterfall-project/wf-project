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
 * reload follows again the tasks that still ran, from the storage of the tab (`storage.ts`).
 */
"use client";

import { useTranslations } from "next-intl";
import {
  createContext,
  type Dispatch,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from "react";

import type { BackgroundTask } from "@/api/problem";

import { restoreTasks, saveTasks } from "./storage";
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

interface TrackerState {
  readonly state: Tracking;
  readonly dispatch: Dispatch<TrackingEvent>;
}

// Two contexts: the screens that hand a task over read a function that never changes, and are
// not rendered again at each read of a task; the panel alone reads what changes.
const TrackContext = createContext<TrackTask | undefined>(undefined);
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
  return inTracker(useContext(TrackContext));
}

/** Follow the background tasks the screens within it start. */
export function TaskTracker({ children }: { readonly children: ReactNode }) {
  const [state, dispatch] = useReducer(tracking, NOTHING_TRACKED);
  // The storage of the tab is the browser's: read once mounted, never while rendering on the
  // server, and written only once read, lest an empty list erase it.
  useEffect(() => {
    dispatch({ type: "restore", tasks: restoreTasks() });
  }, []);
  useEffect(() => {
    if (state.restored) {
      saveTasks(state.tasks);
    }
  }, [state.restored, state.tasks]);
  const track = useCallback<TrackTask>((task, launch = {}) => {
    dispatch({ type: "track", task, launch });
  }, []);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return (
    <TrackContext value={track}>
      <StateContext value={value}>{children}</StateContext>
    </TrackContext>
  );
}

const PANEL = "border-b bg-card px-4 py-2 text-card-foreground";

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
  const { state, dispatch } = inTracker(useContext(StateContext));
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
    const index = state.tasks.findIndex((entry) => entry.key === key);
    const neighbour = state.tasks[index + 1] ?? state.tasks[index - 1];
    const target = neighbour === undefined ? undefined : buttons.current.get(neighbour.key);
    (target ?? mainContent() ?? region.current)?.focus();
    dispatch({ type: "dismiss", key });
  };
  const followed = state.tasks.length > 0;
  return (
    <section
      ref={region}
      tabIndex={-1}
      aria-label={t("label")}
      className={followed ? PANEL : undefined}
    >
      <EndLog log={state.log} />
      {followed ? (
        <ul className="flex flex-wrap gap-x-8 gap-y-2">
          {state.tasks.map((entry) => (
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
