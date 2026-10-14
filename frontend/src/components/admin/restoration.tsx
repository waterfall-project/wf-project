// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The restoration of the platform, on the screen of the backups (US-0440, WF-ADM-0160): the
 * confirmation that names the date of the backup — of the list, or deposited —, and only the whole
 * platform, no part of it; then, the restoration queued, the screen of its maintenance in place of
 * the page.
 *
 * The restoration closes every session and the API answers nothing but its probe until it is done
 * (`getLiveness`, #604): the screen follows the task while the platform still serves — a refusal
 * before the maintenance, an archive of a newer version, comes back to the page —, then the probe,
 * which says the maintenance and its end (`maintenance.tsx`). Done, the sessions closed, the screen
 * offers to sign in again.
 */
"use client";

import { ArchiveRestore, X } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  createContext,
  type ReactNode,
  use,
  useCallback,
  useEffect,
  useState,
  useTransition,
} from "react";

import { type RestoreSource, startPlatformRestore } from "@/api/actions/backups";
import type { Outcome, Problem } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { LocalTime } from "@/components/local-time";
import { RestorationNotice, useRestorationPhase } from "@/components/system/maintenance";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/** A restoration asked: what replaces the platform, and the date of its backup, as the API gave it. */
export interface RestoreAsked {
  readonly source: RestoreSource;
  readonly takenAt: string;
}

/** Ask the confirmation of a restoration; nothing outside the screen of the backups. */
const AskRestore = createContext<((asked: RestoreAsked) => void) | undefined>(undefined);

/** The function that asks the confirmation of a restoration. */
export function useAskRestore(): (asked: RestoreAsked) => void {
  const ask = use(AskRestore);
  if (ask === undefined) {
    throw new Error("a restoration is asked within the screen of the backups");
  }
  return ask;
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
  return <RestorationNotice done={phase.kind === "done"} />;
}

/**
 * The screen of the backups, which a restoration asked replaces by the screen of its maintenance:
 * the confirmation names the date of the backup, as the API gave it, in the local time of the
 * workstation. A refusal of the request, or of the task before the maintenance, is told above the
 * page given back.
 */
export function Restoration({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("admin.restoration");
  const held = useHeldCommand();
  const [asked, setAsked] = useState<RestoreAsked & { readonly open: boolean }>();
  const [taskId, setTaskId] = useState<string>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const failed = useCallback((problem: Problem) => {
    setTaskId(undefined);
    setOutcome({ kind: "refused", problem, conflictingObjectId: null });
  }, []);
  const ask = useCallback((restore: RestoreAsked) => {
    setAsked({ ...restore, open: true });
  }, []);
  const confirmed = (restore: RestoreAsked) => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      const result = await held(startPlatformRestore(restore.source, restore.takenAt));
      if (result.kind === "done") {
        setOutcome(undefined);
        setTaskId(result.data.task_id);
      } else {
        setOutcome(result);
      }
    });
  };
  if (taskId !== undefined) {
    return <Followed taskId={taskId} onFailed={failed} />;
  }
  const date = () => (asked === undefined ? null : <LocalTime value={asked.takenAt} />);
  return (
    <AskRestore value={ask}>
      <OutcomeNotice
        outcome={outcome}
        dismissible
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      {children}
      <AlertDialog
        open={asked?.open ?? false}
        onOpenChange={(open) => {
          if (!open) {
            setAsked((before) => (before === undefined ? before : { ...before, open }));
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("confirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t.rich("confirmText", { time: date })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              <X aria-hidden="true" />
              {t("keep")}
            </AlertDialogCancel>
            <AlertDialogAction
              aria-busy={pending}
              onClick={() => {
                if (asked !== undefined) {
                  confirmed(asked);
                }
              }}
            >
              <ArchiveRestore aria-hidden="true" />
              {t.rich("confirm", { time: date })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AskRestore>
  );
}
