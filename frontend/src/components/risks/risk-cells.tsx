// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the risks that show more than a value formatted: the label of a risk,
 * a link to its detail on the same screen — its description, its mitigation, the history of its
 * reviews (WF-RIS-0040) —, out of the order of tabulation, the grid being one stop, which follows
 * it on Enter (`grid-keyboard.ts`); its state, by the catalogue; the cell of the matrix it falls
 * in, by the one signal of the application (WF-IHM-0070), whose zone the server gives. And the
 * link that closes the detail, which keeps the rest of the address as the label's does.
 */
"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useContext } from "react";

import { usePendingLink } from "@/components/grid/pending-address";
import { Signal } from "@/components/signal/signal";
import { buttonVariants } from "@/components/ui/button";

import { originHref, readRisk, riskHref } from "./address";
import type { RiskRow } from "./risk-grid";

/**
 * Open the detail of a risk — or close it, `undefined` —, from the address last asked: a sort or a
 * filter under way is kept. A click with a modifier is the browser's: a new tab, a new window — on
 * the `href`, which reflects the address shown, not the one asked: a Ctrl+click during a sort
 * opens the tab without the sort (#288).
 */
export function useRiskNavigation(risk: string | undefined) {
  const pathname = usePathname();
  return usePendingLink((query) => riskHref(pathname, query, risk));
}

/** Render the label of a risk, as a link to its detail; the risk shown says so. */
export function RiskLabelCell({ risk }: { readonly risk: RiskRow }) {
  const shown = readRisk(useSearchParams()) === risk.risk_id;
  const { href, onClick } = useRiskNavigation(risk.risk_id);
  return (
    <Link
      href={href}
      onClick={onClick}
      tabIndex={-1}
      aria-current={shown ? "true" : undefined}
      title={risk.label}
      className="block truncate underline-offset-2 hover:underline aria-[current]:font-semibold"
      scroll={false}
    >
      {risk.label}
    </Link>
  );
}

const ORIGIN_GRID = createContext<string | undefined>(undefined);

/**
 * Give the cells of the states the address of the grid of the revision, in its context, which the
 * state of a risk occurred leads to, filtered on it — the estimate, the planning when the session
 * does not read the estimate; none, and they lead nowhere (it reads neither).
 */
export function OccurredLines({
  originGrid,
  children,
}: {
  readonly originGrid: string | undefined;
  readonly children: ReactNode;
}) {
  return <ORIGIN_GRID.Provider value={originGrid}>{children}</ORIGIN_GRID.Provider>;
}

/**
 * Render the state of a risk, in the language of the interface. A risk occurred leads to the grid
 * of the revision filtered on the lines that came of it (`origin_risk_ids`, WF-RIS-0060) — the
 * estimate, or the planning for a session that does not read it: the estimate prices them, and the
 * reestimated amount of the register is their sum. The link is the cell's, which Enter follows;
 * its name keeps the state, as the cell shows it.
 */
export function RiskStateCell({ risk }: { readonly risk: RiskRow }) {
  const t = useTranslations("enums.RiskState");
  const lines = useTranslations("risks.coverage");
  const originGrid = useContext(ORIGIN_GRID);
  const state = t(risk.state);
  if (risk.state !== "occurred" || originGrid === undefined) {
    return (
      <span className="truncate" title={state}>
        {state}
      </span>
    );
  }
  const named = lines("occurredLines", { risk: risk.label });
  return (
    <Link
      href={originHref(originGrid, risk.risk_id)}
      tabIndex={-1}
      aria-label={lines("occurredStateLines", { state, risk: risk.label })}
      title={named}
      className="block truncate underline underline-offset-2"
    >
      {state}
    </Link>
  );
}

/** Render the cell of the matrix a risk falls in, by its signal. */
export function RiskZoneCell({ risk }: { readonly risk: RiskRow }) {
  return <Signal zone={risk.matrix_cell.zone} variant="icon" />;
}

/** Render the link that closes the detail of a risk: the same screen, its query kept, without it. */
export function CloseRiskDetail() {
  const t = useTranslations("risks.detail");
  const { href, onClick } = useRiskNavigation(undefined);
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      aria-label={t("close")}
      className={buttonVariants({ variant: "ghost", size: "icon" })}
    >
      <X aria-hidden="true" className="size-4" />
    </Link>
  );
}
