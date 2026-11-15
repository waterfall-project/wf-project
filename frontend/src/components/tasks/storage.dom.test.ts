// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it } from "vitest";

import type { BackgroundTask } from "@/api/problem";
import { example } from "@/test/fixtures";

import { type KeptTask, restoreTasks, saveTasks, STORAGE_KEY } from "./storage";
import { NOTHING_TRACKED, taskAim, tracking } from "./tracking";

const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const AIM = taskAim("revision_mark", REVISION);

/** The marking of the contract, queued, handed over to the tracker with its aim. */
function handedOver(aim: string | undefined) {
  const task = example("task_mark_queued") as BackgroundTask;
  return tracking(NOTHING_TRACKED, { type: "track", task, launch: { subject: "V2", aim } }).tasks;
}

/** What the tab keeps, as it reads it. */
function kept(): unknown {
  return JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null");
}

/** Keep a value in the storage of the tab, as a former version of the front may have. */
function keep(value: readonly unknown[]) {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

/** A task kept by the tab, running. */
const KEPT: KeptTask = {
  key: "01926f3a-7c00-7000-8000-000000000931",
  task_id: "01926f3a-7c00-7000-8000-000000000931",
  kind: "revision_mark",
  status: "queued",
  subject: "V2",
  aim: AIM,
};

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("the aim of a task kept by the tab", () => {
  it("is kept with the task, and read back with it [WF-IHM-0080-A]", () => {
    // The button that started the task finds it again by its aim after a reload (#3404).
    saveTasks(handedOver(AIM));
    expect(kept()).toEqual([KEPT]);
    expect(restoreTasks().map(({ key, aim, subject }) => ({ key, aim, subject }))).toEqual([
      { key: KEPT.key, aim: AIM, subject: "V2" },
    ]);
  });

  it("is none for a task handed over without one, kept and read back without it", () => {
    saveTasks(handedOver(undefined));
    expect(kept()).toEqual([{ ...KEPT, aim: undefined }]);
    expect(restoreTasks()[0]?.aim).toBeUndefined();
  });

  it("discards a task whose aim read back has not its shape", () => {
    keep([
      { ...KEPT, aim: 42 },
      { ...KEPT, key: "other", task_id: "other", aim: null },
    ]);
    expect(restoreTasks()).toEqual([]);
  });
});
