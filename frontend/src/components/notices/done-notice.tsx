// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a form says once the API has done what it asked — a form of the way in or of the
 * account, the confirmation of an exit of the lifecycle of a project: a status, announced
 * without taking the focus — the refusals, the other outcomes, are `OutcomeNotice`'s. The live
 * region is in place, empty, before it speaks: a region that comes with its text is not always
 * read out. What it says is noted in the history of the messages (`message-history.ts`), once for
 * each outcome it tells.
 */
"use client";

import { CircleCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useShownProjectLabel } from "@/components/shell/shown-project";

import { useNoteMessage } from "./message-history";

/** What was done — nothing yet —, and what may follow it: a link, a way on. */
export interface DoneNoticeProps {
  readonly title: string | undefined;
  readonly children?: ReactNode;
  /**
   * The outcome it tells, which the history of the messages notes once — the same title told of
   * two outcomes, saved twice, is noted twice.
   */
  readonly of: object | undefined;
  /** What the command was about, by its name, which the history of the messages notes. */
  readonly subject?: string | undefined;
}

/** Render what the API has done, or the empty region that will say it. */
export function DoneNotice({ title, children, of, subject }: DoneNoticeProps) {
  useNoteMessage(
    title === undefined ? undefined : of,
    title === undefined ? undefined : { tone: "success", sentence: title, object: subject },
    useShownProjectLabel(),
  );
  return (
    <div role="status" className="empty:hidden">
      {title === undefined ? null : (
        <Alert>
          <CircleCheck aria-hidden="true" />
          <AlertTitle>{title}</AlertTitle>
          {children === undefined ? null : <AlertDescription>{children}</AlertDescription>}
        </Alert>
      )}
    </div>
  );
}
