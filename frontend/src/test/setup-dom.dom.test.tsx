// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

/** A client component in miniature: state, and an event that changes it. */
function Counter() {
  const [count, setCount] = useState(0);
  return (
    <button
      type="button"
      onClick={() => {
        setCount(count + 1);
      }}
    >
      {count}
    </button>
  );
}

// The project of the client components renders into a document, and cleans it after
// each test; no client component exists yet to prove it on.
describe("the component tests", () => {
  it("render a component and play an event on it", async () => {
    render(<Counter />);
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveTextContent("1");
  });

  it("start from an empty document", () => {
    expect(document.body).toBeEmptyDOMElement();
  });
});
