// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The colour tokens of the charter, read from globals.css, against the contrast WCAG AA asks
 * for (§3.6): 4.5:1 for a text on its background, 3:1 for what shows a control — the border
 * of a field, the ring of the focus. In both modes, since each token holds a light and a dark
 * value. The screens themselves are checked in a browser by US-0200.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(join(import.meta.dirname, "globals.css"), "utf-8");

type Mode = "light" | "dark";

/** The declarations of the custom properties of `:root`, by name. */
function declarations(): Map<string, string> {
  const root = /:root\s*\{([^}]*)\}/.exec(CSS)?.[1] ?? "";
  const found = new Map<string, string>();
  for (const [, name = "", value = ""] of root.matchAll(/--([\w-]+):\s*([^;]+);/g)) {
    found.set(name, value.trim());
  }
  return found;
}

const TOKENS = declarations();

/** The colour a token takes in a mode, its references to other tokens followed. */
function colour(name: string, mode: Mode): string {
  const value = TOKENS.get(name);
  if (value === undefined) {
    throw new Error(`no token --${name}`);
  }
  const pair = /^light-dark\((.+),\s*(.+)\)$/.exec(value);
  const chosen = pair === null ? value : (pair[mode === "light" ? 1 : 2] ?? "");
  const reference = /^var\(--([\w-]+)\)$/.exec(chosen.trim());
  return reference?.[1] === undefined ? chosen.trim() : colour(reference[1], mode);
}

/** The relative luminance of a colour written `#rrggbb` (WCAG 2.2, § relative luminance). */
function luminance(hex: string): number {
  const channels = [1, 3, 5].map((at) => Number.parseInt(hex.slice(at, at + 2), 16) / 255);
  const [r = 0, g = 0, b = 0] = channels.map((c) =>
    c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** The contrast ratio of two colours, from 1 to 21. */
function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
}

// A text, and the backgrounds it is written on.
const TEXTS: readonly [string, string][] = [
  ["foreground", "background"],
  ["card-foreground", "card"],
  ["primary-foreground", "primary"],
  ["secondary-foreground", "secondary"],
  ["muted-foreground", "background"],
  ["muted-foreground", "muted"],
  ["muted-foreground", "card"],
  ["accent-foreground", "accent"],
  ["destructive-foreground", "destructive"],
  ["primary", "background"],
  ["destructive", "background"],
  ["destructive", "card"],
];

// What shows a control or its state, and the backgrounds it is drawn on.
const CONTROLS: readonly [string, string][] = [
  ["input", "background"],
  ["input", "card"],
  ["ring", "background"],
  ["ring", "card"],
];

const MODES: readonly Mode[] = ["light", "dark"];

describe("the colour tokens of the charter", () => {
  it("hold a light and a dark value each, the blues of the logos aside", () => {
    const colours = [...TOKENS].filter(([, value]) => /#|light-dark/.test(value));
    const single = colours.filter(([, value]) => !value.startsWith("light-dark("));
    expect(single.map(([name]) => name)).toEqual(["brand-deep", "brand-bright"]);
    expect(colour("brand-deep", "light")).toBe("#027dc6");
    expect(colour("brand-bright", "dark")).toBe("#1195e1");
  });

  it("give Tailwind only tokens of the charter", () => {
    const named = [...CSS.matchAll(/--color-[\w-]+:\s*var\(--([\w-]+)\)/g)].map((m) => m[1]);
    expect(named.length).toBeGreaterThan(0);
    expect(named.filter((name) => name === undefined || !TOKENS.has(name))).toEqual([]);
  });

  describe.each(MODES)("in %s mode", (mode) => {
    it.each(TEXTS)("write %s on %s at 4.5:1 at least", (text, background) => {
      expect(contrast(colour(text, mode), colour(background, mode))).toBeGreaterThanOrEqual(4.5);
    });

    it.each(CONTROLS)("draw %s on %s at 3:1 at least", (control, background) => {
      expect(contrast(colour(control, mode), colour(background, mode))).toBeGreaterThanOrEqual(3);
    });
  });
});
