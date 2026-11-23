// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type OccurrenceReport, ReportBody } from "./occurrence-report";

// The report in the form of a merge: the task the own estimate abandons is kept and completed.
const ABANDONED = example("risk_occurrence_report_abandoned_task") as OccurrenceReport;
// The report as EP-08 gave it, which still carries the two signals the screen no longer tells.
const GRAFT = example("risk_occurrence_report") as OccurrenceReport;

function shown(report: OccurrenceReport) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ReportBody report={report} />
    </NextIntlClientProvider>,
  );
}

describe("le compte rendu de la survenance", () => {
  it("présente les tâches qu'elle termine et la valeur acquise qu'elles apportent [US-3140]", () => {
    shown(ABANDONED);
    const completed = screen.getByRole("region", { name: "Tâches terminées par la survenance" });
    expect(completed).toHaveTextContent(/1 tâche terminée par la survenance/);
    expect(within(completed).getByText(/« Mise en service »/)).toBeVisible();
    expect(completed).toHaveTextContent(/Valeur acquise apportée : 6\s074,57/);
  });

  it("présente ce qu'elle garde et ce qu'elle retire, dans les marques de la grille [US-3140]", () => {
    shown(ABANDONED);
    const table = screen.getByRole("table", { name: /écarts/i });
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(table).toHaveTextContent(/Mise en service/);
    expect(table).toHaveTextContent(/Provision — Mise en service/);
  });

  it("dit la valeur acquise retirée et nomme les tâches terminées qu'elle rouvre [US-3140]", () => {
    shown({
      ...ABANDONED,
      reopened_tasks: [{ lineage_id: "01926f3a-7c00-7000-8000-000000000666", label: "Essais" }],
      earned_value_removed: "1200.00",
    });
    const reopened = screen.getByRole("region", { name: "Tâches rouvertes par la survenance" });
    expect(reopened).toHaveTextContent(/1 tâche terminée rouverte/);
    expect(within(reopened).getByText(/« Essais » : terminée, elle est rouverte/)).toBeVisible();
    expect(reopened).toHaveTextContent(/Valeur acquise retirée : 1\s200,00/);
  });

  it("ne dit ni tâche terminée ni tâche rouverte quand la survenance n'en a aucune [US-3140]", () => {
    shown({
      main_structure_lock_version: ABANDONED.main_structure_lock_version,
      risk_lock_version: ABANDONED.risk_lock_version,
      creates_current_revision: false,
      differences: ABANDONED.differences,
      provision_amount: ABANDONED.provision_amount,
      refusals: [],
    });
    expect(screen.queryByRole("region", { name: /Tâches terminées/ })).toBeNull();
    expect(screen.queryByRole("region", { name: /Tâches rouvertes/ })).toBeNull();
  });

  it("dit ce qui la refuse, en alerte [US-3140]", () => {
    shown({ ...ABANDONED, refusals: [{ code: "TASK_WITHOUT_WORKING_HOURS" }] });
    expect(screen.getByRole("alert")).toHaveTextContent(/1 motif refuse la survenance/);
  });

  it("ne signale plus un devis propre qui commence avant le jour, ni les tâches redatées par la greffe (#4133, #4134) [US-3140]", () => {
    shown({ ...GRAFT, own_estimate_past_planning_start_on: "2026-03-02" });
    expect(screen.queryByRole("note")).toBeNull();
    expect(screen.queryByText(/commence le/)).toBeNull();
  });

  it("dit que la survenance crée la révision en cours, quand elle n'en trouve pas [US-3140]", () => {
    shown({ ...ABANDONED, creates_current_revision: true });
    expect(screen.getByRole("note")).toHaveTextContent(/crée d’abord par copie/);
  });
});
