// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The hidden frames the result of an export downloads by itself through (`downloadWhenThere`,
 * #3103), held by a test. A frame is put in the document, as the screen puts it, so that a test sees
 * it go — after a refusal, or once it has been kept long enough (`frame.isConnected`, #3298) —, but
 * loads no page: happy-dom would ask the network for its address, and say on the error output that it
 * cannot. It loads instead an empty document of its own (`srcdoc`), which happy-dom makes with no
 * request, its address kept in its `src`; the load of that document is no answer of the route, and
 * reaches no listener of the screen. The route refusing, the test sends the frame back to the screen,
 * with the refusal in its address, as the route would. Every frame held leaves the document with the
 * test.
 */
import { onTestFinished, vi } from "vitest";

/** The loads a test sends, as the route would answer: the only ones a frame held lets through. */
const SENT_BACK = new WeakSet<Event>();

/** Keep from the screen the load of the empty document of a frame held: the route answered nothing. */
function untilSentBack(event: Event): void {
  if (!SENT_BACK.has(event)) {
    event.stopImmediatePropagation();
  }
}

/** Hold the frames appended to the body from now on, until the spies are restored. */
export function heldFrames(): readonly HTMLIFrameElement[] {
  const frames: HTMLIFrameElement[] = [];
  const append = document.body.append.bind(document.body);
  vi.spyOn(document.body, "append").mockImplementation((...nodes) => {
    for (const node of nodes) {
      if (node instanceof HTMLIFrameElement) {
        frames.push(node);
        node.setAttribute("srcdoc", "");
        // Heard while the event goes down to the frame, before any listener of the screen on it.
        node.addEventListener("load", untilSentBack, { capture: true });
      }
      append(node);
    }
  });
  onTestFinished(() => {
    for (const frame of frames) {
      frame.remove();
    }
  });
  return frames;
}

/** Load in a frame held the screen the route sends it back to, at the address given. */
export function sendBack(frame: HTMLIFrameElement, address: string): void {
  const { search } = new URL(address, window.location.origin);
  Object.defineProperty(frame, "contentWindow", { value: { location: { search } } });
  const load = new Event("load");
  SENT_BACK.add(load);
  frame.dispatchEvent(load);
}
