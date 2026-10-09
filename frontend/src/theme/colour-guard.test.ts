// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The rules of eslint.config.mjs against a colour or a font written in the code, tried on
 * trapped snippets: a component names a token of the charter, and anything else — a class
 * of the palette of Tailwind, an arbitrary value, a colour in a string or in a style — must
 * be refused as an error, which fails `make lint-front`. And no stylesheet lives outside
 * src/theme/, where the tokens are.
 *
 * A snippet is linted as the text of an existing file of the project, so that the typed
 * rules find it; nothing is written to the disk.
 */
import { readdirSync } from "node:fs";
import { join } from "node:path";

import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { beforeAll, describe, expect, it } from "vitest";

const ROOT = join(import.meta.dirname, "../..");

// A client component of the project, in TSX, and a module of server actions.
const COMPONENT = "src/components/shell/navigation.tsx";
// The component of the signals, the only one that draws the tokens of the zones.
const SIGNAL_COMPONENT = "src/components/signal/signal.tsx";
const ACTION = "src/api/actions/trap.tsx";

const COLOUR =
  "Name a token of the charter, src/theme/globals.css; never write a colour or a font.";
const DARK = "No variant for the dark mode: a token of src/theme/globals.css carries both modes.";
const SIGNAL = "Show a zone with Signal, src/components/signal/: its colour never shows alone.";

/** A component around some JSX, and a constant beside it. */
function component(jsx: string, constant = '""'): string {
  return [
    '"use client";',
    `const VALUE = ${constant};`,
    "/** A component. */",
    "export function Trap({ ok }: { ok: boolean }) {",
    `  return ${jsx};`,
    "}",
  ].join("\n");
}

// A colour or a font written in the classes of an element, however they are built.
const IN_CLASSES: readonly string[] = [
  '<p className="text-white">{VALUE}</p>',
  '<p className="p-2 bg-blue-500">{VALUE}</p>',
  '<p className="hover:bg-sky-600/50 p-2">{VALUE}</p>',
  '<p className="border-t-red-700">{VALUE}</p>',
  '<p className={ok ? "text-slate-900" : "text-foreground"}>{VALUE}</p>',
  "<p className={`p-2 ${VALUE} ring-emerald-400`}>{VALUE}</p>",
  '<p className="bg-[#027dc6]">{VALUE}</p>',
  '<p className="text-[rgb(2_125_198)]">{VALUE}</p>',
  '<p className="fill-[oklch(0.6_0.1_240)]">{VALUE}</p>',
  "<p className=\"font-['Comic_Sans_MS']\">{VALUE}</p>",
  '<p className="bg-[red]">{VALUE}</p>',
  '<p className="text-[rebeccapurple]">{VALUE}</p>',
  '<p className="shadow-[0_0_0_2px_#f00]">{VALUE}</p>',
  '<p className="[color:#027dc6]">{VALUE}</p>',
  '<p className="p-2 [--primary:#ff0000]">{VALUE}</p>',
  '<p className="[font-family:Arial]">{VALUE}</p>',
  '<p className="hover:[background-color:red]">{VALUE}</p>',
  '<p className="bg-[color-mix(in_oklab,#fff,#000)]">{VALUE}</p>',
  '<p className="bg-(--brand-deep)">{VALUE}</p>',
  '<p className="text-(--brand-bright)">{VALUE}</p>',
  '<p className="font-(family-name:--x)">{VALUE}</p>',
];

// A colour or a font written elsewhere: a string of its own, an attribute of an SVG, a style.
const ELSEWHERE: readonly [string, string][] = [
  ["<p>{VALUE}</p>", '"#027dc6"'],
  ["<p>{VALUE}</p>", '"#FFF"'],
  ["<p>{VALUE}</p>", '"rgb(2, 125, 198)"'],
  ["<p>{VALUE}</p>", "`hsl(200 90% 40%)`"],
  ['<svg><path d="M0 0" fill="#1195e1" /></svg>', '""'],
  ["<p style={{ color: VALUE }}>{VALUE}</p>", '"var(--primary)"'],
  ["<p style={{ backgroundColor: VALUE }}>{VALUE}</p>", '""'],
  ["<p style={{ fontFamily: VALUE }}>{VALUE}</p>", '"Arial"'],
  ['<p style={{ border: "1px solid #ff0000" }}>{VALUE}</p>', '""'],
  ['<p style={{ boxShadow: "0 0 0 2px #f00" }}>{VALUE}</p>', '""'],
  ['<p style={{ outline: "2px solid red" }}>{VALUE}</p>', '""'],
  ['<p style={{ "color": VALUE }}>{VALUE}</p>', '"red"'],
  ['<p style={{ "--primary": VALUE }}>{VALUE}</p>', '"red"'],
  ["<p style={{ caretColor: VALUE }}>{VALUE}</p>", '"red"'],
  ['<svg><path d="M0 0" fill="red" /></svg>', '""'],
  ['<svg><path d="M0 0" stroke={"black"} /></svg>', '""'],
  ['<svg><stop stopColor="white" /></svg>', '""'],
  ['<svg><path d="M0 0" fill={ok ? "red" : "none"} /></svg>', '""'],
  ['<svg><path d="M0 0" fill={`red`} /></svg>', '""'],
  ["<p>{VALUE}</p>", '"color-mix(in oklab, var(--primary), transparent)"'],
];

// What a component may write: the tokens of the charter, and what only looks like a colour.
const ALLOWED: readonly [string, string][] = [
  ['<p className="bg-primary text-primary-foreground">{VALUE}</p>', '""'],
  ['<p className="text-muted-foreground hover:bg-accent/90">{VALUE}</p>', '""'],
  ['<p className="border-input ring-ring md:grid-cols-[16rem_1fr]">{VALUE}</p>', '""'],
  ['<svg><path d="M0 0" fill="currentColor" /></svg>', '""'],
  ['<svg><path d="M0 0" fill="CurrentColor" /></svg>', '""'],
  ['<svg><path d="M0 0" fill={level > 2 ? "none" : "currentColor"} /></svg>', '""'],
  ['<svg><path d="M0 0" fill={ok ? "currentColor" : null} /></svg>', '""'],
  ['<a href="#main">{VALUE}</a>', '"text-whitespace blue-print"'],
  ["<p style={{ width: VALUE }}>{VALUE}</p>", '"12rem"'],
  ['<p className="ring-[3px] text-[14px] stroke-[1.5] font-[600] from-[10%]">{VALUE}</p>', '""'],
  [
    '<p className="[&_svg]:size-4 aria-[current=page]:bg-accent grid-cols-[1fr_2fr]">{VALUE}</p>',
    '""',
  ],
  ['<svg><path d="M0 0" fill="none" stroke="url(#edge)" /></svg>', '""'],
  ['<svg><path d="M0 0" fill={ok ? `none` : "currentColor"} /></svg>', '""'],
  ['<p className="text-(length:--size) grid-cols-(--columns)">{VALUE}</p>', '""'],
  ["<p>{VALUE}</p>", '"the darkest hour: dark matter"'],
];

// The dark variant, which follows the workstation alone.
const DARK_VARIANT: readonly string[] = [
  '<p className="bg-background dark:bg-card">{VALUE}</p>',
  "<p className={`p-2 md:dark:text-foreground`}>{VALUE}</p>",
];

let eslint: ESLint;
let actions: ESLint;

beforeAll(() => {
  eslint = new ESLint({ cwd: ROOT });
  actions = new ESLint({ cwd: ROOT, overrideConfig: tseslint.configs.disableTypeChecked });
});

/** The rule, severity and message of each finding of the colour guard on a snippet. */
async function findings(code: string, file = COMPONENT, linter = eslint) {
  const [result] = await linter.lintText(code, { filePath: file });
  return (result?.messages ?? [])
    .filter((m) => m.fatal === true || m.message === COLOUR)
    .map((m) => [m.ruleId, m.severity, m.message]);
}

describe("the colour guard", { timeout: 60_000 }, () => {
  it.each(IN_CLASSES)("refuses %j", async (jsx) => {
    // Severity 2 is an error: it fails `make lint-front`, and so the chain.
    expect(await findings(component(jsx))).toContainEqual(["no-restricted-syntax", 2, COLOUR]);
  });

  it.each(ELSEWHERE)("refuses %j with %s", async (jsx, constant) => {
    expect(await findings(component(jsx, constant))).toContainEqual([
      "no-restricted-syntax",
      2,
      COLOUR,
    ]);
  });

  it.each(ALLOWED)("lets %j with %s through", async (jsx, constant) => {
    expect(await findings(component(jsx, constant))).toEqual([]);
  });

  it.each(DARK_VARIANT)("refuses the dark variant in %j", async (jsx) => {
    const [result] = await eslint.lintText(component(jsx), { filePath: COMPONENT });
    expect(result?.messages.map((m) => [m.ruleId, m.severity, m.message])).toContainEqual([
      "no-restricted-syntax",
      2,
      DARK,
    ]);
  });

  it.each([
    '<p className="bg-signal-alert">{VALUE}</p>',
    "<p className={`p-2 hover:text-signal-watch`}>{VALUE}</p>",
  ])("refuses the token of a zone outside Signal, in %j", async (jsx) => {
    // A cell tinted by its zone, without the shape and the name `Signal` gives it (WF-IHM-0070).
    const [result] = await eslint.lintText(component(jsx), { filePath: COMPONENT });
    expect(result?.messages.map((m) => [m.ruleId, m.severity, m.message])).toContainEqual([
      "no-restricted-syntax",
      2,
      SIGNAL,
    ]);
  });

  it("lets Signal draw the token of a zone, and still refuses a colour there", async () => {
    const lint = async (jsx: string) => {
      const [result] = await eslint.lintText(component(jsx), { filePath: SIGNAL_COMPONENT });
      return (result?.messages ?? [])
        .filter((m) => m.fatal === true || m.ruleId === "no-restricted-syntax")
        .map((m) => [m.ruleId, m.severity, m.message]);
    };
    expect(await lint('<p className="text-signal-alert">{VALUE}</p>')).toEqual([]);
    expect(await lint('<p className="text-red-700">{VALUE}</p>')).toContainEqual([
      "no-restricted-syntax",
      2,
      COLOUR,
    ]);
  });

  it("holds in the server actions, whose block redefines the rule", async () => {
    const code = '"use server";\n/** A trap. */\nexport const TRAP = "#027dc6";';
    expect(await findings(code, ACTION, actions)).toEqual([["no-restricted-syntax", 2, COLOUR]]);
    const signal = '"use server";\n/** A trap. */\nexport const TRAP = "bg-signal-alert";';
    const [result] = await actions.lintText(signal, { filePath: ACTION });
    expect(result?.messages.map((m) => m.message)).toEqual([SIGNAL]);
  });

  it("finds no stylesheet outside src/theme/, where the tokens are", () => {
    const sheets = readdirSync(join(ROOT, "src"), { recursive: true, encoding: "utf-8" }).filter(
      (file) => file.endsWith(".css"),
    );
    expect(sheets).toEqual([join("theme", "globals.css")]);
  });
});
