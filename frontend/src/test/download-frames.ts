// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The hidden frames the result of an export downloads by itself through (`downloadWhenThere`,
 * #3103), held by a test: happy-dom loads no page in a frame, and would say so on the error output.
 * A frame is kept out of the document, its address read by the test; the route refusing, the test
 * sends it back to the screen, with the refusal in its address, as the route would.
 */
import { vi } from "vitest";

/** Hold the frames appended to the body from now on, until the spies are restored. */
export function heldFrames(): readonly HTMLIFrameElement[] {
  const frames: HTMLIFrameElement[] = [];
  const append = document.body.append.bind(document.body);
  vi.spyOn(document.body, "append").mockImplementation((...nodes) => {
    for (const node of nodes) {
      if (node instanceof HTMLIFrameElement) {
        frames.push(node);
      } else {
        append(node);
      }
    }
  });
  return frames;
}

/** Load in a frame held the screen the route sends it back to, at the address given. */
export function sendBack(frame: HTMLIFrameElement, address: string): void {
  const { search } = new URL(address, window.location.origin);
  Object.defineProperty(frame, "contentWindow", { value: { location: { search } } });
  frame.dispatchEvent(new Event("load"));
}
