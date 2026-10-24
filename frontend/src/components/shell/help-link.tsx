// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A link of a page of the help to another of its pages (WF-IHM-0140, US-0580), followed in the
 * panel without leaving the screen. Apart from the Markdown, so that the panel can show the links
 * of its own parts without loading the renderer of the pages.
 */
"use client";

import type { MouseEvent, ReactNode } from "react";

import { fileOf, type HelpTarget } from "@/help/help";

/** The class of a link of the help, which shows another page of it in the panel. */
const LINK =
  "rounded-sm text-primary underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** A link to another page of the help, followed in the panel. */
export function HelpLink({
  target,
  onFollow,
  children,
}: {
  readonly target: HelpTarget;
  readonly onFollow: (target: HelpTarget) => void;
  readonly children: ReactNode;
}) {
  return (
    <a
      href={`#${fileOf(target)}`}
      className={LINK}
      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault();
        onFollow(target);
      }}
    >
      {children}
    </a>
  );
}
