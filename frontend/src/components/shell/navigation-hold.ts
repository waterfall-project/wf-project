// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The navigations of the page held while a write is under way (#688): a click on a link of the
 * front — the side bar, a breadcrumb, a link of the screen — waits until every write has answered,
 * then is made again as it was, the link deciding how it navigates; one write refused, it is not
 * made at all, and the screen says the refusal where the write was (`held-writes.ts`). A link to
 * another site, to another tab, or a download, is left alone; so is a click with a modifier, which
 * opens elsewhere.
 *
 * Listened for on the document as the click goes down, before the router of Next sees it.
 */
"use client";

import { useEffect } from "react";

import { writesApplied, writesUnderWay } from "@/navigation/held-writes";

/** The link of the front a click would follow in this tab, if any. */
function followedLink(event: MouseEvent): HTMLAnchorElement | undefined {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return undefined;
  }
  const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
  if (
    !(link instanceof HTMLAnchorElement) ||
    !["", "_self"].includes(link.target) ||
    link.hasAttribute("download")
  ) {
    return undefined;
  }
  return new URL(link.href, window.location.href).origin === window.location.origin
    ? link
    : undefined;
}

/** Hold the navigations of the page while a write is under way, and drop them when one is refused. */
export function useNavigationHold(): void {
  useEffect(() => {
    const hold = (event: MouseEvent) => {
      const link = writesUnderWay() ? followedLink(event) : undefined;
      if (link === undefined) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      void writesApplied().then((applied) => {
        if (applied && link.isConnected) {
          link.click();
        }
      });
    };
    document.addEventListener("click", hold, true);
    return () => {
      document.removeEventListener("click", hold, true);
    };
  }, []);
}
