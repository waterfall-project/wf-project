// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * One background task the tracker follows (WF-IHM-0080): what it is — its kind, and what the
 * user named it after —, where it stands, how far it has gone while it runs, and, failed, its
 * motive in a sentence of the catalogue and the offer to run the same command again — or,
 * without the command, the way to do it from the screen of its object —; succeeded, the offer
 * to read the screen anew, and to download its result when it made a file — an export —, which
 * the server of Next hands on from the API as a stream (`app/tasks/[taskId]/result`). Before each
 * download, the entry reads the task anew (`getBackgroundTask`, #329): a refusal of that read — the
 * task unknown, the session lost — is told by the notice of the entry, and a task that no longer
 * gives a result (`result_url` none) is said so in place of the offer; only a task that still gives
 * one lets the download leave, and only if the entry is still there. What the route refuses
 * afterwards — the result expired or not ready between the read and the download (409) — sends the
 * browser back to the screen, where the tracker tells it by the same notice (#416). While the task
 * runs, the shell asks the server where it stands, by a server action, every so often, whether its
 * entry shows or not (`TaskPolling`) — the panel that shows the entries comes and goes —; it stops
 * once the task has ended, once the API refuses to say — the follow-up is then interrupted, and the
 * entry says so —, and when it is dismissed or the shell goes away.
 *
 * The ends are read out apart, in a log (`EndLog`): a progress that moves is not read out at
 * every step, an end is, and the ends add up. Each end is noted in the history of the messages,
 * with the screen the task was started from.
 */
"use client";

import { RefreshCw, RotateCcw, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type Dispatch, useCallback, useEffect, useMemo, useRef, useTransition } from "react";

import { readBackgroundTask } from "@/api/actions/tasks";
import type { BackgroundTask, Outcome, Problem } from "@/api/problem";
import { heldAttributes } from "@/components/commands/held-attributes";
import {
  OutcomeNotice,
  SignIn,
  useNoteRefusal,
  useReadAnew,
} from "@/components/commands/outcome-notice";
import { useHeldCommand } from "@/components/commands/held";
import { useNoteMessage } from "@/components/notices/message-history";
import { rejectedRead } from "@/components/commands/rejection";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";
import { asksIdentifiers } from "@/navigation/login";

import { DownloadResult } from "./result-download";
import {
  type EndKind,
  type EndLine,
  givesFile,
  isPolled,
  type Refusal,
  type TrackedTask,
  type TrackingEvent,
} from "./tracking";

/** How long an entry waits before asking again where its running task stands, in ms. */
export const POLL_INTERVAL = 2000;

/** The sentence of each end, by how it ended. */
export const END_SENTENCE: Readonly<Record<EndKind, "succeeded" | "failed" | "interruptedLine">> = {
  succeeded: "succeeded",
  failed: "failed",
  interrupted: "interruptedLine",
};

/** What names a task, in the language of the interface: its kind, and a kind with a subject. */
export interface TaskNaming {
  readonly kind: (kind: BackgroundTask["kind"]) => string;
  readonly named: (kind: string, subject: string) => string;
}

/** What names a task, in the language of the interface. */
export function useTaskNaming(): TaskNaming {
  const kinds = useTranslations("enums.BackgroundTaskRef.kind");
  const t = useTranslations("tasks");
  return useMemo(
    () => ({
      kind: (kind) => kinds(kind),
      named: (kind, subject) => t("named", { kind, subject }),
    }),
    [kinds, t],
  );
}

/** What a task is called: its kind, and what the user named it after when there is one. */
export function taskName(
  naming: TaskNaming,
  { task, subject }: Pick<TrackedTask, "task" | "subject">,
): string {
  const kind = naming.kind(task.kind);
  return subject === undefined ? kind : naming.named(kind, subject);
}

/** What a task is called, in the language of the interface. */
export function useTaskName(named: Pick<TrackedTask, "task" | "subject">): string {
  return taskName(useTaskNaming(), named);
}

/** The sentence of a motive — of a failure, of a refusal —, from its envelope. */
export function Motive({ problem }: { readonly problem: Problem | null | undefined }) {
  const locale = useLocale();
  const messages = useMessages();
  return problem == null ? null : <p>{problemMessage(problem, { locale, messages })}</p>;
}

/**
 * One end of the log: the sentence of the end, and its motive when it has one — noted, once, in the
 * history of the messages, with the screen the task was started from.
 */
function End({ line }: { readonly line: EndLine }) {
  const t = useTranslations("tasks");
  const locale = useLocale();
  const messages = useMessages();
  const task = useTaskName(line);
  const sentence = t(END_SENTENCE[line.end], { task });
  const { problem } = line;
  useNoteMessage(line, {
    tone: line.end === "succeeded" ? "success" : "refusal",
    sentence,
    detail: problem === undefined ? undefined : problemMessage(problem, { locale, messages }),
    object: task,
    reference: problem?.code === "INTERNAL_ERROR" ? problem.correlation_id : undefined,
    screen: line.from,
  });
  return (
    <div>
      <p>{sentence}</p>
      <Motive problem={problem} />
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

/** How far a running task has gone, as the API says it. */
function Progress({
  name,
  progress,
}: {
  readonly name: string;
  /** None while the progress is not known yet: a bar without a value. */
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
        <div className="h-full bg-primary" style={{ width: `${String(progress ?? 0)}%` }} />
      </div>
      {progress === undefined ? null : <span>{t("progress", { progress })}</span>}
    </div>
  );
}

/**
 * The offer to read the screen anew once a task has succeeded: what it changed shows only then.
 * The tracker reads anew by itself only a screen the task concerns — of its project, or the one it
 * was started from (`readsAnew`) —; on another, the user decides, and the panel closes on the
 * screen read anew.
 */
function ReloadScreen({ onShown }: { readonly onShown: () => void }) {
  const t = useTranslations("tasks");
  const router = useRouter();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        router.refresh();
        onShown();
      }}
    >
      <RefreshCw aria-hidden="true" />
      {t("reload")}
    </Button>
  );
}

/** Why the follow-up stopped: the refusal of the API, and the way to sign in without a session. */
function Interruption({ refusal }: { readonly refusal: Refusal }) {
  return (
    <>
      <Motive problem={refusal.problem} />
      {refusal.kind === "signed_out" ? (
        <SignIn reauthenticate={asksIdentifiers(refusal.problem.code)} />
      ) : null}
    </>
  );
}

/**
 * Ask the server where a task stands, a while after each answer, as long as it is polled. The
 * answer is applied to the task it was asked for: dismissed or relaunched meanwhile, it is
 * dropped — the tracker checks the task, and an entry gone asks nothing more.
 *
 * The next read is asked by the answer of the last one, not by a new entry: a read that finds the
 * task where it stood leaves the entry as it was (#180), and a follow-up that waited for a new
 * entry stopped there — a task read twice, ended, and never read again (#3103). The loop starts
 * again only for another task — a relaunch — or once the task is polled again.
 */
function usePolling(entry: TrackedTask, dispatch: Dispatch<TrackingEvent>) {
  const { key } = entry;
  const taskId = entry.task.task_id;
  const polled = isPolled(entry);
  useEffect(() => {
    if (!polled) {
      return undefined;
    }
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const ask = () => {
      timer = setTimeout(() => {
        void readBackgroundTask(taskId).then(answered, (error: unknown) => {
          answered(rejectedRead(error));
        });
      }, POLL_INTERVAL);
    };
    // The answer is applied, then the next read is asked: an answer that ends the task, or the
    // follow-up, makes the entry no longer polled, and the cleanup below cancels that read.
    const answered = (outcome: Outcome<BackgroundTask>) => {
      if (live) {
        dispatch({ type: "answer", source: "read", key, taskId, outcome });
        ask();
      }
    };
    ask();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [key, taskId, polled, dispatch]);
}

/** What the entry of a task shows, and what it does. */
export interface TaskEntryProps {
  readonly entry: TrackedTask;
  readonly dispatch: Dispatch<TrackingEvent>;
  /** Stop following the task: the panel takes the focus to where it should go. */
  readonly onDismiss: (key: string) => void;
  /** Hand the panel the button that dismisses the task, to give it the focus. */
  readonly dismissRef: (key: string, button: HTMLButtonElement | null) => void;
  /** Close the panel, the screen read anew under it. */
  readonly onScreenShown: () => void;
}

/**
 * Follow a task while it runs, whether its entry shows or not: the panel that shows the entries
 * comes and goes, the follow-up stays with the shell — and so does the history of the messages, where
 * a refusal of the follow-up, or of a relaunch, is noted as it arrives, the panel closed or open:
 * its entry tells it once the panel shows it, and notes nothing more.
 */
export function TaskPolling({
  entry,
  dispatch,
}: {
  readonly entry: TrackedTask;
  readonly dispatch: Dispatch<TrackingEvent>;
}) {
  usePolling(entry, dispatch);
  const noteRefusal = useNoteRefusal();
  const name = useTaskName(entry);
  const { outcome } = entry;
  useEffect(() => {
    if (outcome !== undefined) {
      noteRefusal(outcome, { subject: name });
    }
  }, [outcome, noteRefusal, name]);
  return null;
}

/** Show a task the tracker follows, and offer to run it again failed. */
export function TaskEntry({
  entry,
  dispatch,
  onDismiss,
  dismissRef,
  onScreenShown,
}: TaskEntryProps) {
  const t = useTranslations();
  const [pending, startTransition] = useTransition();
  const held = useHeldCommand();
  const dismiss = useRef<HTMLButtonElement | null>(null);
  const { key, task, command, interrupted } = entry;
  const setDismiss = useCallback(
    (button: HTMLButtonElement | null) => {
      dismiss.current = button;
      dismissRef(key, button);
    },
    [key, dismissRef],
  );
  const name = useTaskName(entry);
  // A relaunch lost once sent: the button waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(entry.outcome);
  const relaunch = () => {
    if (command === undefined || pending || reading) {
      return;
    }
    startTransition(async () => {
      const outcome = await held(command());
      dispatch({ type: "answer", source: "relaunch", key, taskId: task.task_id, outcome });
      if (outcome.kind === "done" || outcome.kind === "stale") {
        // The button pressed goes — with the failure, or with the command refused as stale —:
        // the focus stays within the entry, on its dismissal.
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
            ? t(`enums.BackgroundTaskStatus.${task.status}`)
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
          onClick={() => {
            if (!pending) {
              onDismiss(key);
            }
          }}
        >
          <X aria-hidden />
        </Button>
      </div>
      {isPolled(entry) ? (
        <Progress
          name={name}
          progress={entry.progressUnknown === true ? undefined : task.progress}
        />
      ) : null}
      {interrupted === undefined ? null : <Interruption refusal={interrupted} />}
      {task.status === "succeeded" ? <ReloadScreen onShown={onScreenShown} /> : null}
      {givesFile(task) ? (
        <DownloadResult
          taskKey={key}
          task={task}
          name={name}
          label={t("tasks.download")}
          dispatch={dispatch}
        />
      ) : null}
      {entry.resultUnavailable === true ? (
        <p role="alert" className="text-destructive">
          {t("tasks.resultUnavailable")}
        </p>
      ) : null}
      {failed ? <Motive problem={task.problem} /> : null}
      {failed && command !== undefined ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={t("tasks.relaunchLabel", { task: name })}
          {...heldAttributes(pending, reading)}
          onClick={relaunch}
        >
          <RotateCcw aria-hidden="true" />
          {t("tasks.relaunch")}
        </Button>
      ) : null}
      {failed && command === undefined ? (
        <p className="text-muted-foreground">{t("tasks.relaunchFromScreen")}</p>
      ) : null}
      <OutcomeNotice
        outcome={entry.outcome}
        reading={reading}
        onClear={() => {
          dispatch({ type: "clear", key });
        }}
        subject={name}
      />
    </div>
  );
}
