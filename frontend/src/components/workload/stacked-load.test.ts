// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { ChartPalette } from "@/components/chart/chart";
import { example } from "@/test/fixtures";

import { type LoadRole, monthTooltip, stackedRoles } from "./stacked-load";

const PALETTE: ChartPalette = {
  series: ["rgb(1, 1, 1)", "rgb(2, 2, 2)", "rgb(3, 3, 3)"],
  text: "rgb(3, 3, 3)",
  mark: "rgb(4, 4, 4)",
  axis: "rgb(5, 5, 5)",
  grid: "rgb(6, 6, 6)",
  background: "rgb(7, 7, 7)",
  zones: { nominal: "nominal", watch: "watch", alert: "alert" },
  font: "sans-serif",
};

/** The roles of the witness project, as the service gives them: the third is loaded on 8 months. */
const ROLES = (example("workload") as { roles: LoadRole[] }).roles;

/** The `[instant, hours]` points of each series. */
function points(roles: readonly LoadRole[]) {
  return stackedRoles(PALETTE, roles).map((series) => series.data);
}

describe("the series of the roles of a stack of bars", () => {
  it("ranks the points of a role loaded on fewer months at the ranks of the others, the months it lacks left empty [WF-DEV-0070-A]", () => {
    const [electrician, technician, wirer] = points(ROLES);
    expect(ROLES.map((role) => role.months.length)).toEqual([38, 38, 8]);
    // Every series holds the same months, in the same order: ECharts stacks by rank.
    const instants = (data: typeof electrician) => data?.map(([instant]) => instant);
    expect(instants(technician)).toEqual(instants(electrician));
    expect(instants(wirer)).toEqual(instants(electrician));
    // The 38 months of the first two roles lack December 2027, which the third carries: 39.
    expect(electrician).toHaveLength(39);
    const rank = (month: string) => instants(electrician)?.indexOf(`${month}-01T00:00:00Z`) ?? -1;
    expect(instants(electrician)).toEqual([...(instants(electrician) ?? [])].sort());
    // The wirer is on its own months, at the rank of those months — September 2027, not June 2026.
    expect(wirer?.[rank("2027-09")]).toEqual(["2027-09-01T00:00:00Z", ROLES[2]?.months[0]?.hours]);
    expect(wirer?.[rank("2026-06")]?.[1]).toBe("-");
    expect(wirer?.[rank("2029-08")]?.[1]).toBe("-");
    // And the others are empty in December 2027, where only the wirer is loaded.
    expect(electrician?.[rank("2027-12")]?.[1]).toBe("-");
    expect(wirer?.[rank("2027-12")]?.[1]).not.toBe("-");
  });

  it("keeps the hours of the API as they are: nothing is summed, nothing is rounded [WF-DEV-0070-A]", () => {
    const [electrician] = points(ROLES);
    const given = new Map(
      ROLES[0]?.months.map((each) => [`${each.month}-01T00:00:00Z`, each.hours]),
    );
    for (const [instant, hours] of electrician ?? []) {
      if (hours !== "-") {
        expect(hours).toBe(given.get(String(instant)));
      }
    }
  });
});

describe("the tooltip of a month", () => {
  const tooltip = monthTooltip("en", (hours) => `${hours} h`) as {
    formatter: (params: unknown) => string;
  };
  const row = (name: string, hours: string) => ({
    seriesName: name,
    marker: "",
    value: ["2027-12-01T00:00:00Z", hours],
  });

  it("lists the roles loaded that month alone, then the total of the server, without error on a role that has no load [WF-DEV-0070-A]", () => {
    expect(
      tooltip.formatter([
        row("Ingénieur électricien", "-"),
        row("Technicien de mise en service", "-"),
        row("Monteur câbleur", "1650.00"),
        row("Total", "1650.00"),
      ]),
    ).toBe(
      ["<b>December 2027</b>", "Monteur câbleur <b>1,650.00 h</b>", "Total <b>1,650.00 h</b>"].join(
        "<br/>",
      ),
    );
  });
});
