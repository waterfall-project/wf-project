// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The restoration of the platform, on the screen of the backups (US-0440, WF-ADM-0160): once the
 * confirmation of a backup of the list or of a deposit has queued it (`restore-dialog.tsx`), the
 * screen of its maintenance in place of the page.
 *
 * The restoration closes every session and the API answers nothing but its probe until it is done
 * (`getLiveness`, #604): the screen follows the task while the platform still serves — a refusal
 * before the maintenance, an archive of a newer version, comes back to the page —, then the probe,
 * which says the maintenance and its end (`maintenance.tsx`). Done, the sessions closed, the screen
 * offers to sign in again.
 */
"use client";

import { createContext, type ReactNode, use, useCallback, useEffect, useState } from "react";

import type { Outcome, Problem } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { RestorationNotice, useRestorationPhase } from "@/components/system/maintenance";

/** Follow a restoration queued, by its task; nothing outside the screen of the backups. */
const FollowRestoration = createContext<((taskId: string) => void) | undefined>(undefined);

/** The function that hands a restoration queued over to the screen of its maintenance. */
export function useFollowRestoration(): (taskId: string) => void {
  const follow = use(FollowRestoration);
  if (follow === undefined) {
    throw new Error("a restoration is followed within the screen of the backups");
  }
  return follow;
}

/** The task of the restoration followed, until it fails before the maintenance. */
function Followed({
  taskId,
  onFailed,
}: {
  readonly taskId: string;
  readonly onFailed: (problem: Problem) => void;
}) {
  const phase = useRestorationPhase(taskId);
  useEffect(() => {
    if (phase.kind === "failed") {
      onFailed(phase.problem);
    }
  }, [phase, onFailed]);
  return <RestorationNotice phase={phase} />;
}

/**
 * The screen of the backups, which a restoration queued replaces by the screen of its maintenance.
 * A refusal of the task before the maintenance is told above the page given back.
 */
export function Restoration({ children }: { readonly children: ReactNode }) {
  const [taskId, setTaskId] = useState<string>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const failed = useCallback((problem: Problem) => {
    setTaskId(undefined);
    setOutcome({ kind: "refused", problem, conflictingObjectId: null });
  }, []);
  const follow = useCallback((queued: string) => {
    setOutcome(undefined);
    setTaskId(queued);
  }, []);
  if (taskId !== undefined) {
    return <Followed taskId={taskId} onFailed={failed} />;
  }
  return (
    <FollowRestoration value={follow}>
      <OutcomeNotice
        outcome={outcome}
        dismissible
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      {children}
    </FollowRestoration>
  );
}
