// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The project a screen shows, handed to the shell: the side bar names it in its choice of a
 * project, and the breadcrumb in its steps. The shell persists from one page to the next, and
 * the root layout, rendered once, never learns the address shown; the screen of a project has
 * already read its project for the banner of its context (`ContextBanner`), which hands it on
 * from there — no read more.
 *
 * The shell keeps the last project handed on, and names it only while the address shows that
 * same project: on the way to another, whose screen is still loading, it says a project is open
 * without naming it rather than name the one left.
 *
 * It keeps it outside React, in a store the side bar and the breadcrumb subscribe to: a screen
 * hands its project on as it mounts, while a page streamed by the server may not be revealed yet
 * under the shell, and a context above it that changed then would make React render that page
 * anew in the browser, beside the one the server sent (#173, #180). The same project handed on
 * again, as each screen of it mounts, tells no one.
 */
"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
} from "react";

import type { components } from "@/api/generated/schema";

/** What the shell shows of a project: its identifier, its label, its code and its state. */
export type ShownProject = Pick<
  components["schemas"]["Project"],
  "project_id" | "label" | "code" | "state"
>;

/** The project handed on last, and who reads it. */
interface ShownStore {
  readonly subscribe: (listener: () => void) => () => void;
  readonly read: () => ShownProject | undefined;
  readonly show: (project: ShownProject) => void;
}

/** Whether two projects handed on show the same. */
function same(a: ShownProject | undefined, b: ShownProject): boolean {
  return (
    a?.project_id === b.project_id &&
    a.label === b.label &&
    a.code === b.code &&
    a.state === b.state
  );
}

/** A store of the project shown, none yet. */
function shownStore(): ShownStore {
  let shown: ShownProject | undefined;
  const listeners = new Set<() => void>();
  return {
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    read: () => shown,
    show: (project) => {
      if (same(shown, project)) {
        return;
      }
      shown = project;
      for (const listener of listeners) {
        listener();
      }
    },
  };
}

/** Outside the shell — a component rendered alone, in a test —: nothing shown, nothing kept. */
const NO_STORE: ShownStore = {
  subscribe: () => () => undefined,
  read: () => undefined,
  show: () => undefined,
};

const ShownContext = createContext<ShownStore>(NO_STORE);

/** What the server renders: no project handed on yet. */
function noneShown(): undefined {
  return undefined;
}

/** Keep the project the screens hand on, for the shell within it. */
export function ShownProjectProvider({ children }: { readonly children: ReactNode }) {
  const [store] = useState(shownStore);
  return <ShownContext value={store}>{children}</ShownContext>;
}

/** The project handed on, if it is the one the address names; `undefined` otherwise. */
export function useShownProject(projectId: string | undefined): ShownProject | undefined {
  const store = useContext(ShownContext);
  const shown = useSyncExternalStore(store.subscribe, store.read, noneShown);
  return projectId !== undefined && shown?.project_id === projectId ? shown : undefined;
}

/**
 * Hand the project of the screen on to the shell; nothing outside it — a component rendered
 * alone, in a test.
 */
export function ShowProject({ project }: { readonly project: ShownProject }) {
  const { show } = useContext(ShownContext);
  const { project_id, label, state } = project;
  const code = project.code ?? null;
  useEffect(() => {
    show({ project_id, label, code, state });
  }, [show, project_id, label, code, state]);
  return null;
}
