// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { rowNature, RowNatureIcon } from "./row-nature";

type Node = components["schemas"]["Node"];

const [summary, task, line] = (example("nodes") as { items: Node[] }).items;

// A milestone of the contract, carried by its summary task (`nodes_milestone`).
const [, milestone] = (example("nodes_milestone") as { items: Node[] }).items;

describe("the nature of a row", () => {
  it("is read from the kind of the node and the flags of its task", () => {
    expect([summary, task, line].map((node) => node && rowNature(node))).toEqual([
      "summary",
      "task",
      "estimateLine",
    ]);
    expect(milestone && rowNature(milestone)).toBe("milestone");
  });

  it("shows as an icon named for it, in the language of the page", () => {
    const html = milestone
      ? renderToStaticMarkup(
          <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
            <RowNatureIcon node={milestone} />
          </NextIntlClientProvider>,
        )
      : "";
    expect(html).toMatch(/^<svg[^>]*class="lucide lucide-diamond[^"]*"[^>]*role="img"/);
    expect(html).toContain('aria-label="Jalon"');
  });
});
