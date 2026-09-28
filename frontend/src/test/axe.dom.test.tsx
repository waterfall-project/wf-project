// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import { expectAccessible } from "./axe";

// The helper runs under happy-dom: it must find what axe finds in a browser, not pass
// everything because the document is simulated.
describe("expectAccessible", () => {
  it("passes a component whose controls all have a name", async () => {
    const { container } = render(
      <form aria-label="Display mode">
        <label htmlFor="mode">Mode</label>
        <select id="mode">
          <option>Dark</option>
        </select>
        <ul>
          <li>
            <button type="submit">Apply</button>
          </li>
        </ul>
      </form>,
    );
    await expectAccessible(container);
  });

  it.each([
    ["a button without a name", <button key="b" type="button" />, "button-name"],
    // Written without JSX: the linter would refuse the very defect this case traps.
    ["an image without a text", createElement("img", { src: "/logo.svg" }), "image-alt"],
    [
      "a field without a label",
      <select key="s">
        <option>fr</option>
      </select>,
      "select-name",
    ],
    ["a list item out of a list", <li key="l">item</li>, "listitem"],
  ])("fails %s", async (_, element, rule) => {
    const { container } = render(element);
    const failure = await expectAccessible(container).then(
      () => undefined,
      (error: unknown) => String(error),
    );
    expect(failure).toContain(rule);
  });
});
