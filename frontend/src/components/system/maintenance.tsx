// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The maintenance of a restoration of the platform, as a screen reads it (WF-ADM-0160, #604): the
 * restoration closes every session, and the API answers nothing but its probe (`getLiveness`) until
 * it is done. The screen that asked it follows its task while the platform still serves, then the
 * probe; any other screen — the screen of failure, which whoever meets the maintenance sees — the
 * probe alone. Said in place of the screen: the platform under maintenance and every user signed
 * out, then the restoration done and the way to sign in again.
 */
"use client";

import { CircleCheck, LoaderCircle, Wrench } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { type Liveness, readLiveness } from "@/api/actions/backups";
import { readBackgroundTask } from "@/api/actions/tasks";
import type { Problem } from "@/api/problem";
import { SignIn } from "@/components/commands/outcome-notice";

/** How long the screen waits before asking again where the restoration stands, in ms. */
export const RESTORATION_POLL = 2000;

/**
 * Where a restoration stands, as the screen reads it: `asking`, nothing read yet; `serving`, the
 * platform serves and no restoration was followed; `queued`, the task waits, the platform serving;
 * `maintenance`; `done`, the maintenance lifted, the sessions closed; `failed`, refused before the
 * maintenance, with its motive.
 */
export type RestorationPhase =
  | { readonly kind: "asking" | "serving" | "queued" | "maintenance" | "done" }
  | { readonly kind: "failed"; readonly problem: Problem };

/** The motive of a task that failed without one: the unexpected error. */
const UNEXPECTED: Problem = { code: "INTERNAL_ERROR", status: 500 };

const QUEUED: RestorationPhase = { kind: "queued" };
const DONE: RestorationPhase = { kind: "done" };

/** The phases after which nothing more is asked. */
const ENDED: ReadonlySet<RestorationPhase["kind"]> = new Set(["serving", "done", "failed"]);

/**
 * Where a restoration stands by its task, the platform serving: done once it succeeded — or once
 * it cannot be read for want of a session, the restoration having closed them all —, failed with
 * its motive, or still to come.
 */
async function taskPhase(taskId: string): Promise<RestorationPhase> {
  const read = await readBackgroundTask(taskId);
  if (read.kind === "signed_out") {
    return DONE;
  }
  if (read.kind !== "done") {
    return QUEUED;
  }
  if (read.data.status === "failed") {
    return { kind: "failed", problem: read.data.problem ?? UNEXPECTED };
  }
  return read.data.status === "succeeded" ? DONE : QUEUED;
}

/**
 * Where a restoration stands by what the probe says, and whether a maintenance was seen; the task
 * read when there is one and the platform serves; `undefined` when nothing can be said yet.
 */
async function phaseOf(
  live: Liveness,
  seen: boolean,
  taskId: string | undefined,
): Promise<RestorationPhase | undefined> {
  if (live === "maintenance") {
    return { kind: "maintenance" };
  }
  if (seen) {
    return live === "ok" ? DONE : undefined;
  }
  if (taskId === undefined) {
    return { kind: "serving" };
  }
  return live === "ok" ? taskPhase(taskId) : undefined;
}

/**
 * Follow the platform until a restoration is done: the task given, while the platform serves, then
 * the probe; with no task, the probe alone, which says `serving` at once unless a maintenance is
 * under way. A maintenance seen, the platform serving again is the restoration done. An answer
 * that comes once the screen is gone, or follows another task, is dropped.
 */
export function useRestorationPhase(taskId: string | undefined): RestorationPhase {
  const [phase, setPhase] = useState<RestorationPhase>({ kind: "asking" });
  useEffect(() => {
    let stopped = false;
    let seen = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const step = async () => {
      const live = await readLiveness();
      seen ||= live === "maintenance";
      const next = stopped ? undefined : await phaseOf(live, seen, taskId);
      if (stopped) {
        return;
      }
      if (next !== undefined) {
        setPhase(next);
      }
      if (next === undefined || !ENDED.has(next.kind)) {
        timer = setTimeout(() => void step(), RESTORATION_POLL);
      }
    };
    void step();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [taskId]);
  return phase;
}

/**
 * The screen of a restoration under way, or done: that the platform is under maintenance and every
 * user signed out until it ends; then that it is done, and the way to sign in again.
 */
export function RestorationNotice({ done }: { readonly done: boolean }) {
  const t = useTranslations("maintenance");
  return (
    <section role="status" aria-label={t("title")} className="max-w-prose space-y-2 text-sm">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        {done ? (
          <CircleCheck aria-hidden="true" className="size-5 shrink-0" />
        ) : (
          <Wrench aria-hidden="true" className="size-5 shrink-0" />
        )}
        {done ? t("doneTitle") : t("title")}
      </h1>
      {done ? (
        <>
          <p>{t("done")}</p>
          <SignIn reauthenticate />
        </>
      ) : (
        <p className="flex items-start gap-1.5">
          <LoaderCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 animate-spin" />
          {t("maintenance")}
        </p>
      )}
    </section>
  );
}
