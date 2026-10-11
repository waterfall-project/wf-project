// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A link of the page under the hold of its navigations (#688): what a test clicks while a write of
 * the screen answers, to see whether the click is followed.
 */
import { fireEvent, renderHook } from "@testing-library/react";
import { type Mock, vi } from "vitest";

import { useNavigationHold } from "@/components/shell/navigation-hold";

/** A link of the page, the navigations of the page held by the writes of its screens. */
export interface HeldLink {
  /** Called when the click is followed, its navigation prevented: the document stays. */
  readonly followed: Mock<(event: MouseEvent) => void>;
  /** Click the link as a pointer does: down, then the click. */
  readonly click: () => void;
  /** Take the link out of the page. */
  readonly remove: () => void;
}

/** Hold the navigations of the page as the shell does, and put a link in it. */
export function heldLink(href = "/portfolio"): HeldLink {
  renderHook(() => {
    useNavigationHold();
  });
  const followed = vi.fn((event: MouseEvent) => {
    event.preventDefault();
  });
  const link = document.createElement("a");
  link.href = href;
  link.addEventListener("click", followed);
  document.body.append(link);
  return {
    followed,
    click: () => {
      fireEvent.pointerDown(link);
      link.click();
    },
    remove: () => {
      link.remove();
    },
  };
}
