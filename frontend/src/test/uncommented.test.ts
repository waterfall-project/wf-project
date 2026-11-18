// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { uncommented } from "./uncommented";

// The guards of the sources read them through this one function (#839).
describe("a source without its comments", () => {
  it("[US-2530] removes the block and the line comments, and keeps the lines", () => {
    expect(uncommented("a /* b\nc */ d // e\nf")).toBe("a  d \nf");
    expect(uncommented("a // no end")).toBe("a ");
    expect(uncommented("a /* never closed")).toBe("a ");
  });

  it("[US-2530] opens no comment in a string, single, double or template", () => {
    expect(uncommented('const g = "/*"; x /* y */')).toBe('const g = "/*"; x ');
    expect(uncommented("const g = '//'; x // y")).toBe("const g = '//'; x ");
    expect(uncommented("const g = `/* ${a} //`; x /* y */")).toBe("const g = `/* ${a} //`; x ");
    expect(uncommented('"a \\" /* b" /* c */ d')).toBe('"a \\" /* b"  d');
  });

  it("[US-2530] reads a comment inside a substitution of a template, and its nested strings", () => {
    expect(uncommented("`a ${ b /* c */ + `d ${'/*'}` } e // f`")).toBe(
      "`a ${ b  + `d ${'/*'}` } e // f`",
    );
    expect(uncommented("`${{ a: 1 }.a} /* x */` y /* z */")).toBe("`${{ a: 1 }.a} /* x */` y ");
  });

  it("[US-2530] ends a quoted string at its line, so that an apostrophe costs one line", () => {
    expect(uncommented("<p>don't</p>\n/* c */ ok")).toBe("<p>don't</p>\n ok");
  });
});
