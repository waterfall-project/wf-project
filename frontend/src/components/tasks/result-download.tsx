// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The download of the file a background task made — an export —, made on demand and not kept
 * (WF-DAT-0120), which the server of Next hands on from the API as a stream
 * (`app/tasks/[taskId]/result`). Before each download, the task is read anew (`getBackgroundTask`,
 * #329): its answer is applied to the task as a read of its progress is — a refusal is told by the
 * notice of its entry, and noted in the history of the messages —, and only a task that still gives
 * a result lets the download leave. What the route refuses afterwards — the result expired or not
 * ready between the read and the download (409) — sends the browser back to the screen it left from,
 * where the tracker tells it (#416).
 *
 * The download is offered by the entry of the task in the panel and by the card of its end; and it
 * leaves by itself once the task has succeeded, when the screen that asked for the export still
 * shows (#3103, `useDownloadWhenTaskSucceeds` of the tracker): a task that ends while the user is
 * elsewhere downloads nothing by itself — its card offers it.
 */
"use client";

import { Download } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  type ComponentProps,
  type Dispatch,
  type MouseEvent,
  useEffect,
  useRef,
  useTransition,
} from "react";

import { readBackgroundTask } from "@/api/actions/tasks";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { rejected } from "@/components/commands/rejection";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";

import { resultHref, withoutRefusal } from "./result-refusal";
import { type EndLine, givesFile, type TrackingEvent } from "./tracking";

/**
 * Read the task anew before its result is downloaded, and apply the answer to the task followed
 * under `key`: what it gives back is the answer, and whether the result is still there.
 */
async function checkResult(
  key: string,
  task: BackgroundTask,
  dispatch: Dispatch<TrackingEvent>,
): Promise<{ readonly outcome: Outcome<BackgroundTask>; readonly there: boolean }> {
  const outcome = await readBackgroundTask(task.task_id).catch(rejected);
  dispatch({ type: "answer", source: "download", key, taskId: task.task_id, outcome });
  return { outcome, there: outcome.kind === "done" && outcome.data.result_url != null };
}

/** The screen shown, from which a download leaves, without a refusal it may carry. */
function useShownScreen(): string {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  return withoutRefusal({ pathname, search });
}

/** What the offer to download a result reads, and what it tells. */
export interface DownloadResultProps extends Omit<
  ComponentProps<"a">,
  "href" | "children" | "aria-label" | "aria-busy"
> {
  /** The key the task is followed under, which the answer of the read is applied to. */
  readonly taskKey: string;
  readonly task: BackgroundTask;
  /** The name of the task, which the name of the link carries. */
  readonly name: string;
  /** What the link says. */
  readonly label: string;
  readonly dispatch: Dispatch<TrackingEvent>;
  /** Told the answer of the read before the download, the download left or not. */
  readonly onChecked?: (outcome: Outcome<BackgroundTask>, left: boolean) => void;
}

/**
 * The offer to download the file a task made. The link leaves once the server has said the result is
 * still there, and only if the offer still shows. It has no `download`: a refusal of the route brings
 * the browser back to the screen, which a download would save as a file.
 */
export function DownloadResult({
  taskKey,
  task,
  name,
  label,
  dispatch,
  onChecked,
  onClick,
  className,
  ...link
}: DownloadResultProps) {
  const t = useTranslations("tasks");
  const [pending, startTransition] = useTransition();
  const from = useShownScreen();
  // Whether the click is the one the check lets through, to the browser.
  const through = useRef(false);
  // Whether the offer is still shown: gone during the read, it downloads nothing.
  const shown = useRef(true);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
  const download = (event: MouseEvent<HTMLAnchorElement>) => {
    // What wraps the link — a tooltip — hears the click too.
    onClick?.(event);
    if (through.current) {
      through.current = false;
      return;
    }
    event.preventDefault();
    if (pending) {
      return;
    }
    const link = event.currentTarget;
    startTransition(async () => {
      const { outcome, there } = await checkResult(taskKey, task, dispatch);
      const left = shown.current && there;
      if (left) {
        through.current = true;
        link.click();
      }
      onChecked?.(outcome, left);
    });
  };
  return (
    <a
      {...link}
      href={resultHref(task.task_id, from)}
      aria-label={t("downloadLabel", { task: name })}
      aria-busy={pending}
      className={cn(buttonVariants({ variant: "outline", size: "sm" }), className)}
      onClick={download}
    >
      <Download aria-hidden="true" />
      {label}
    </a>
  );
}

/**
 * Download the result of a task that has succeeded, the screen shown being the one it leaves from —
 * read anew first, as an offer to download is —, and only if `still` says so once the read has
 * answered: the screen that asked for it still shows. Nothing for a task without a file.
 */
export function downloadWhenThere(
  line: EndLine,
  dispatch: Dispatch<TrackingEvent>,
  still: () => boolean,
): void {
  if (!givesFile(line.task)) {
    return;
  }
  void checkResult(line.key, line.task, dispatch).then(({ there }) => {
    if (there && still()) {
      follow(resultHref(line.task.task_id, withoutRefusal(window.location)));
    }
  });
}

/** Follow a link the screen does not show, as a click of the user would: the browser downloads. */
function follow(href: string): void {
  const link = document.createElement("a");
  link.href = href;
  document.body.append(link);
  link.click();
  link.remove();
}
