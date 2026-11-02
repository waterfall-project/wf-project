// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { isApplicationPath } from "./application-path";

const CONTROLS = [
  ...Array.from({ length: 0x20 }, (_, code) => String.fromCharCode(code)),
  String.fromCharCode(0x7f),
];

describe("the guard of an address the front follows back", () => {
  it("refuses every control character, U+0000 to U+001F and U+007F, wherever it stands [WF-SEC-0010-A]", () => {
    for (const control of CONTROLS) {
      const code = control.charCodeAt(0).toString(16);
      expect(isApplicationPath(`/${control}/elsewhere`), code).toBe(false);
      expect(isApplicationPath(`/projects?label=a${control}`), code).toBe(false);
    }
  });

  it.each(["//elsewhere", "/\\elsewhere", "/projects\\x", "https://elsewhere", "projects", ""])(
    "refuses %j, which is no path of the front as written [WF-SEC-0010-A]",
    (address) => {
      expect(isApplicationPath(address)).toBe(false);
    },
  );

  it.each(["/", "/projects?states=active,planned", "/a b/é", "/%2F%2Felsewhere", "/~"])(
    "follows the path of the front %j",
    (address) => {
      expect(isApplicationPath(address)).toBe(true);
    },
  );
});
