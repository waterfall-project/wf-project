// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { onTask, TASK_PARAMETER, targetTask } from "./planning-target";

const TASK = "01926f3a-7c00-7000-8000-000000000552";

describe("the task the address of the planning names", () => {
  it("is read from its parameter, a well-formed identifier alone", () => {
    expect(TASK_PARAMETER).toBe("task");
    expect(targetTask(new URLSearchParams({ task: TASK }))).toBe(TASK);
    expect(targetTask(new URLSearchParams({ task: "552" }))).toBeUndefined();
    expect(targetTask(new URLSearchParams())).toBeUndefined();
  });

  it("is added to the address of the planning, after the context it carries", () => {
    expect(onTask("/projects/p/revisions/r/planning", TASK)).toBe(
      `/projects/p/revisions/r/planning?task=${TASK}`,
    );
    expect(onTask("/projects/p/revisions/r/planning?as_of=2026-03-16", TASK)).toBe(
      `/projects/p/revisions/r/planning?as_of=2026-03-16&task=${TASK}`,
    );
  });
});
