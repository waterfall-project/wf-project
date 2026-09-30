// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a form of the way in or of the account — or the confirmation of an exit of the lifecycle
 * of a project — says once the API has done what it asked: a status, announced without taking
 * the focus — the refusals, the other outcomes, are `OutcomeNotice`'s. The live region is in place, empty, before it speaks: a region that comes
 * with its text is not always read out.
 */
import { CircleCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

/** What was done — nothing yet —, and what may follow it: a link, a way on. */
export interface DoneNoticeProps {
  readonly title: string | undefined;
  readonly children?: ReactNode;
}

/** Render what the API has done, or the empty region that will say it. */
export function DoneNotice({ title, children }: DoneNoticeProps) {
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
