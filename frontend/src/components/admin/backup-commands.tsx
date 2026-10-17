// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the screen of the backups (US-0440): a backup asked, which the worker takes and
 * the tracker of the shell follows to its end (WF-ADM-0150, WF-ARC-0090); and the refusal of a
 * download, which the route of the archive carries back in the address.
 * Every refusal of the API is told where its command is (`OutcomeNotice`).
 */
"use client";

import { DatabaseBackup } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";

import { startPlatformBackup } from "@/api/actions/backups";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

import { DOWNLOAD_REFUSAL } from "./backup-address";

/** Ask a backup of the platform, and hand its task over to the tracker. */
export function StartBackup() {
  const t = useTranslations("admin.backups");
  const track = useTrackTask();
  const held = useHeldCommand();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const start = () => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      const result = await held(startPlatformBackup());
      if (result.kind === "done") {
        setOutcome(undefined);
        track(result.data, { command: startPlatformBackup });
      } else {
        setOutcome(result);
      }
    });
  };
  return (
    <div className="space-y-2">
      <Button type="button" size="sm" aria-busy={pending} onClick={start}>
        <DatabaseBackup aria-hidden="true" />
        {t("start")}
      </Button>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}

/**
 * The refusal of a download, which the route of the archive carried back in the address: told
 * until dismissed, which takes it away from the address.
 */
export function DownloadRefusal({ refusal }: { readonly refusal: Outcome<never> | undefined }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = new URLSearchParams(useSearchParams());
  search.delete(DOWNLOAD_REFUSAL);
  const kept = search.toString();
  return (
    <OutcomeNotice
      outcome={refusal}
      dismissible
      onClear={() => {
        router.replace(kept === "" ? pathname : `${pathname}?${kept}`, { scroll: false });
      }}
    />
  );
}
