// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { plain, textOfMarkup } from "./page-stream";

describe("the reading of the markup of a page (#3935)", () => {
  it("cuts a comment which holds a line break [WF-QUA-0010-A]", () => {
    expect(plain("a<!-- one\ntwo -->b")).toBe("ab");
    expect(textOfMarkup("a<!-- one\ntwo -->b")).toBe("ab");
  });

  it("drops what follows a comment left open [WF-QUA-0010-A]", () => {
    expect(plain("a<!-- never closed <b>b</b>")).toBe("a");
    expect(textOfMarkup("a<!-- never closed <b>b</b>")).toBe("a");
  });

  it("separates the texts of neighbouring tags by a space [WF-QUA-0010-A]", () => {
    expect(textOfMarkup("<p>one</p><p>two</p>")).toBe(" one  two ");
  });

  it("reads the escaped quote as a quote [WF-QUA-0010-A]", () => {
    expect(plain("l&#x27;a")).toBe("l'a");
    expect(textOfMarkup("<i>l&#x27;a</i>")).toBe(" l'a ");
  });
});
