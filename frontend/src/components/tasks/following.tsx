// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The follow-up of a task a command handed to the worker (WF-ARC-0090, WF-IHM-0080): the command
 * mounts it with the reference the API gave, and the tracker of the shell follows the task. It is
 * mounted by the confirmation alone, so that a screen that offers the command needs the tracker only
 * to follow a task. Once the task has succeeded the screen is read again, and told.
 */
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import type { BackgroundTask } from "@/api/problem";

import { type TaskCommand } from "./tracking";
import { useTrackTask, useWhenTaskSucceeds } from "./task-tracker";

/** Hand a task to the tracker of the shell, once, and wait for its end. */
export function Following({
  task,
  subject,
  command,
  onSucceeded,
}: {
  readonly task: BackgroundTask;
  /** What the command was about or what the user named it, shown as it was typed. */
  readonly subject: string;
  /**
   * The command that started the task, which a failed task runs again; none when running it again
   * would confirm what the user has not been shown anew (the occurrence of a risk): the entry then
   * says to start it again from the screen of its object.
   */
  readonly command?: TaskCommand | undefined;
  readonly onSucceeded: () => void;
}) {
  const router = useRouter();
  const track = useTrackTask();
  const handed = useRef(false);
  useEffect(() => {
    if (!handed.current) {
      handed.current = true;
      track(task, { command, subject });
    }
  }, [track, task, command, subject]);
  useWhenTaskSucceeds(task.task_id, () => {
    onSucceeded();
    router.refresh();
  });
  return null;
}
