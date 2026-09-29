// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { BackgroundTask } from "@/api/problem";
import { example } from "@/test/fixtures";

import { isPolled, NOTHING_TRACKED, type Tracking, tracking } from "./tracking";

const MARKING = "01926f3a-7c00-7000-8000-000000000901";

/** A task of the contract, by the name of its example. */
function task(name: string): BackgroundTask {
  return example(name) as BackgroundTask;
}

/** The tracker once a task has been handed over to it. */
function following(given: BackgroundTask): Tracking {
  return tracking(NOTHING_TRACKED, { type: "track", task: given, launch: {} });
}

describe("what the tracker follows", () => {
  it("drops the answer to a task a relaunch has replaced since it was asked", () => {
    const relaunched = { ...task("task_running"), task_id: "01926f3a-7c00-7000-8000-000000000999" };
    const before = tracking(following(task("task_failed")), {
      type: "answer",
      source: "read",
      key: MARKING,
      taskId: MARKING,
      outcome: { kind: "done", data: relaunched },
    });
    // The read of the failed task, asked before the relaunch, answers late.
    const after = tracking(before, {
      type: "answer",
      source: "read",
      key: MARKING,
      taskId: MARKING,
      outcome: { kind: "done", data: task("task_failed") },
    });
    expect(after).toBe(before);
    expect(after.tasks[0]?.task.status).toBe("running");
  });

  it("drops the answer to a task dismissed since it was asked", () => {
    const dismissed = tracking(following(task("task_running")), { type: "dismiss", key: MARKING });
    const after = tracking(dismissed, {
      type: "answer",
      source: "read",
      key: MARKING,
      taskId: MARKING,
      outcome: { kind: "done", data: task("task_succeeded") },
    });
    expect(after).toBe(dismissed);
    expect(after.tasks).toEqual([]);
  });

  it("logs at once the end of a task handed over already ended", () => {
    expect(following(task("task_succeeded")).log.map((line) => line.end)).toEqual(["succeeded"]);
    expect(following(task("task_running")).log).toEqual([]);
  });

  it("keeps the last ten ends in its log, each added after the one before", () => {
    let state = NOTHING_TRACKED;
    for (let turn = 0; turn < 12; turn += 1) {
      state = tracking(state, { type: "track", task: task("task_failed"), launch: {} });
    }
    expect(state.log.map((line) => line.id)).toEqual([3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
  });

  it("follows a task handed over twice once", () => {
    const twice = tracking(following(task("task_mark_queued")), {
      type: "track",
      task: task("task_running"),
      launch: {},
    });
    expect(twice.tasks.map((tracked) => tracked.task.status)).toEqual(["running"]);
  });

  it("does not follow twice a task restored after it was handed over again", () => {
    const tracked = following(task("task_running"));
    const restored = tracking(tracked, { type: "restore", tasks: tracked.tasks });
    expect(restored.tasks).toHaveLength(1);
    expect(restored.restored).toBe(true);
  });

  it("asks again after the API out of reach, and not after a refusal", () => {
    const [running] = following(task("task_running")).tasks;
    if (running === undefined) {
      throw new Error("the task is followed");
    }
    expect(isPolled(running)).toBe(true);
    expect(isPolled({ ...running, outcome: { kind: "unreachable" } })).toBe(true);
    const problem = { code: "NOT_FOUND", status: 404 } as const;
    expect(
      isPolled({
        ...running,
        interrupted: { kind: "refused", problem, conflictingObjectId: null },
      }),
    ).toBe(false);
    expect(isPolled({ ...running, task: task("task_succeeded") })).toBe(false);
  });

  it("forgets every task and every end once signed out, and drops an answer still on its way", () => {
    const followed = tracking(
      tracking(following(task("task_succeeded")), { type: "restore", tasks: [] }),
      { type: "track", task: task("task_running"), launch: {} },
    );
    const forgotten = tracking(followed, { type: "forget" });
    expect(forgotten).toEqual({ tasks: [], log: [], restored: true });
    const late = tracking(forgotten, {
      type: "answer",
      source: "read",
      key: MARKING,
      taskId: MARKING,
      outcome: { kind: "done", data: task("task_succeeded") },
    });
    expect(late).toBe(forgotten);
  });
});
