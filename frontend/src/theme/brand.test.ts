// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const FRONT = join(import.meta.dirname, "../..");
const ASSETS = join(FRONT, "../docs/assets");

// The front serves the logos and the icon of docs/assets, where they are drawn: its copies
// are the same files, never a variant edited on the side.
describe("the logos and the icon of the front", () => {
  it.each([
    ["public/waterfall_logo.svg", "waterfall_logo.svg"],
    ["public/waterfall_logo-dark.svg", "waterfall_logo-dark.svg"],
    ["src/app/icon.svg", "waterfall_icon.svg"],
  ])("serves %s as docs/assets/%s", (copy, original) => {
    expect(readFileSync(join(FRONT, copy))).toEqual(readFileSync(join(ASSETS, original)));
  });
});
