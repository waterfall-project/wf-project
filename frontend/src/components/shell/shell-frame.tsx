// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What of the shell frames the page the browser shows: the side bar, the bar above the page and
 * the panel of the background tasks. The page keeps its place in the tree.
 */
"use client";

import type { ReactNode } from "react";

import { TaskPanel } from "@/components/tasks/task-tracker";
import { SidebarInset } from "@/components/ui/sidebar";

/**
 * The page bounded to the height of the window when its screen fills it (`Screen`, `fill`) —
 * from the large breakpoint only for a screen that fills it there alone: the bar, the banner and
 * the screen share that height, and the grid of the screen takes what is left. Any other page
 * grows with its content, and the document scrolls.
 */
const FILLED = "has-[main[data-fill]]:h-svh lg:has-[main[data-fill-lg]]:h-svh";

/** The side bar — none without a session —, the bar above the page, and the page. */
export interface ShellFrameProps {
  readonly navigation: ReactNode;
  readonly bar: ReactNode;
  readonly children: ReactNode;
}

/** Render the page in the frame of the shell. */
export function ShellFrame({ navigation, bar, children }: ShellFrameProps) {
  return (
    <>
      {navigation}
      <SidebarInset className={FILLED}>
        {bar}
        <TaskPanel />
        {children}
      </SidebarInset>
    </>
  );
}
