// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { CHART_ROOM, roomForCharts } from "./chart-room";
import { takeStderr, watchStderr } from "./stderr";

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

describe("the error output of a component test", () => {
  it("is watched: what a test writes there is kept, to fail the test once it ends", () => {
    // A console of its own, watched as the console of the tests is, which writes nowhere.
    const [error, warn] = [vi.fn(), vi.fn()];
    const own = { error, warn, trace: vi.fn() };
    watchStderr(own);
    own.warn("[ECharts] Can't get DOM width or height.");
    own.error("an error", { code: 42 });
    // Each line still goes out.
    expect(warn).toHaveBeenCalledWith("[ECharts] Can't get DOM width or height.");
    expect(error).toHaveBeenCalledWith("an error", { code: 42 });
    // Taken here, so that this test passes: the setup takes it after each test, and fails it.
    const test = expect.getState().currentTestName ?? "";
    expect(takeStderr()).toEqual([
      `${test} › console.warn: [ECharts] Can't get DOM width or height.`,
      `${test} › console.error: an error { code: 42 }`,
    ]);
    expect(takeStderr()).toEqual([]);
  });

  it("leaves to a test what it catches by a spy on the console, which writes nothing", () => {
    const told = vi.spyOn(console, "error").mockImplementation(() => undefined);
    console.error("an error the test proves is told");
    expect(told).toHaveBeenCalledOnce();
    told.mockRestore();
    expect(takeStderr()).toEqual([]);
  });
});

describe("a line written on the error output after its test", () => {
  // A console of its own, watched as the console of the tests is, which writes nowhere.
  const own = { error: vi.fn(), warn: vi.fn(), trace: vi.fn() };
  watchStderr(own);
  let written: readonly string[] = [];
  let running: string | undefined;

  it("is left to a timer the test does not wait for", () => {
    setTimeout(() => {
      running = expect.getState().currentTestName;
      own.warn("written late");
      // Taken as it is written, so that the setup does not fail the test it lands in.
      written = takeStderr();
    }, 0);
  });

  it("is told under the name of the test running as it was written", async () => {
    await vi.waitFor(() => {
      expect(written).toHaveLength(1);
    });
    expect(written).toEqual([`${running ?? "(before any test)"} › console.warn: written late`]);
  });
});

describe("the room of a chart", () => {
  roomForCharts();

  it("sizes the drawing of a chart alone, and leaves every other element as the document measures it", () => {
    render(
      <figure>
        <div role="img" aria-label="Une courbe" />
        <div data-testid="beside" />
      </figure>,
    );
    const drawing = screen.getByRole("img", { name: "Une courbe" });
    expect([drawing.clientWidth, drawing.clientHeight]).toEqual([
      CHART_ROOM.width,
      CHART_ROOM.height,
    ]);
    expect(screen.getByTestId("beside").clientWidth).toBe(0);
  });
});
