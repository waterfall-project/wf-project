// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import type { NodeList } from "./nodes";
import { PhysicalProgressCell } from "./planning-cells";

describe("the physical progress of a summary", () => {
  it("shows a progress too small to show below the smallest share, never « 0 % » (#626)", () => {
    // A variant of the first summary of `nodes_planning`: its physical progress, 1, changed to
    // 0.00003 — the rest of the node kept.
    const node = (example("nodes_planning") as NodeList).items.find(
      (item) => item.task?.physical_progress !== undefined && item.task.physical_progress !== null,
    );
    const task = node?.task;
    expect(task?.physical_progress?.value).toBe("1");
    if (node === undefined || task === undefined || task === null) {
      throw new Error("The example lacks a summary");
    }
    const tiny = {
      ...node,
      task: { ...task, physical_progress: { is_computable: true, value: "0.00003", reason: null } },
    };
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <PhysicalProgressCell node={tiny} />
      </NextIntlClientProvider>,
    );
    expect(html).toBe("&lt;0.01%");
  });
});
