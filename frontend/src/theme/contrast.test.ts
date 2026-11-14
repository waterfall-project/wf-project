// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The colour tokens of the charter, read from globals.css, against the contrast WCAG AA asks
 * for (§3.6): 4.5:1 for a text on its background, 3:1 for what shows a control — the border
 * of a field, the ring of the focus. In both modes, since each token holds a light and a dark
 * value. The screens themselves are checked in a browser by US-0200.
 *
 * The tokens of the signals are also seen as a grey copy and as a protanope and a deuteranope
 * see them (WF-IHM-0070): what tells the zones apart is the shape and the name of `Signal`,
 * and the colours do not collapse into one either.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ProjectState } from "@/api/project-state";

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

type Linear = readonly [number, number, number];

/** The linear red, green and blue of a colour written `#rrggbb`, from 0 to 1. */
function linear(hex: string): Linear {
  const [r = 0, g = 0, b = 0] = [1, 3, 5]
    .map((at) => Number.parseInt(hex.slice(at, at + 2), 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return [r, g, b];
}

/** The relative luminance of linear channels (WCAG 2.2, § relative luminance). */
function luminanceOf([r, g, b]: Linear): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** The relative luminance of a colour written `#rrggbb`. */
function luminance(hex: string): number {
  return luminanceOf(linear(hex));
}

/** The contrast ratio of two colours, from 1 to 21. */
function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
}

type AlertZone = components["schemas"]["AlertZone"];

// The token of each zone of the contract, which `Signal` names as `text-signal-<zone>`.
const SIGNALS: Readonly<Record<AlertZone, string>> = {
  nominal: "signal-nominal",
  watch: "signal-watch",
  alert: "signal-alert",
};

// The token of each state of a project, the fill of its badge, which `ProjectStateBadge` names as
// `bg-state-<state>`, its text as `text-state-<state>-foreground` (#523).
const STATES: Readonly<Record<ProjectState, string>> = {
  created: "state-created",
  pricing: "state-pricing",
  in_progress: "state-in-progress",
  completed: "state-completed",
  lost: "state-lost",
  abandoned: "state-abandoned",
};

// The tint of the row of each difference a differential marks, and the mark written on it
// (`DiffMark`, US-0500).
const DIFFERENCES = ["diff-added", "diff-removed", "diff-modified"] as const;

// A text, and the backgrounds it is written on.
const TEXTS: readonly [string, string][] = [
  ["foreground", "background"],
  ["card-foreground", "card"],
  ["primary-foreground", "primary"],
  ["primary-foreground", "primary-hover"],
  ["secondary-foreground", "secondary"],
  ["muted-foreground", "background"],
  // The header row of every table, a list or a dense grid (#508).
  ["muted-foreground", "muted"],
  ["muted-foreground", "card"],
  ["accent-foreground", "accent"],
  // The link of the navigation under the pointer, or the page shown, and its headings.
  ["foreground", "accent"],
  ["muted-foreground", "accent"],
  ["destructive-foreground", "destructive"],
  ["primary", "background"],
  // The words of the chip of a filter on, in the tint of the primary (#3077, US-2080).
  ["primary", "accent"],
  ["destructive", "background"],
  ["destructive", "card"],
  // The banner of the reading context, on its muted strip, and the headings of the header row of
  // a table that are not muted (#508); a tooltip, the page inverted.
  ["foreground", "muted"],
  ["background", "foreground"],
  // A menu of the shell, its entries, their muted values, the entry under the focus.
  ["popover-foreground", "popover"],
  ["muted-foreground", "popover"],
  ["destructive", "popover"],
  // The side bar, dark in both modes: its entries, the labels of its groups, the current entry
  // and the entry under the pointer, the project whose icon it shows, the icon of the project
  // switcher on its tile. Inside it, the tokens a component names take these values (SIDEBAR).
  ["sidebar-foreground", "sidebar"],
  ["sidebar-foreground", "sidebar-accent"],
  ["sidebar-muted-foreground", "sidebar"],
  ["sidebar-muted-foreground", "sidebar-accent"],
  ["sidebar-accent-foreground", "sidebar-accent"],
  ["sidebar-primary-foreground", "sidebar-primary"],
  // The name and the icon of a signal, wherever a screen sets one: a page, a card, a muted
  // row, a selected row.
  ...Object.values(SIGNALS).flatMap((signal) =>
    (["background", "card", "muted", "accent"] as const).map((background): [string, string] => [
      signal,
      background,
    ]),
  ),
  // The word of the state of a project, on the fill of its badge (#523, WF-IHM-0100).
  ...Object.values(STATES).map((state): [string, string] => [`${state}-foreground`, state]),
  // The text of a cell of a table, on the card its cells are set on (#3277).
  ["foreground", "card"],
  // The text of a row under the pointer: the label, the muted number, a signal (US-2080).
  ["foreground", "row-hover"],
  ["muted-foreground", "row-hover"],
  ...Object.values(SIGNALS).map((signal): [string, string] => [signal, "row-hover"]),
  // The mark of a difference, and the text of the row it tints: the label, the muted number.
  ...DIFFERENCES.flatMap((tint): [string, string][] => [
    [`${tint}-mark`, tint],
    ["foreground", tint],
    ["muted-foreground", tint],
  ]),
  // The series of a chart, on the page and on a card, as legible as a text (US-0240).
  ...(["chart-1", "chart-2", "chart-3", "chart-4"] as const).flatMap((series) =>
    (["background", "card"] as const).map((background): [string, string] => [series, background]),
  ),
];

// What shows a control or its state, and the backgrounds it is drawn on.
const CONTROLS: readonly [string, string][] = [
  // The border of a field, and the axes of a chart (US-0240).
  ["input", "background"],
  ["input", "card"],
  ["ring", "background"],
  ["ring", "card"],
  // The focus of the link that lifts a filter, drawn on its chip.
  ["ring", "accent"],
  // The focus in the banner, in a menu, and in the side bar on its entries.
  ["ring", "muted"],
  ["ring", "popover"],
  // The hatching of the days off in the Gantt, on the page and on its own tint (US-0530/L5).
  ["day-off-mark", "background"],
  ["day-off-mark", "day-off"],
  ["sidebar-ring", "sidebar"],
  ["sidebar-ring", "sidebar-accent"],
  // The tile of the project switcher, which shows where the switcher is on the dark bar.
  ["sidebar-primary", "sidebar"],
  // The border of a field on a muted control, a header row, a selected row or a secondary one.
  ["input", "muted"],
  ["input", "accent"],
  ["input", "secondary"],
  // The dot of the state « Actif » of a line, wherever a table sets it: a page, a card, a muted
  // row, a selected row (#3079).
  ...(["background", "card", "muted", "accent"] as const).map((background): [string, string] => [
    "active-mark",
    background,
  ]),
  // The dot « Actif », the focus of the active cell and the border of a field, on a row under the
  // pointer (US-2080).
  ["active-mark", "row-hover"],
  ["ring", "row-hover"],
  ["input", "row-hover"],
  // The border of a command of a row (the variant `row` of `Button`), on the card the cells of a
  // table are set on, on a row under the pointer and on a row selected (#3332, WCAG 1.4.11).
  ["row-command-border", "card"],
  ["row-command-border", "row-hover"],
  ["row-command-border", "accent"],
  // The line under the current tab of a row of tabs (`Tabs`), on the page and on a card (US-2070).
  ["primary", "background"],
  ["primary", "card"],
];

const MODES: readonly Mode[] = ["light", "dark"];

describe("the colour tokens of the charter", () => {
  it("hold a light and a dark value each, the blues of the logos through the ring", () => {
    const colours = [...TOKENS].filter(([, value]) => /#|light-dark/.test(value));
    const single = colours.filter(([, value]) => !value.startsWith("light-dark("));
    // A colour of a single value would not change with the mode, and would be measured in
    // one of them only: the blues of the logos reach a component through the ring alone.
    expect(single.map(([name]) => name)).toEqual([]);
    expect(colour("ring", "light")).toBe("#027dc6");
    expect(colour("ring", "dark")).toBe("#1195e1");
  });

  it("give Tailwind only tokens of the charter", () => {
    const named = [...CSS.matchAll(/--color-[\w-]+:\s*var\(--([\w-]+)\)/g)].map((m) => m[1]);
    expect(named.length).toBeGreaterThan(0);
    expect(named.filter((name) => name === undefined || !TOKENS.has(name))).toEqual([]);
  });

  describe.each(MODES)("in %s mode", (mode) => {
    it.each(TEXTS)("write %s on %s at 4.5:1 at least [WF-IHM-0100-A]", (text, background) => {
      expect(contrast(colour(text, mode), colour(background, mode))).toBeGreaterThanOrEqual(4.5);
    });

    it.each(CONTROLS)("draw %s on %s at 3:1 at least [WF-IHM-0100-A]", (control, background) => {
      expect(contrast(colour(control, mode), colour(background, mode))).toBeGreaterThanOrEqual(3);
    });
  });
});

/** The custom properties a block of rules other than `:root` declares, by name. */
function rebound(selector: string): Map<string, string> {
  const at = CSS.indexOf(`${selector} {`);
  const body = at < 0 ? "" : CSS.slice(at, CSS.indexOf("}", at));
  return new Map(
    [...body.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1] ?? "", m[2] ?? ""]),
  );
}

const SHELL = join(import.meta.dirname, "..", "components", "shell");

// The tokens a component inside the side bar names, and the token of the bar each takes there.
const SIDEBAR: Readonly<Record<string, string>> = {
  foreground: "sidebar-foreground",
  "muted-foreground": "sidebar-muted-foreground",
  primary: "sidebar-primary",
  "primary-foreground": "sidebar-primary-foreground",
  accent: "sidebar-accent",
  "accent-foreground": "sidebar-accent-foreground",
  border: "sidebar-border",
  ring: "sidebar-ring",
};

describe("the side bar", () => {
  it("gives the tokens its entries name the values of the dark bar, measured above [WF-IHM-0100-A]", () => {
    // A label in `text-muted-foreground` or the tile in `bg-primary` would otherwise take the
    // value written for the page, dark on the dark bar; each token it takes is measured in TEXTS
    // and CONTROLS.
    const found = rebound('[data-sidebar="sidebar"]');
    expect(Object.fromEntries(found)).toEqual(
      Object.fromEntries(Object.entries(SIDEBAR).map(([name, bar]) => [name, `var(--${bar})`])),
    );
    for (const bar of Object.values(SIDEBAR)) {
      expect(TOKENS.has(bar), bar).toBe(true);
    }
  });

  it("leaves no token it renders to the value written for the page [WF-IHM-0100-A]", () => {
    // The classes of colour the components of the bar render: a token named there that the bar
    // does not redefine (`bg-secondary`, `border-input`, `text-destructive`...) would keep its
    // light value on the dark bar, unmeasured.
    const redefined = rebound('[data-sidebar="sidebar"]');
    const named = new Set<string>();
    for (const file of ["navigation.tsx", "project-switcher.tsx"]) {
      const source = readFileSync(join(SHELL, file), "utf-8");
      for (const word of source.split(/[\s"'`{}()]+/)) {
        const bare = word.slice(word.lastIndexOf(":") + 1).replace(/\/\d+$/, "");
        const token =
          /^(?:bg|text|border|ring|outline|fill|stroke|divide|shadow|decoration)-(.+)$/.exec(
            bare,
          )?.[1];
        if (token !== undefined && TOKENS.has(token)) {
          named.add(token);
        }
      }
    }
    expect(named.size).toBeGreaterThan(0);
    const unredefined = [...named].filter(
      (token) => !token.startsWith("sidebar") && !redefined.has(token),
    );
    expect(unredefined).toEqual([]);
  });

  it.each(MODES)("is midnight blue, its text light, in %s mode", (mode) => {
    // La barre latérale est sombre dans les deux modes (EP-25, « Décisions »): the same bar, its
    // current entry a step lighter, beside a light page and a dark one.
    expect(colour("sidebar", mode)).toBe("#0f1b2d");
    expect(colour("sidebar-accent", mode)).toBe("#22324b");
    expect(luminance(colour("sidebar-foreground", mode))).toBeGreaterThan(0.7);
  });
});

describe("the colours of the charter of EP-25", () => {
  it("paint the page, the cards and the primary in light mode as the mock-up does", () => {
    // En mode clair, la page a un fond gris pâle (#f3f5f8) ; la couleur primaire est le bleu
    // nuit (#14233b), le bleu du logo ne servant plus qu'au logo (#3079).
    expect(colour("background", "light")).toBe("#f3f5f8");
    expect(colour("card", "light")).toBe("#ffffff");
    expect(colour("primary", "light")).toBe("#14233b");
    // The rings of the focus, on the page and on the bar, are the blues of the logos, and nothing else.
    for (const name of [...TOKENS.keys()].filter((token) => !token.endsWith("ring"))) {
      expect(colour(name, "light"), name).not.toMatch(/^#(027dc6|1195e1|0270b3)$/);
    }
  });

  it("set in dark mode a page under its cards, and a primary that stands out of both", () => {
    // Le mode sombre a ses propres valeurs : the cards a step lighter than the page, as what rises
    // over a dark page is, and a filled control the lightest surface, as it is the darkest in light
    // mode; the bar dark and apart from the page.
    const [page, card, primary] = (["background", "card", "primary"] as const).map((name) =>
      luminance(colour(name, "dark")),
    );
    expect(card).toBeGreaterThan(page ?? 1);
    expect(primary).toBeGreaterThan(0.7);
    expect(luminance(colour("primary", "light"))).toBeLessThan(0.05);
    expect(colour("sidebar", "dark")).not.toBe(colour("background", "dark"));
  });
});

type Lab = readonly [number, number, number];

/** The CIE L*a*b* coordinates of linear channels, under the white of sRGB (D65). */
function lab(channels: Linear): Lab {
  const [r, g, b] = channels;
  const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
  const x = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047);
  const y = f(luminanceOf(channels));
  const z = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}

type Matrix = readonly [Linear, Linear, Linear];

// How a dichromat sees a colour, in linear sRGB: Viénot, Brettel and Mollon (1999), the
// matrices DaltonLens publishes. A protanope and a deuteranope confuse the red and the green,
// the case the requirement names.
const VIEWS: readonly [string, Matrix][] = [
  [
    "trichromat",
    [
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ],
  ],
  [
    "protanope",
    [
      [0.11238, 0.88762, 0],
      [0.11238, 0.88762, 0],
      [0.00401, -0.00401, 1],
    ],
  ],
  [
    "deuteranope",
    [
      [0.29275, 0.70725, 0],
      [0.29275, 0.70725, 0],
      [-0.02234, 0.02234, 1],
    ],
  ],
];

/** A colour as a view sees it, its channels kept within the gamut. */
function seen(channels: Linear, view: Matrix): Linear {
  const [r = 0, g = 0, b = 0] = view.map((row) =>
    Math.min(1, Math.max(0, row[0] * channels[0] + row[1] * channels[1] + row[2] * channels[2])),
  );
  return [r, g, b];
}

/** Every pair of zones, once. */
function pairs(): [AlertZone, AlertZone][] {
  const zones = Object.keys(SIGNALS) as AlertZone[];
  return zones.flatMap((a, at) => zones.slice(at + 1).map((b): [AlertZone, AlertZone] => [a, b]));
}

/** The channels of the token of a zone in a mode. */
function zone(name: AlertZone, mode: Mode): Linear {
  return linear(colour(SIGNALS[name], mode));
}

// Two colours a glance tells apart: a CIE76 difference of 20 is several times the smallest
// one noticed side by side (about 2.3), so that two zones in two rows do not pass for one.
const DISTINCT = 20;
// Two greys a glance tells apart: 8 points of lightness, out of the 100 from black to white.
const GREY_STEP = 8;
// The zones from the lightest grey to the darkest, in each mode: the alert stands out the most
// from the page, the darkest on the light one and the lightest on the dark one.
const STANDING_OUT: Readonly<Record<Mode, readonly [AlertZone, AlertZone, AlertZone]>> = {
  light: ["nominal", "watch", "alert"],
  dark: ["alert", "watch", "nominal"],
};

describe("the tokens of the signals", () => {
  it("give each zone of the contract its class for Tailwind", () => {
    for (const token of Object.values(SIGNALS)) {
      expect(CSS).toContain(`--color-${token}: var(--${token});`);
    }
  });

  it("keep the colours EP-24 left them, whatever the charter around them [WF-IHM-0070-A]", () => {
    // La même zone d'indice porte la même couleur dans la liste des projets, dans les indicateurs
    // du projet et dans la performance du portefeuille : one token per zone, which the charter of
    // EP-25 does not touch, so that their distances for a protanope and a deuteranope, measured
    // below, stay those that were validated.
    const values = Object.fromEntries(
      Object.values(SIGNALS).map((token) => [token, MODES.map((mode) => colour(token, mode))]),
    );
    expect(values).toEqual({
      "signal-nominal": ["#1f756c", "#07a1a3"],
      "signal-watch": ["#923002", "#f89228"],
      "signal-alert": ["#6b1d24", "#fdb299"],
    });
  });

  describe.each(MODES)("in %s mode", (mode) => {
    it("leave each signal identifiable in a grey copy, the alert standing out the most from the page [WF-IHM-0070-A]", () => {
      // Une copie d'écran en niveaux de gris laisse identifier chaque signalement : the shape
      // and the name tell the zones apart (signal.dom.test.tsx), and their greys too — the
      // alert the darkest on the light page, the lightest on the dark one.
      const grey = (name: AlertZone) => lab(zone(name, mode))[0];
      const [lightest, middle, darkest] = STANDING_OUT[mode];
      expect(grey(lightest)).toBeGreaterThan(grey(middle));
      expect(grey(middle)).toBeGreaterThan(grey(darkest));
      for (const [a, b] of pairs()) {
        expect(Math.abs(grey(a) - grey(b))).toBeGreaterThanOrEqual(GREY_STEP);
      }
    });

    it("set the alert apart from the page the most, and the nominal the least", () => {
      const page = colour("background", mode);
      const standing = (name: AlertZone) => contrast(colour(SIGNALS[name], mode), page);
      expect(standing("alert")).toBeGreaterThan(standing("watch"));
      expect(standing("watch")).toBeGreaterThan(standing("nominal"));
    });

    it.each(VIEWS)("keep the zones apart for a %s", (_view, matrix) => {
      for (const [a, b] of pairs()) {
        const [la, lb] = [lab(seen(zone(a, mode), matrix)), lab(seen(zone(b, mode), matrix))];
        const difference = Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2]);
        expect(difference, `${a} and ${b}`).toBeGreaterThanOrEqual(DISTINCT);
      }
    });
  });
});

describe("the tokens of the states of a project", () => {
  it.each(MODES)(
    "exist for each state of the contract, its fill and its text, in %s mode",
    (mode) => {
      // Les six jetons existent dans les deux thèmes (#523): each a light and a dark value, which the
      // first test of the charter requires of every colour, and each given to Tailwind.
      for (const token of Object.values(STATES)) {
        for (const name of [token, `${token}-foreground`]) {
          expect(TOKENS.get(name), name).toMatch(/^light-dark\(/);
          expect(colour(name, mode), name).toMatch(/^#[0-9a-f]{6}$/);
          expect(CSS).toContain(`--color-${name}: var(--${name});`);
        }
      }
    },
  );

  describe.each(MODES)("in %s mode", (mode) => {
    it("stay apart from the zones of a signal, so that no state reads as an alert", () => {
      // Ces couleurs restent distinctes de celles des zones des indices : the green of a project in
      // progress is not the nominal, its orange when lost not the watch, its red when abandoned
      // not the alert — by as much as two zones are apart from one another.
      for (const [state, token] of Object.entries(STATES)) {
        for (const signal of Object.keys(SIGNALS) as AlertZone[]) {
          const [a, b] = [lab(linear(colour(token, mode))), lab(zone(signal, mode))];
          const difference = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
          expect(difference, `${state} and ${signal}`).toBeGreaterThanOrEqual(DISTINCT);
        }
      }
    });
  });
});
