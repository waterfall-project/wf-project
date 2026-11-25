// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type OccurrenceReport, ReportBody } from "./occurrence-report";

const REPORT = example("risk_occurrence_report") as OccurrenceReport;

/**
 * The report as the contract gives it, with what the occurrence of #4133 and #4134 adds. The
 * difference `updated` of a task redated is derived by hand from the example `risk_occurrence_report`:
 * no example of the contract carries it (the contract is frozen, #4134 form 1).
 */
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

  it("ne dit aucune rangée de moins ni ne déplace le focus pour un compte rendu court, lu en entier [US-3280] [WF-INTF-0080-A]", () => {
    shown(REDATING);
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.queryByText(/rangées/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Tout afficher" })).toBeNull();
    expect(document.body).toHaveFocus();
  });

  it("rend toutes les rangées d'un tableau d'écarts non limité, sans bouton [US-3280] [WF-INTF-0080-A]", () => {
    const [difference] = REPORT.differences;
    if (difference === undefined) {
      throw new Error("the example has no difference");
    }
    shown({ ...REPORT, differences: Array.from({ length: 250 }, () => difference) });
    const table = screen.getByRole("table", { name: /écarts/i });
    expect(within(table).getAllByRole("row")).toHaveLength(251);
    expect(screen.queryByRole("button", { name: "Tout afficher" })).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("signale un devis propre qui commence avant le jour de la déclaration, sans le refuser [US-2640] [WF-IHM-0020-A]", () => {
    shown(REDATING);
    expect(screen.getByRole("note")).toHaveTextContent(/commence le 2 mars 2026, avant le jour/);
    // Un avertissement, non un motif de refus : rien n'est dit en alerte.
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ne signale pas de départ passé quand le contrat n'en donne aucun, que le report crée la révision ou non [US-2640] [WF-IHM-0020-A]", () => {
    // The example has `creates_current_revision` false: that the absence of a note comes from the date
    // alone is proven with the revision created, whose own note is the only one told.
    const { unmount } = shown({ ...REPORT, own_estimate_past_planning_start_on: null });
    expect(screen.queryByRole("note")).toBeNull();
    unmount();
    shown({
      ...REPORT,
      creates_current_revision: true,
      own_estimate_past_planning_start_on: null,
    });
    expect(screen.getAllByRole("note")).toHaveLength(1);
    expect(screen.getByRole("note")).toHaveTextContent(/crée d’abord par copie/);
    expect(screen.queryByText(/commence le/)).toBeNull();
  });

  it("dit les deux notes quand la révision est créée et que le devis propre commence avant le jour [US-2640] [WF-IHM-0020-A]", () => {
    shown({ ...REDATING, creates_current_revision: true });
    const notes = screen.getAllByRole("note");
    expect(notes).toHaveLength(2);
    expect(screen.getByText(/crée d’abord par copie/)).toBeVisible();
    expect(screen.getByText(/commence le 2 mars 2026/)).toBeVisible();
  });

  it.each([
    ["2026-03-01", "1 mars 2026"],
    ["2026-12-31", "31 déc. 2026"],
  ])(
    "dit le jour calendaire %s sans le décaler, quel que soit le fuseau de l'écran [US-2640] [WF-IHM-0020-A]",
    (day, said) => {
      render(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="Pacific/Auckland">
          <ReportBody report={{ ...REDATING, own_estimate_past_planning_start_on: day }} />
        </NextIntlClientProvider>,
      );
      expect(screen.getByRole("note")).toHaveTextContent(`commence le ${said}, avant`);
    },
  );
});
