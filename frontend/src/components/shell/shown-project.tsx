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
 */
"use client";

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import type { components } from "@/api/generated/schema";

/** What the shell shows of a project: its identifier, its label, its code and its state. */
export type ShownProject = Pick<
  components["schemas"]["Project"],
  "project_id" | "label" | "code" | "state"
>;

interface Shown {
  readonly shown: ShownProject | undefined;
  readonly show: (project: ShownProject) => void;
}

const ShownContext = createContext<Shown | undefined>(undefined);

/** Keep the project the screens hand on, for the shell within it. */
export function ShownProjectProvider({ children }: { readonly children: ReactNode }) {
  const [shown, show] = useState<ShownProject>();
  const value = useMemo(() => ({ shown, show }), [shown]);
  return <ShownContext value={value}>{children}</ShownContext>;
}

/** The project handed on, if it is the one the address names; `undefined` otherwise. */
export function useShownProject(projectId: string | undefined): ShownProject | undefined {
  const shown = useContext(ShownContext)?.shown;
  return projectId !== undefined && shown?.project_id === projectId ? shown : undefined;
}

/**
 * Hand the project of the screen on to the shell; nothing outside it — a component rendered
 * alone, in a test.
 */
export function ShowProject({ project }: { readonly project: ShownProject }) {
  const show = useContext(ShownContext)?.show;
  const { project_id, label, state } = project;
  const code = project.code ?? null;
  useEffect(() => {
    show?.({ project_id, label, code, state });
  }, [show, project_id, label, code, state]);
  return null;
}
