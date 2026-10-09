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
 * their changes. Without one, each user keeps its own — the grid alone, as on the planning, shares
 * its own with its bar. What was asked is forgotten once the screen shows another address than the
 * one it was asked from: it has arrived, another navigation replaced it, or the history went back
 * or forward — back to the very address it was asked from too, which then shows as it is, the
 * change given up never applied again by the next one. Whether the address shown is the one a
 * navigation asked tells an entry made while it was under way, which its arrival keeps
 * (`useDatedState`), from one the history comes back over, which is forgotten.
 */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  type RefObject,
  useContext,
  useLayoutEffect,
  useRef,
} from "react";

/**
 * An address asked, by its query, and the query of the address it was asked from; and the streak it
 * ends: the queries of every address asked from that same address, each composed on the one before
 * it before any arrived — a search, then a sort that carries it —, of which the one that arrives
 * is the last asked, or one Next had not dropped yet.
 */
export interface Asked {
  readonly from: string;
  readonly query: string;
  /**
   * Shared by every address of the streak, so that an entry made while the first was under way
   * knows of those asked after it; added to by an event alone, never by a render.
   */
  readonly streak: Set<string>;
}

/** The address a screen last asked for; none outside a screen that shares one. */
const AskedContext = createContext<RefObject<Asked | undefined> | undefined>(undefined);

/**
 * Share the address last asked for among the parts of a screen — or of a grid, which shares it
 * with its bar: one already shared around it is kept, the grid composing with its screen.
 */
export function PendingAddress({ children }: { readonly children: ReactNode }) {
  const around = useContext(AskedContext);
  // A ref, stable from the first render: the value of the context never changes.
  const asked = useRef<Asked>(undefined);
  return <AskedContext value={around ?? asked}>{children}</AskedContext>;
}

/** The query of an address, as the address shown writes it once arrived. */
function queryOf(href: string): string {
  const [address = ""] = href.split("#");
  return new URLSearchParams(address.split("?")[1] ?? "").toString();
}

/**
 * The query of the address shown, the navigation asked from it and not arrived yet, and how to ask
 * one: what was asked is forgotten once the screen shows another address than the one it was asked
 * from.
 */
function useAsked() {
  const shared = useContext(AskedContext);
  const own = useRef<Asked>(undefined);
  const askedRef = shared ?? own;
  const shown = useSearchParams().toString();
  // Forgotten as the address shown is committed: only an event reads what was asked, never a
  // render, and no event runs between a commit and its layout effects (défaut n° 2).
  useLayoutEffect(() => {
    if (askedRef.current !== undefined && askedRef.current.from !== shown) {
      askedRef.current = undefined;
    }
  }, [askedRef, shown]);
  return {
    shown,
    /** The navigation asked from the address shown and not arrived yet; none. Read in an event. */
    underWay: (): Asked | undefined =>
      askedRef.current?.from === shown ? askedRef.current : undefined,
    /**
     * Keep an address as asked from the one shown, in the streak of one still under way; the
     * address shown itself asks nothing, and gives up what was under way, which Next drops for it.
     */
    ask: (href: string) => {
      const query = queryOf(href);
      if (query === shown) {
        askedRef.current = undefined;
        return;
      }
      const streak = askedRef.current?.from === shown ? askedRef.current.streak : new Set<string>();
      streak.add(query);
      askedRef.current = { from: shown, query, streak };
    },
  };
}

/**
 * The query a change goes on from — the one last asked, until it arrives, or that of the
 * address —, and how to navigate to an address built from it.
 */
export function usePendingAddress() {
  const { shown, underWay, ask } = useAsked();
  const router = useRouter();
  /** The query a change goes on from. */
  const base = () => new URLSearchParams(underWay()?.query ?? shown);
  /** Navigate to an address built from the query a change goes on from, and keep it as asked. */
  const request = (build: (query: URLSearchParams) => string) => {
    const href = build(base());
    ask(href);
    router.push(href, { scroll: false });
  };
  return { base, request };
}

/**
 * The navigation a screen asked and that has not arrived yet, read when an entry is made, and
 * whether the address shown is the one a navigation asked — or one composed on it before it
 * arrived, a sort clicked while the search sent was on its way —: an entry made while it was under
 * way survives its arrival (`useDatedState`). It is shared by a screen, a grid or a filter
 * (`PendingAddress`): a part that asks no navigation of its own, outside of them, knows of none, and
 * its entry is forgotten whenever the address changes it.
 */
export function useAskedArrival() {
  const { shown, underWay } = useAsked();
  return {
    /** The navigation under way; none. Read in an event, never in a render. */
    underWay,
    /** Whether the address shown ends the streak of a navigation; never for none. */
    arrived: (navigation: Asked | undefined): boolean => navigation?.streak.has(shown) ?? false,
  };
}

/**
 * A link of the screen to an address built from its query: its `href`, from the address shown, for
 * the browser — a new tab, a new window, a click with a modifier —, and a plain click, which goes
 * on from the address last asked (`usePendingAddress`): a sort or a filter under way is kept.
 */
export function usePendingLink(build: (query: URLSearchParams) => string) {
  const address = useSearchParams();
  const { request } = usePendingAddress();
  return {
    href: build(new URLSearchParams(address)),
    onClick: (event: MouseEvent<HTMLAnchorElement>) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      event.preventDefault();
      request(build);
    },
  };
}
