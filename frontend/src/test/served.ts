// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A component as the server sends it, then as React hydrates it in the browser: the markup of
 * `renderToString` put in a document, and `hydrateRoot` on it. A discordance between the two is
 * told by React on the console, which fails the test (`src/test/stderr.ts`).
 */
import { act } from "@testing-library/react";
import type { ReactNode } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";

/** The markup the server sends, in the document; hydrated by `hydrate`, let go by `unmount`. */
export interface Served {
  readonly container: HTMLElement;
  readonly hydrate: () => Promise<void>;
  readonly unmount: () => Promise<void>;
}

/** Put in the document what the server sends for a component, to hydrate it when the test says. */
export function served(node: ReactNode): Served {
  const container = document.createElement("div");
  container.innerHTML = renderToString(node);
  document.body.append(container);
  let root: Root | undefined;
  return {
    container,
    hydrate: async () => {
      await act(async () => {
        root = hydrateRoot(container, node);
        await Promise.resolve();
      });
    },
    unmount: async () => {
      await act(async () => {
        root?.unmount();
        await Promise.resolve();
      });
      container.remove();
    },
  };
}
