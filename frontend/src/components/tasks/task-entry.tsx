// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * One background task the tracker follows (WF-IHM-0080): what it is — its kind, and what the
 * user named it after —, where it stands, how far it has gone while it runs, and, failed, its
 * motive in a sentence of the catalogue and the offer to run the same command again. While the
 * task runs, the entry asks the server where it stands, by a server action, every so often;
 * it stops once the task has ended, once the API refuses to say, and when it is dismissed or
 * the shell goes away.
 *
 * The end of a task is announced apart, in a live region (`Announcement`): a progress that
 * moves is not read out at every step, an end is.
 */
"use client";

import { X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type Dispatch, useEffect, useRef, useTransition } from "react";

import { readBackgroundTask } from "@/api/actions/tasks";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";

import { isPolled, RUNNING, type TrackedTask, type TrackingEvent } from "./tracking";

/** How long an entry waits before asking again where its running task stands, in ms. */
export const POLL_INTERVAL = 2000;

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<BackgroundTask> = { kind: "unreachable" };

/** What a task is called: its kind, and what the user named it after when there is one. */
function useTaskName({ task, subject }: TrackedTask): string {
  const t = useTranslations();
  const kind = t(`enums.BackgroundTaskRef.kind.${task.kind}`);
  return subject === undefined ? kind : t("tasks.named", { kind, subject });
}

/** The sentence of the motive of a failed task, from its envelope. */
function Motive({ task }: { readonly task: BackgroundTask }) {
  const locale = useLocale();
  const messages = useMessages();
  return task.problem == null ? null : <p>{problemMessage(task.problem, { locale, messages })}</p>;
}

/**
 * The announcement of the end of a task, success or failure with its motive, in a live region
 * present before it speaks; read by a screen reader, while the entry shows the same state.
 */
export function Announcement({ entry }: { readonly entry: TrackedTask | undefined }) {
  return (
    <div role="status" aria-live="polite" className="sr-only">
      {entry === undefined || RUNNING[entry.task.status] ? null : <End entry={entry} />}
    </div>
  );
}

/** The sentence of the end of a task. */
function End({ entry }: { readonly entry: TrackedTask }) {
  const t = useTranslations("tasks");
  const task = useTaskName(entry);
  return entry.task.status === "succeeded" ? (
    <p>{t("succeeded", { task })}</p>
  ) : (
    <>
      <p>{t("failed", { task })}</p>
      <Motive task={entry.task} />
    </>
  );
}

/** How far a running task has gone, when the API says it; a bar without a value otherwise. */
function Progress({
  name,
  progress,
}: {
  readonly name: string;
  readonly progress: number | undefined;
}) {
  const t = useTranslations("tasks");
  return (
    <div className="flex items-center gap-2">
      <div
        role="progressbar"
        aria-label={name}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
        className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
      >
        {progress === undefined ? null : (
          <div className="h-full bg-primary" style={{ width: `${String(progress)}%` }} />
        )}
      </div>
      {progress === undefined ? null : <span>{t("progress", { progress })}</span>}
    </div>
  );
}

/**
 * Ask the server where a task stands, a while after each answer, as long as it is polled. The
 * answer is applied to the task it was asked for: dismissed or relaunched meanwhile, it is
 * dropped — the tracker checks the task, and an entry gone asks nothing more.
 */
function usePolling(entry: TrackedTask, dispatch: Dispatch<TrackingEvent>) {
  useEffect(() => {
    if (!isPolled(entry)) {
      return undefined;
    }
    const { key } = entry;
    const taskId = entry.task.task_id;
    let live = true;
    const timer = setTimeout(() => {
      void readBackgroundTask(taskId).then(
        (outcome) => {
          if (live) {
            dispatch({ type: "answer", key, taskId, outcome });
          }
        },
        () => {
          if (live) {
            dispatch({ type: "answer", key, taskId, outcome: UNREACHABLE });
          }
        },
      );
    }, POLL_INTERVAL);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [entry, dispatch]);
}

/** What the entry of a task shows, and what it does. */
export interface TaskEntryProps {
  readonly entry: TrackedTask;
  readonly dispatch: Dispatch<TrackingEvent>;
}

/** Show a task the tracker follows, follow it while it runs, and offer to run it again failed. */
export function TaskEntry({ entry, dispatch }: TaskEntryProps) {
  const t = useTranslations();
  const [pending, startTransition] = useTransition();
  const dismiss = useRef<HTMLButtonElement>(null);
  usePolling(entry, dispatch);
  const name = useTaskName(entry);
  const { key, task, command } = entry;
  const relaunch = () => {
    if (command === undefined || pending) {
      return;
    }
    startTransition(async () => {
      const outcome = await command().catch(() => UNREACHABLE);
      dispatch({ type: "answer", key, taskId: task.task_id, outcome });
      if (outcome.kind === "done") {
        // The button pressed goes with the failure: the focus stays within the entry.
        dismiss.current?.focus();
      }
    });
  };
  return (
    <div className="space-y-1 text-sm">
      <div className="flex items-center gap-2">
        <p className="mr-auto font-medium">{name}</p>
        <p className="text-muted-foreground">
          {t(`enums.BackgroundTaskRef.status.${task.status}`)}
        </p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          ref={dismiss}
          aria-label={t("tasks.dismiss", { task: name })}
          onClick={() => {
            dispatch({ type: "dismiss", key });
          }}
        >
          <X aria-hidden />
        </Button>
      </div>
      {RUNNING[task.status] ? <Progress name={name} progress={task.progress} /> : null}
      {task.status === "failed" ? <Motive task={task} /> : null}
      {task.status === "failed" && command !== undefined ? (
        <Button type="button" variant="outline" size="sm" aria-busy={pending} onClick={relaunch}>
          {t("tasks.relaunch")}
        </Button>
      ) : null}
      <OutcomeNotice
        outcome={entry.outcome}
        onClear={() => {
          dispatch({ type: "clear", key });
        }}
      />
    </div>
  );
}
