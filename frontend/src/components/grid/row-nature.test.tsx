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

const nodes = (name: string) => (example(name) as { items: Node[] }).items;

// A milestone of the contract, carried by its summary task (`nodes_milestone`).
const [, milestone] = nodes("nodes_milestone");

describe("the nature of a row", () => {
  it("is read from the kind of the node and the flags of its facet", () => {
    expect(nodes("nodes").map(rowNature)).toEqual([
      "summary",
      "task",
      "disbursement",
      "task",
      "task",
      "milestone",
      "task",
    ]);
    expect(nodes("nodes_estimate").map(rowNature)).toEqual([
      "summary",
      "task",
      "labour",
      "disbursement",
      "provision",
      "summary",
      "task",
      "disbursement",
      "task",
      "disbursement",
      "milestone",
    ]);
  });

  it("takes a line without its facet for a disbursement, and a task without its facet for a task", () => {
    const [summary, , line] = nodes("nodes");
    expect(line && rowNature({ ...line, estimate_line: null })).toBe("disbursement");
    expect(summary && rowNature({ ...summary, task: null })).toBe("task");
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
