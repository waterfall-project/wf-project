// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The texts of the empty states that the screens of the project wait for (`project-screens.ts`),
 * read against the catalogue of the messages the components render them from: a tool of the
 * measure, which covers no requirement of its own and cites none.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { SCREENS } from "./project-screens";

const CATALOGUE: unknown = JSON.parse(
  readFileSync(join(__dirname, "../../messages/fr.json"), "utf8"),
);

/** The text of a key of the catalogue, by its dotted path. */
function message(key: string): string {
  let node: unknown = CATALOGUE;
  for (const part of key.split(".")) {
    node = (node as Record<string, unknown> | undefined)?.[part];
  }
  if (typeof node !== "string") throw new Error(`no message at ${key}`);
  return node;
}

/** The keys each section renders when it has nothing to draw, in its component. */
const EMPTY_KEYS: Readonly<Record<string, readonly string[]>> = {
  "Plan de charge du projet": ["workload.none", "workload.noneInNode"],
  "Projection de dépenses": ["spending.none"],
  "Suivi des jalons": ["projectIndicators.milestones.none"],
  "Coûts cumulés": ["projectIndicators.curves.empty"],
  "Courbes de valeur acquise": ["projectIndicators.curves.empty"],
};

describe("the empty states of the screens of the project", () => {
  const sections = SCREENS.flatMap((screen) => screen.sections).filter(
    (section) => section.empty !== undefined,
  );

  it("name every section that has an empty state", () => {
    expect(sections.map((section) => section.name).sort()).toEqual(Object.keys(EMPTY_KEYS).sort());
  });

  it.each(sections.map((section) => [section.name, section.empty] as const))(
    "%s: the pattern %s matches the message its component renders",
    (name, empty) => {
      for (const key of EMPTY_KEYS[name] ?? []) {
        expect(new RegExp(empty ?? "").test(message(key))).toBe(true);
      }
    },
  );
});
