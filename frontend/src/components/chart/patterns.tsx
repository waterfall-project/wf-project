// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether the account asks for the patterns of the series of its charts (WF-ADM-0040,
 * WF-IHM-0070, WF-IHM-0130): one preference of the account, `chart_series_patterns`, off when the
 * account never asked for it. The layout reads it with the account (`getMe`) once per request and
 * hands it down; `Chart` alone reads it, and draws every chart with it — the patterns of the bars,
 * the symbols of the points, the legend and the exported image (`ChartPalette.patterns`): one
 * point of decision, no command on each chart (EP-25, « Les motifs d'un graphique se décident en
 * un point »).
 *
 * A module apart from the chart, so that the layout mounts the provider without the drawing.
 */
"use client";

import { createContext, type ReactNode, useContext } from "react";

const ChartPatternsContext = createContext(false);

/** Make the preference of the account available to the charts below. */
export function ChartPatternsProvider({
  patterns,
  children,
}: {
  readonly patterns: boolean;
  readonly children: ReactNode;
}) {
  return <ChartPatternsContext value={patterns}>{children}</ChartPatternsContext>;
}

/** Whether the series of a chart are drawn with their patterns and their symbols. */
export function useChartPatterns(): boolean {
  return useContext(ChartPatternsContext);
}
