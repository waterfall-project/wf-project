// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard against `useId` in a server component (#251): the identifiers React gives the server
 * components of a page and the client components of the shell may meet — the region of the detail
 * of a risk was once named after the hint of the search of the shell. A section of a server
 * component is named by `aria-label`, a field by an identifier of its own; `useId` is for the
 * client components, where React keeps it unique. The rule is in `docs/dev/typescript.md`, « Où
 * s'exécute un composant »; nothing else holds it: the sources are read, as the network guard
 * reads them.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..");

/** Every module of the front: the `.ts` and `.tsx` files of `src/`, tests and types left out. */
function modules(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        /\.tsx?$/.test(entry.name) &&
        !entry.name.endsWith(".d.ts") &&
        !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** Whether a module runs in the browser: it opens on the directive, after its comments if any. */
function isClient(source: string): boolean {
  // A line comment runs to the end of its line: a directive written within it is none.
  // Each alternative opens on its own character, and a block comment ends at its first `*/`: no
  // string can be matched two ways, so the test runs in linear time (CodeQL, inefficient regex).
  return /^(?:\s|\/\/[^\n]*\n|\/\*(?:[^*]|\*(?!\/))*\*\/)*["']use client["']/.test(source);
}

/** A source without its comments: a comment that names `useId` is no use of it. */
function uncommented(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
}

/**
 * Whether a module takes `useId` from React: a named import, under its name or another
 * (`useId as makeId`), or the hook read from the module itself (`React.useId`).
 */
function takesUseId(source: string): boolean {
  const code = uncommented(source);
  const named = /import\s*(?:type\s+)?\{([^}]*)\}\s*from\s*["']react["']/g;
  for (const [, specifiers = ""] of code.matchAll(named)) {
    if (/(?:^|,)\s*useId\b/.test(specifiers)) {
      return true;
    }
  }
  return /\b\w+\.useId\b/.test(code) && /from\s*["']react["']/.test(code);
}

describe("the identifiers of the server components", () => {
  it("never come from useId, which a server component may share with a client one of the shell", () => {
    const offending = modules().filter((file) => {
      const source = readFileSync(file, "utf-8");
      return !isClient(source) && takesUseId(source);
    });
    expect(offending.map((file) => relative(SOURCES, file))).toEqual([]);
  });

  it("know a client component by its directive, whatever comments and blank lines come before it", () => {
    expect(isClient('// SPDX\n/** doc */\n"use client";\n')).toBe(true);
    expect(isClient('// SPDX\n// SPDX\n\n/**\n * doc\n */\n\n"use client";\n')).toBe(true);
    expect(isClient("'use client';\n")).toBe(true);
    expect(isClient('// SPDX\nimport { useId } from "react";\n"use client";\n')).toBe(false);
    expect(isClient('// "use client" is not the directive in a comment\nconst a = 1;\n')).toBe(
      false,
    );
  });

  it("find useId imported from React, under another name or read from the module", () => {
    expect(takesUseId('import { useId } from "react";')).toBe(true);
    expect(takesUseId('import { type ReactNode, useId } from "react";')).toBe(true);
    expect(takesUseId('import {\n  useEffect,\n  useId as makeId,\n} from "react";')).toBe(true);
    expect(takesUseId('import * as React from "react";\nconst id = React.useId();')).toBe(true);
    expect(takesUseId('import React from "react";\nconst id = React.useId();')).toBe(true);
  });

  it("find no useId in a comment, in another module, or in a name that only begins with it", () => {
    expect(takesUseId('// useId is not used: import { useId } from "react";\n')).toBe(false);
    expect(takesUseId('/* import { useId } from "react"; */\nconst a = 1;')).toBe(false);
    expect(takesUseId('import { useId } from "./ids";')).toBe(false);
    expect(takesUseId('import { useIdentity } from "react";')).toBe(false);
    expect(takesUseId('import { type ReactNode } from "react";')).toBe(false);
  });
});
