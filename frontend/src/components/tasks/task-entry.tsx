// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * One background task the tracker follows (WF-IHM-0080): what it is — its kind, and what the
 * user named it after —, where it stands, how far it has gone while it runs, and, failed, its
 * motive in a sentence of the catalogue and the offer to run the same command again — or,
 * without the command, the way to do it from the screen of its object —; succeeded, the offer
 * to read the screen anew. While the task runs,
 * the entry asks the server where it stands, by a server action, every so often; it stops once
 * the task has ended, once the API refuses to say — the follow-up is then interrupted, and the
 * entry says so —, and when it is dismissed or the shell goes away.
 *
 * The ends are read out apart, in a log (`EndLog`): a progress that moves is not read out at
 * every step, an end is, and the ends add up.
 */
"use client";

import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type Dispatch, useCallback, useEffect, useRef, useTransition } from "react";

import { readBackgroundTask } from "@/api/actions/tasks";
import type { BackgroundTask, Outcome, Problem } from "@/api/problem";
import { OutcomeNotice, SignIn } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";

import {
  type EndKind,
  type EndLine,
  isPolled,
  type Refusal,
  type TrackedTask,
  type TrackingEvent,
} from "./tracking";

/** How long an entry waits before asking again where its running task stands, in ms. */
export const POLL_INTERVAL = 2000;

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<BackgroundTask> = { kind: "unreachable" };

/** The sentence of each end, by how it ended. */
const END_SENTENCE: Readonly<Record<EndKind, "succeeded" | "failed" | "interruptedLine">> = {
  succeeded: "succeeded",
  failed: "failed",
  interrupted: "interruptedLine",
};

/** What a task is called: its kind, and what the user named it after when there is one. */
function useTaskName({ task, subject }: Pick<TrackedTask, "task" | "subject">): string {
  const t = useTranslations();
  const kind = t(`enums.BackgroundTaskRef.kind.${task.kind}`);
  return subject === undefined ? kind : t("tasks.named", { kind, subject });
}

/** The sentence of a motive — of a failure, of a refusal —, from its envelope. */
function Motive({ problem }: { readonly problem: Problem | null | undefined }) {
  const locale = useLocale();
  const messages = useMessages();
  return problem == null ? null : <p>{problemMessage(problem, { locale, messages })}</p>;
}

/** One end of the log: the sentence of the end, and its motive when it has one. */
function End({ line }: { readonly line: EndLine }) {
  const t = useTranslations("tasks");
  const task = useTaskName(line);
  return (
    <div>
      <p>{t(END_SENTENCE[line.end], { task })}</p>
      <Motive problem={line.problem} />
    </div>
  );
}

/**
 * The log of the ends of the tasks — succeeded, failed with its motive, follow-up interrupted
 * —, a live region mounted with the shell, before it ever speaks: each end is added, and read
 * out, while the entry shows the same state.
 */
export function EndLog({ log }: { readonly log: readonly EndLine[] }) {
  return (
    <div role="log" className="sr-only">
      {log.map((line) => (
        <End key={line.id} line={line} />
      ))}
    </div>
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
 * The offer to read the screen anew once a task has succeeded: what it changed shows only then.
 * The tracker never reloads by itself — the screen may hold what the user is typing —: the user
 * decides.
 */
function ReloadScreen() {
  const t = useTranslations("tasks");
  const router = useRouter();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        router.refresh();
      }}
    >
      {t("reload")}
    </Button>
  );
}

/** Why the follow-up stopped: the refusal of the API, and the way to sign in without a session. */
function Interruption({ refusal }: { readonly refusal: Refusal }) {
  return (
    <>
      <Motive problem={refusal.problem} />
      {refusal.kind === "signed_out" ? <SignIn /> : null}
    </>
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
    const answered = (outcome: Outcome<BackgroundTask>) => {
      if (live) {
        dispatch({ type: "answer", source: "read", key, taskId, outcome });
      }
    };
    const timer = setTimeout(() => {
      void readBackgroundTask(taskId).then(answered, () => {
        answered(UNREACHABLE);
      });
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
  /** Stop following the task: the panel takes the focus to where it should go. */
  readonly onDismiss: (key: string) => void;
  /** Hand the panel the button that dismisses the task, to give it the focus. */
  readonly dismissRef: (key: string, button: HTMLButtonElement | null) => void;
}

/** Show a task the tracker follows, follow it while it runs, and offer to run it again failed. */
export function TaskEntry({ entry, dispatch, onDismiss, dismissRef }: TaskEntryProps) {
  const t = useTranslations();
  const [pending, startTransition] = useTransition();
  const dismiss = useRef<HTMLButtonElement | null>(null);
  const { key, task, command, interrupted } = entry;
  const setDismiss = useCallback(
    (button: HTMLButtonElement | null) => {
      dismiss.current = button;
      dismissRef(key, button);
    },
    [key, dismissRef],
  );
  usePolling(entry, dispatch);
  const name = useTaskName(entry);
  const relaunch = () => {
    if (command === undefined || pending) {
      return;
    }
    startTransition(async () => {
      const outcome = await command().catch(() => UNREACHABLE);
      dispatch({ type: "answer", source: "relaunch", key, taskId: task.task_id, outcome });
      if (outcome.kind === "done") {
        // The button pressed goes with the failure: the focus stays within the entry.
        dismiss.current?.focus();
      }
    });
  };
  const failed = task.status === "failed";
  return (
    <div className="space-y-1 text-sm">
      <div className="flex items-center gap-2">
        <p className="mr-auto font-medium">{name}</p>
        <p className="text-muted-foreground">
          {interrupted === undefined
            ? t(`enums.BackgroundTaskRef.status.${task.status}`)
            : t("tasks.interrupted")}
        </p>
        {/* Dismissed while it runs again, the task relaunched would be lost: it waits. */}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          ref={setDismiss}
          aria-label={t("tasks.dismiss", { task: name })}
          aria-disabled={pending ? true : undefined}
          className="aria-disabled:cursor-not-allowed aria-disabled:opacity-50"
          onClick={() => {
            if (!pending) {
              onDismiss(key);
            }
          }}
        >
          <X aria-hidden />
        </Button>
      </div>
      {isPolled(entry) ? <Progress name={name} progress={task.progress} /> : null}
      {interrupted === undefined ? null : <Interruption refusal={interrupted} />}
      {task.status === "succeeded" ? <ReloadScreen /> : null}
      {failed ? <Motive problem={task.problem} /> : null}
      {failed && command !== undefined ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={t("tasks.relaunchLabel", { task: name })}
          aria-busy={pending}
          onClick={relaunch}
        >
          {t("tasks.relaunch")}
        </Button>
      ) : null}
      {failed && command === undefined ? (
        <p className="text-muted-foreground">{t("tasks.relaunchFromScreen")}</p>
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
