// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The address a screen last asked for, until it arrives. A sort, a search, a filter, a detail
 * opened only change the address, and the server answers anew; until the navigation arrives, the
 * address the browser reads is still the one before, and Next drops a navigation under way for
 * the next one. A change made meanwhile must then go on from the address asked, not from the one
 * shown: a filter chosen right after a sort carries the sort, and a second state chosen the first.
 *
 * One source for a whole screen (`PendingAddress`): the grid, its filter and its links compose
 * their changes. Without one, each user keeps its own — the grid alone, as on the planning. What
 * was asked is forgotten once the address of the screen changes: it has arrived, or another
 * navigation replaced it.
 */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { createContext, type ReactNode, type RefObject, useContext, useRef } from "react";

/** The address asked, by its query, and the query of the address it was asked from. */
interface Asked {
  readonly from: string;
  readonly query: string;
}

/** The address a screen last asked for; none outside a screen that shares one. */
const AskedContext = createContext<RefObject<Asked | undefined> | undefined>(undefined);

/** Share the address last asked for among the parts of a screen. */
export function PendingAddress({ children }: { readonly children: ReactNode }) {
  // A ref, stable from the first render: the value of the context never changes.
  const asked = useRef<Asked>(undefined);
  return <AskedContext value={asked}>{children}</AskedContext>;
}

/**
 * The query a change goes on from — the one last asked, until it arrives, or that of the
 * address —, and how to navigate to an address built from it.
 */
export function usePendingAddress() {
  const shared = useContext(AskedContext);
  const own = useRef<Asked>(undefined);
  const asked = shared ?? own;
  const router = useRouter();
  const address = useSearchParams();
  /** The query a change goes on from. */
  const base = () => {
    const from = address.toString();
    return new URLSearchParams(asked.current?.from === from ? asked.current.query : from);
  };
  /** Navigate to an address built from the query a change goes on from, and keep it as asked. */
  const request = (build: (query: URLSearchParams) => string) => {
    const href = build(base());
    asked.current = { from: address.toString(), query: href.split("?")[1] ?? "" };
    router.push(href, { scroll: false });
  };
  return { base, request };
}
