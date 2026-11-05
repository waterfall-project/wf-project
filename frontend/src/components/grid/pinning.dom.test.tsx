// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useFrameRoom } from "./pinning";

describe("the room of the frame of a grid", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** A frame in its holder, which shows the room it measures. */
  function Grid() {
    const frame = useRef<HTMLDivElement>(null);
    const room = useFrameRoom(frame);
    return (
      <div>
        <div ref={frame} data-testid="frame" data-room={room ?? "none"} />
      </div>
    );
  }

  it("is none where the browser does not lay out", () => {
    const { getByTestId } = render(<Grid />);
    expect(getByTestId("frame").dataset.room).toBe("none");
  });

  it("is the width of the holder less the borders and the scroll bar of the frame, where a test sizes the boxes", () => {
    // The bridge of the test setup gives the inside of an element as its box: without border nor
    // scroll bar, the room is the whole width of the holder.
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
    const { getByTestId } = render(<Grid />);
    expect(getByTestId("frame").dataset.room).toBe("1600");
  });
});
