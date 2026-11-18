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
 *
 * Downloaded by itself, no gesture of the user asked for it: it never leaves nor loads the screen
 * again, where the user may be typing. It goes by a hidden frame, which the route answers as the
 * screen would be: the file, which the browser downloads from the frame, as it comes — never held
 * in memory —; or, refused, a page with nothing in it, loaded in the frame without its scripts
 * (`sandbox`), whose address says the refusal (`readRefusal`), told by the card of the end — and,
 * the session having ended, the sign-in page, which says that. Not by
 * `fetch`, which the network guard keeps to the client of the API (WF-ARC-0020), and which would hold
 * the whole file in memory before saving it.
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
import { rejectedRead } from "@/components/commands/rejection";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";
import { LOGIN_ROUTE } from "@/navigation/login";

import {
  readRefusal,
  type ResultRefusal,
  resultHref,
  SESSION_ENDED,
  withoutRefusal,
} from "./result-refusal";
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
  const outcome = await readBackgroundTask(task.task_id).catch(rejectedRead);
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
 * answered: the screen that asked for it still shows. Nothing for a task without a file. The
 * download gone, its card no longer offers the file, served once; refused, its card tells why.
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
    if (!there || !still()) {
      return;
    }
    const href = resultHref(line.task.task_id, withoutRefusal(window.location));
    dispatch({ type: "card_delivered", id: line.id });
    inFrame(href, (refusal) => {
      dispatch({
        type: "card_refused",
        id: line.id,
        key: line.key,
        taskId: line.task.task_id,
        refusal,
      });
    });
  });
}

/**
 * Download the file at an address by a hidden frame, the screen staying as it is: what the route
 * refuses, it sends the frame to a page with nothing in it, the refusal in its address
 * (`app/tasks/[taskId]/refused`, #3297), told to `refused`; a frame that comes to the sign-in page
 * says the session ended.
 * The frame runs no script — the application it would load —, keeps the origin of the screen — the
 * session goes with the request, and its address can be read —, and may download.
 */
function inFrame(href: string, refused: (refusal: ResultRefusal) => void): void {
  const frame = document.createElement("iframe");
  frame.hidden = true;
  frame.setAttribute("sandbox", "allow-downloads allow-same-origin");
  frame.tabIndex = -1;
  frame.setAttribute("aria-hidden", "true");
  // A frame that downloads fires nothing: it goes once the download has long begun.
  const timer = setTimeout(() => {
    frame.remove();
  }, FRAME_KEPT);
  frame.addEventListener("load", () => {
    const shown = frameAddress(frame);
    // A frame that came to the sign-in page — the session ended — carries nothing of the refusal:
    // it is told as the end of the session.
    const refusal = isSignIn(shown.pathname)
      ? SESSION_ENDED
      : readRefusal(new URLSearchParams(shown.search))?.refusal;
    if (refusal === undefined) {
      return;
    }
    clearTimeout(timer);
    frame.remove();
    refused(refusal);
  });
  frame.src = href;
  document.body.append(frame);
}

/** The path and the query of the address a frame shows, empty when they cannot be read. */
function frameAddress(frame: HTMLIFrameElement): { pathname: string; search: string } {
  try {
    const { pathname = "", search = "" } = frame.contentWindow?.location ?? {};
    return { pathname, search };
  } catch {
    // Not proven against a real frame: a policy of headers (`frame-ancestors`, `X-Frame-Options`)
    // would land here, and the refusal would be lost without a sound. No e2e plays the download by
    // itself against the page of a refusal, which the tests of the frame simulate.
    return { pathname: "", search: "" };
  }
}

/** Whether a path is the sign-in page of the front, or one of its pages. */
function isSignIn(pathname: string): boolean {
  return pathname === LOGIN_ROUTE || pathname.startsWith(`${LOGIN_ROUTE}/`);
}

/** How long a frame that downloads is kept: the download it began goes on without it. */
const FRAME_KEPT = 5 * 60_000;
