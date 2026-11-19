// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The fields of the charter are those of this directory (US-2070, #3079): a field where one types,
 * a list to choose from, a multi-line field are `Input`, `NativeSelect` and `Textarea`, pills
 * bordered by the token of a field. A field written by hand outside them kept its own shape —
 * seven did, square, after the charter came (#3259). This test reads every module of the screens
 * and refuses a `<textarea>`, a `<select>` or an `<input>` written by hand, but an input that is no
 * field to type in: hidden, a box to tick, a radio button, the choice of a file.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

import { uncommented } from "@/test/uncommented";

const SRC = join(import.meta.dirname, "..", "..");
const UI = import.meta.dirname;

/** The modules of the screens under a directory: every `.tsx` but the tests and this directory. */
function modules(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return path === UI ? [] : modules(path);
    }
    return entry.name.endsWith(".tsx") && !entry.name.includes(".test.") ? [path] : [];
  });
}

// An input that is no field to type in, and keeps the look of the browser.
const NOT_TYPED = /\btype="(?:hidden|checkbox|radio|file)"/;

/** The fields a source writes by hand, each as its opening tag. */
function handWritten(source: string): string[] {
  const code = uncommented(source);
  return [...code.matchAll(/<(input|textarea|select)\b[^>]*>/g)]
    .map((match) => match[0])
    .filter((tag) => !(tag.startsWith("<input") && NOT_TYPED.test(tag)));
}

const SOURCES = modules(SRC).map((path): [string, string] => [
  relative(SRC, path),
  readFileSync(path, "utf-8"),
]);

describe("the fields of the screens (#3259)", () => {
  it("are read, a field written by hand and a box to tick among them", () => {
    expect(SOURCES.length).toBeGreaterThan(100);
    expect(handWritten('<input\n  id={field}\n  value={name}\n  className="h-9" />')).toHaveLength(
      1,
    );
    expect(handWritten("<textarea rows={3} />")).toHaveLength(1);
    expect(handWritten("<select value={kind}>")).toHaveLength(1);
    expect(handWritten('<input type="checkbox" checked={on} />')).toEqual([]);
    expect(handWritten('<Input type="date" />')).toEqual([]);
  });

  it("finds a field written after a string holding a comment opener [US-2800]", () => {
    expect(handWritten('const a = "http://x";\n<input id={a} />')).toHaveLength(1);
    expect(handWritten('const a = "/*";\n<textarea />\n// */')).toHaveLength(1);
    expect(handWritten("// <input />\n/* <select> */")).toEqual([]);
  });

  it.each(SOURCES)("are the fields of the charter: %s", (_path, source) => {
    expect(handWritten(source)).toEqual([]);
  });
});
