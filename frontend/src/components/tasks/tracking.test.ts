// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { BackgroundTask } from "@/api/problem";
import { example } from "@/test/fixtures";

import {
  givesFile,
  isPolled,
  NOTHING_TRACKED,
  readsAnew,
  type Tracking,
  tracking,
} from "./tracking";

const MARKING = "01926f3a-7c00-7000-8000-000000000931";

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
    const relaunched = task("task_mark_relaunched");
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
    expect(after.tasks[0]?.task.task_id).toBe(relaunched.task_id);
    expect(after.tasks[0]?.task.status).toBe("queued");
  });

  it("changes nothing, not even the list, when a read finds the task where it stood", () => {
    const before = following(task("task_running"));
    const read = {
      type: "answer",
      source: "read",
      key: MARKING,
      taskId: MARKING,
      outcome: { kind: "done", data: { ...task("task_running") } },
    } as const;
    expect(tracking(before, read)).toBe(before);
    // A task that moved on changes it.
    const moved = tracking(before, {
      ...read,
      outcome: { kind: "done", data: task("task_succeeded") },
    });
    expect(moved).not.toBe(before);
    expect(moved.tasks[0]?.task.status).toBe("succeeded");
  });

  it("tells a refusal of the read before a download in place, and interrupts no follow-up", () => {
    const refusal = {
      kind: "refused",
      problem: { code: "NOT_FOUND", status: 404 },
      conflictingObjectId: null,
    } as const;
    const exported = "01926f3a-7c00-7000-8000-000000000935";
    const before = following(task("task_export_succeeded"));
    const after = tracking(before, {
      type: "answer",
      source: "download",
      key: exported,
      taskId: exported,
      outcome: refusal,
    });
    expect(after.tasks[0]).toMatchObject({ outcome: refusal, interrupted: undefined });
    // The end of the task was logged when it was handed over; the refusal adds no line.
    expect(after.log).toEqual(before.log);
  });

  it("says the result no longer available when the read before a download finds none, and not after any other read", () => {
    const exported = "01926f3a-7c00-7000-8000-000000000935";
    const withoutResult = { ...task("task_export_succeeded"), result_url: null };
    const answered = (source: "read" | "download") =>
      tracking(following(task("task_export_succeeded")), {
        type: "answer",
        source,
        key: exported,
        taskId: exported,
        outcome: { kind: "done", data: withoutResult },
      }).tasks[0];
    expect(answered("download")).toMatchObject({ resultUnavailable: true, task: withoutResult });
    expect(answered("read")).toMatchObject({ resultUnavailable: false });
  });

  it("does not follow a restoration the API lists [WF-ADM-0160-A]", () => {
    const before = following(task("task_running"));
    const restoration = {
      ...task("task_mark_queued"),
      task_id: "restore-1",
      kind: "restore",
    } as const;
    expect(tracking(before, { type: "found", tasks: [restoration] })).toBe(before);
    expect(tracking(NOTHING_TRACKED, { type: "found", tasks: [restoration] })).toBe(
      NOTHING_TRACKED,
    );
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

  it("keeps the same list when the tab has nothing to restore, or the API nothing new to list", () => {
    const tracked = following(task("task_running"));
    expect(tracking(tracked, { type: "restore", tasks: [] }).tasks).toBe(tracked.tasks);
    expect(tracking(tracked, { type: "found", tasks: [] }).tasks).toBe(tracked.tasks);
  });

  it("keeps the refusal of the reads out of reach, noted once, and takes anew a relaunch out of reach after them, noted anew (#1181)", () => {
    const answer = (source: "read" | "relaunch") =>
      ({
        type: "answer",
        source,
        key: MARKING,
        taskId: MARKING,
        outcome: { kind: "unreachable" },
      }) as const;
    const once = tracking(following(task("task_running")), answer("read"));
    const first = once.tasks[0]?.outcome;
    expect(first).toEqual({ kind: "unreachable" });
    // Read again out of reach: the same refusal, which the history noted already.
    const twice = tracking(once, answer("read"));
    expect(twice.tasks[0]?.outcome).toBe(first);
    // A relaunch the user pressed, out of reach: a refusal of its own, told and noted anew.
    const relaunched = tracking(twice, answer("relaunch"));
    expect(relaunched.tasks[0]?.outcome).toEqual({ kind: "unreachable" });
    expect(relaunched.tasks[0]?.outcome).not.toBe(first);
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

  it("forgets every task, every end and every dismissal once signed out, and drops an answer still on its way", () => {
    const followed = tracking(
      tracking(following(task("task_succeeded")), { type: "restore", tasks: [] }),
      { type: "track", task: task("task_running"), launch: {} },
    );
    const dismissed = tracking(followed, { type: "dismiss", key: task("task_running").task_id });
    expect(dismissed.dismissed).toContain(task("task_running").task_id);
    // Dismissed, a task the list of the user brings again is not followed again.
    expect(tracking(dismissed, { type: "found", tasks: [task("task_running")] }).tasks).toEqual(
      dismissed.tasks,
    );
    const forgotten = tracking(dismissed, { type: "forget" });
    expect(forgotten).toEqual({ tasks: [], log: [], dismissed: [], restored: true, cards: [] });
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

describe("the cards of the ends (US-2170)", () => {
  const RUNNING_ID = task("task_running").task_id;

  /** The tracker once a task handed over running has been read in the state named. */
  function read(state: Tracking, name: string): Tracking {
    return tracking(state, {
      type: "answer",
      source: "read",
      key: RUNNING_ID,
      taskId: RUNNING_ID,
      outcome: { kind: "done", data: task(name) },
    });
  }

  it("stacks a card for each success and each failure, the last on top, and none for a follow-up interrupted [WF-IHM-0080-A]", () => {
    const failed = following(task("task_failed"));
    const both = read(
      tracking(failed, { type: "track", task: task("task_running"), launch: {} }),
      "task_succeeded",
    );
    expect(both.cards.map((card) => [card.end, card.key])).toEqual([
      ["succeeded", RUNNING_ID],
      ["failed", MARKING],
    ]);
    const interrupted = tracking(following(task("task_running")), {
      type: "answer",
      source: "read",
      key: RUNNING_ID,
      taskId: RUNNING_ID,
      outcome: {
        kind: "refused",
        problem: { code: "NOT_FOUND", status: 404 },
        conflictingObjectId: null,
      },
    });
    expect(interrupted.log.map((line) => line.end)).toEqual(["interrupted"]);
    expect(interrupted.cards).toEqual([]);
  });

  it("keeps a card until it is closed, however many ends the log has kept since [WF-IHM-0080-A]", () => {
    let state = following(task("task_failed"));
    const [first] = state.cards;
    for (let turn = 0; turn < 12; turn += 1) {
      state = read(
        tracking(state, { type: "track", task: task("task_running"), launch: {} }),
        "task_succeeded",
      );
    }
    expect(state.log).not.toContain(first);
    expect(state.cards).toHaveLength(13);
    expect(state.cards.at(-1)).toBe(first);
    const closed = tracking(state, { type: "card_closed", id: first?.id ?? 0 });
    expect(closed.cards).toHaveLength(12);
    expect(closed.cards).not.toContain(first);
    expect(closed.log).toBe(state.log);
    // A card closed already closes nothing more.
    expect(tracking(closed, { type: "card_closed", id: first?.id ?? 0 })).toBe(closed);
  });

  it("leaves the cards as they are on a read that changes nothing, and forgets them on signing out [WF-IHM-0080-A]", () => {
    const ended = following(task("task_failed"));
    expect(tracking(ended, { type: "found", tasks: [] })).toBe(ended);
    expect(tracking(ended, { type: "forget" }).cards).toEqual([]);
  });

  it("makes the card of an end before the log keeps its last ten lines, the log full [WF-IHM-0080-A]", () => {
    let state = NOTHING_TRACKED;
    for (let turn = 0; turn < 10; turn += 1) {
      state = tracking(state, { type: "track", task: task("task_failed"), launch: {} });
    }
    expect(state.log).toHaveLength(10);
    const full = tracking(state, {
      type: "track",
      task: task("task_export_succeeded"),
      launch: {},
    });
    expect(full.log).toHaveLength(10);
    expect(full.log.at(-1)?.id).toBe(11);
    expect(full.cards.map((card) => card.id)).toEqual([11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]);
  });

  it("offers the file of a card no more once downloaded by itself, and again with the refusal the card tells, or by the entry the card closed [WF-IHM-0080-A]", () => {
    const exported = task("task_export_succeeded");
    const ended = following(exported);
    const [card] = ended.cards;
    const id = card?.id ?? 0;
    const delivered = tracking(ended, { type: "card_delivered", id });
    expect(delivered.cards).toEqual([{ ...card, delivered: true }]);
    expect(delivered.log).toBe(ended.log);
    const refusal = {
      kind: "conflict",
      problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
      conflictingObjectId: null,
    } as const;
    const event = {
      type: "card_refused",
      id,
      key: exported.task_id,
      taskId: exported.task_id,
      refusal,
    } as const;
    expect(tracking(delivered, event).cards).toEqual([{ ...card, delivered: false, refusal }]);
    expect(tracking(ended, event).tasks).toBe(ended.tasks);
    // The card closed: the entry of the task tells it, as the refusal of a click would.
    const closed = tracking(ended, { type: "card_closed", id });
    const told = tracking(closed, event);
    expect(told.cards).toEqual([]);
    expect(told.tasks[0]?.outcome).toBe(refusal);
    expect(tracking(closed, { type: "card_delivered", id })).toBe(closed);
  });
});

describe("the screen read anew at the end of a task (#3103)", () => {
  const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";
  it.each([
    ["succeeded", `${PROJECT}/revisions?revision_id=1`, `${PROJECT}/revisions`, true],
    ["failed", `${PROJECT}/revisions`, `${PROJECT}/exchanges`, true],
    ["interrupted", `${PROJECT}/revisions`, `${PROJECT}/revisions`, false],
    ["succeeded", `${PROJECT}/revisions`, "/projects/01926f3a-7c00-7000-8000-000000000002", false],
    ["succeeded", `${PROJECT}/revisions`, "/admin/backups", false],
    ["succeeded", "/admin/backups?page=2", "/admin/backups", true],
    ["succeeded", "/admin/backups", "/admin/users", false],
  ] as const)("a task %s, started on %s, reads %s anew: %s", (end, href, shown, read) => {
    expect(readsAnew({ end, from: { href } }, shown)).toBe(read);
  });

  it("reads nothing anew for a task found again, its screen unknown", () => {
    expect(readsAnew({ end: "succeeded", from: undefined }, "/projects/x/revisions")).toBe(false);
  });
});

describe("the result of a task", () => {
  it.each([
    ["task_export_succeeded", true],
    ["identity_sync_succeeded", false],
    ["task_succeeded", false],
    ["task_running", false],
  ])("of %s is a file to download: %s", (name, file) => {
    expect(givesFile(example(name) as BackgroundTask)).toBe(file);
  });
});
