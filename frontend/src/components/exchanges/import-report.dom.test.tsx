// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { ImportList } from "./import-list";
import { ImportReport } from "./import-report";

// The server of Next, as far as the report needs it: the fake back behind serverClient, which the
// report asks nothing of while it is only read.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

type Import = components["schemas"]["ImportDetail"];
type Listed = components["schemas"]["Import"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;

/** Render the report of an import of the contract, as the screen shows it, in French. */
function open(entry: Import, locale: "fr" | "en" = "fr") {
  server.client = fakeClient({});
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <ImportReport projectId={PROJECT} entry={entry} start={START} />
    </NextIntlClientProvider>,
  );
}

describe("the report of an import, what the file dates otherwise", () => {
  it("names each task the file dates otherwise than Waterfall computes it, with the columns that differ, as information and not a reason to confirm", () => {
    open(example("import_planning_mismatch") as Import);
    const table = screen.getByRole("table", { name: "Tâches datées autrement par le fichier" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["TâcheChamps", "ÉtudesFin", "Revue de conceptionFin"]);
    expect(screen.getByText(/^2 tâches datées autrement par le fichier/)).toBeVisible();
  });

  it("names no such task for a file Waterfall dates alike, an estimate", () => {
    open(example("import_analysed") as Import);
    expect(
      screen.queryByRole("table", { name: "Tâches datées autrement par le fichier" }),
    ).toBeNull();
  });
});

describe("the report of an import, the unit constants of the file", () => {
  it("signals the constants of an MS Project file that differ from those of the installation, the file's and the installation's [WF-PLA-0160-A]", () => {
    open(example("import_planning_other_constants") as Import);
    expect(
      screen.getByText(
        "Le fichier compte 7 heures par jour, 35 par semaine et 20 jours par mois, l’installation 8, 40 et 20 : les durées et les décalages gardent leurs heures, lues aux constantes de l’installation.",
      ),
    ).toBeVisible();
    expect(screen.queryByText("Confirmation explicite demandée")).toBeNull();
  });

  it("signals them in English [WF-PLA-0160-A]", () => {
    open(example("import_planning_other_constants") as Import, "en");
    expect(
      screen.getByText(
        "The file counts 7 hours a day, 35 a week and 20 days a month, the installation 8, 40 and 20: the durations and the lags keep their hours, read at the constants of the installation.",
      ),
    ).toBeVisible();
  });

  it.each(["import_planning_mismatch", "import_analysed"] as const)(
    "signals nothing when the report bears no constants, %s",
    (name) => {
      open(example(name) as Import);
      expect(screen.queryByText(/^Le fichier compte/)).toBeNull();
    },
  );
});

describe("the report of an import, a line that puts a task under a milestone", () => {
  it("is rejected with the sentence of the catalogue, by its place in the file [WF-PLA-0050-A]", () => {
    const analysed = example("import_analysed") as Import & {
      report: NonNullable<Import["report"]>;
    };
    const [line] = analysed.report.rejected;
    expect(line).toBeDefined();
    open({
      ...analysed,
      report: {
        ...analysed.report,
        rejected:
          line === undefined ? [] : [{ ...line, code: "MILESTONE_HAS_NO_SUBTASK", params: {} }],
      },
    });
    const table = screen.getByRole("table", { name: /Lignes rejetées/i });
    expect(within(table).getByText("Un jalon ne porte pas de sous-tâches.")).toBeVisible();
  });
});

/** An import applied, read whole: both commands it lists are unavailable, each with its condition. */
function applied(): Import {
  const { items } = example("imports") as { items: Listed[] };
  const listed = items.find((entry) => entry.status === "applied");
  if (listed === undefined) {
    throw new Error("the example of the imports holds one applied");
  }
  return {
    ...listed,
    report: null,
    task: (example("import_analysed") as Import).task,
    available_commands: [
      { command: "apply", is_available: false, missing_conditions: ["import_awaiting_decision"] },
      { command: "abandon", is_available: false, missing_conditions: ["import_not_applied"] },
    ],
  };
}

/** The journal of the imports, in a language. */
function openList(entries: Listed[], locale: "fr" | "en" = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <ImportList imports={entries} total={entries.length} current={undefined} start={START} />
    </NextIntlClientProvider>,
  );
}

describe("the report of an import, its commands and its refusal", () => {
  it("presents application and abandonment of an import applied as the import lists them, unavailable with their condition [WF-IHM-0090-A]", async () => {
    open(applied());
    const apply = screen.getByRole("button", { name: "Appliquer l’import" });
    const abandon = screen.getByRole("button", { name: "Abandonner l’import" });
    expect(apply).toHaveAttribute("aria-disabled", "true");
    expect(apply).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: import en attente de décision.",
    );
    expect(abandon).toHaveAttribute("aria-disabled", "true");
    expect(abandon).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: import non appliqué.",
    );
    await userEvent.click(apply);
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.getByText("Cet import n’a pas de compte rendu.")).toBeVisible();
  });

  it("reads the commands from the import and not from its status: an analysed import that lists no command offers none [WF-IHM-0090-A]", () => {
    open({ ...(example("import_analysed") as Import), available_commands: [] });
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("offers the abandonment of an import whose application was refused, by what the import lists, with the explanation of the refusal [WF-IHM-0090-A]", () => {
    open({
      ...(example("import_apply_refused_permission") as Import),
      available_commands: [
        { command: "apply", is_available: false, missing_conditions: ["import_awaiting_decision"] },
        { command: "abandon", is_available: true, missing_conditions: [] },
      ],
    });
    expect(screen.getByText("Refusé")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent(
      "Refusé à l’application, le fichier est supprimé : relancez l’import pour le reprendre.",
    );
    expect(screen.getByRole("button", { name: "Appliquer l’import" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: "Abandonner l’import" })).not.toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("says the label and the explanation of the refused status in English, on the report [WF-IHM-0090-A]", () => {
    open(example("import_apply_refused_permission") as Import, "en");
    expect(screen.getByText("Refused")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent(
      "Refused at the application, the file is deleted: restart the import to take it up again.",
    );
  });

  it("says the explanation of the refused status in the journal of the imports, in both languages [WF-IHM-0090-A]", () => {
    const refused = example("import_apply_refused_permission") as Import;
    const { unmount } = openList([refused]);
    expect(screen.getByText("Refusé")).toBeVisible();
    expect(screen.getByText(/^Refusé à l’application, le fichier est supprimé/)).toBeVisible();
    unmount();
    openList([refused], "en");
    expect(screen.getByText("Refused")).toBeVisible();
    expect(screen.getByText(/^Refused at the application, the file is deleted/)).toBeVisible();
  });
});
