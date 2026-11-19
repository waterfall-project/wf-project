// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type OccurrenceReport, ReportBody } from "./occurrence-report";

const REPORT = example("risk_occurrence_report") as OccurrenceReport;

/** The report as the contract gives it, with what the survenance of #4133 and #4134 adds. */
const REDATING: OccurrenceReport = {
  ...REPORT,
  own_estimate_past_planning_start_on: "2026-03-02",
  differences: [
    ...REPORT.differences,
    {
      change: "updated",
      target: "task",
      lineage_id: "01926f3a-7c00-7000-8000-000000000653",
      label: "Essais de réception",
      predecessor_label: null,
      fields: ["start", "finish"],
    },
  ],
};

function shown(report: OccurrenceReport) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ReportBody report={report} />
    </NextIntlClientProvider>,
  );
}

describe("le compte rendu de la survenance", () => {
  it("présente en tâche modifiée chaque tâche que la greffe redate, après la tâche porteuse [US-2640] [WF-IHM-0020-A]", () => {
    shown(REDATING);
    const table = screen.getByRole("table", { name: /écarts/i });
    const row = within(table).getByRole("row", { name: /Essais de réception/ });
    expect(within(row).getAllByRole("cell")[0]).toHaveAccessibleName("Modifié");
    expect(row).toHaveTextContent(/Début/);
    expect(row).toHaveTextContent(/Fin/);
  });

  it("signale un devis propre qui commence avant le jour de la déclaration, sans le refuser [US-2640] [WF-IHM-0020-A]", () => {
    shown(REDATING);
    expect(screen.getByRole("note")).toHaveTextContent(/commence le 2 mars 2026, avant le jour/);
    // Un avertissement, non un motif de refus : rien n'est dit en alerte.
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ne signale rien quand le devis propre ne commence pas avant le jour [US-2640] [WF-IHM-0020-A]", () => {
    const { unmount } = shown({ ...REPORT, own_estimate_past_planning_start_on: null });
    expect(screen.queryByRole("note")).toBeNull();
    unmount();
    shown(REPORT);
    expect(screen.queryByRole("note")).toBeNull();
  });
});
