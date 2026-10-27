// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";

import { ActualCostMapping } from "./actual-cost-mapping";

type Mapping = components["schemas"]["ActualCostMapping"];

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/costs/actual-cost-mapping",
  useSearchParams: () => new URLSearchParams(),
}));

const SET = "PUT /reference/actual-cost-mapping";
const witness = example("actual_cost_mapping") as Mapping;
const empty = example("actual_cost_mapping_empty") as Mapping;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers) {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The correspondence in French, editable or read only. */
function shown(mapping: Mapping, writes: boolean) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ActualCostMapping mapping={mapping} writes={writes} />
    </NextIntlClientProvider>,
  );
}

afterEach(() => {
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the correspondence of the extraction of the actual costs, read", () => {
  it("lists the labels of each column read and the kept columns, with no command, to a session that only reads [WF-REF-0190-A]", async () => {
    const { container } = shown(witness, false);
    const wbs = screen.getByRole("region", { name: "Élément d’OTP" });
    expect(within(wbs).getByText("Elément d'OTP")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Poste de la pièce" })).getByText(
        "Aucun intitulé.",
      ),
    ).toBeInTheDocument();
    const kept = screen.getByRole("region", { name: "Colonnes conservées" });
    expect(
      within(kept)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Fournisseur", "Texte de commande"]);
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("La correspondance est complète");
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    await expectAccessible(container);
  });

  it("names, on an empty correspondence, the four columns required that have no label, the post left out, as the server computes them [WF-REF-0190-A]", () => {
    shown(empty, false);
    expect(screen.getByText(/Colonnes exigées sans intitulé/)).toHaveTextContent(
      "Colonnes exigées sans intitulé : Élément d’OTP, N° de pièce, Date de pièce, Montant. L’import des coûts réels est refusé",
    );
    expect(screen.getByText("Aucune colonne conservée.")).toBeInTheDocument();
  });
});

describe("the correspondence of the extraction of the actual costs, written", () => {
  it("adds a label and a kept column, sends the correspondence whole with the version read, and takes the answer [WF-REF-0190-A]", async () => {
    const client = serve({ [SET]: "actual_cost_mapping_updated" });
    shown(witness, true);
    await userEvent.click(
      screen.getByRole("button", { name: "Ajouter un intitulé à « Poste de la pièce »" }),
    );
    const post = screen.getByRole("textbox", { name: "Intitulé 1 de « Poste de la pièce »" });
    expect(post).toHaveFocus();
    await userEvent.type(post, "  Poste  ");
    await userEvent.click(screen.getByRole("button", { name: "Déclarer une colonne conservée" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" }),
      "Document d'achat",
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await vi.waitFor(() => {
      expect(screen.getByText("Correspondance enregistrée.")).toBeInTheDocument();
    });
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      {
        route: SET,
        body: {
          columns: [
            { column: "wbs_element", labels: ["Elément d'OTP"] },
            { column: "document_number", labels: ["Nº pièce référence"] },
            { column: "document_item", labels: ["Poste"] },
            { column: "document_date", labels: ["Date de la pièce"] },
            { column: "amount", labels: ["Val./Devise objet"] },
          ],
          kept_columns: ["Fournisseur", "Texte de commande", "Document d'achat"],
          lock_version: 2,
        },
      },
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("modifies and removes a label, the focus going to the command that adds one [WF-REF-0190-A]", async () => {
    const client = serve({ [SET]: "actual_cost_mapping_updated" });
    shown(witness, true);
    const date = screen.getByRole("textbox", { name: "Intitulé 1 de « Date de pièce »" });
    await userEvent.clear(date);
    await userEvent.type(date, "Date comptable");
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer l’intitulé 1 de « Montant »" }),
    );
    expect(screen.getByRole("button", { name: "Ajouter un intitulé à « Montant »" })).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Retirer la colonne conservée 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual({
      columns: [
        { column: "wbs_element", labels: ["Elément d'OTP"] },
        { column: "document_number", labels: ["Nº pièce référence"] },
        { column: "document_item", labels: [] },
        { column: "document_date", labels: ["Date comptable"] },
        { column: "amount", labels: [] },
      ],
      kept_columns: ["Texte de commande"],
      lock_version: 2,
    });
  });

  it("says at the label a duplicate refused, naming the label it doubles, and writes nothing [WF-REF-0190-A]", async () => {
    serve({
      [SET]: { problem: example("actual_cost_mapping_duplicate") as Problem & { status: 422 } },
    });
    shown(witness, true);
    await userEvent.click(screen.getByRole("button", { name: "Déclarer une colonne conservée" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" }),
      "Élément d'OTP",
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    const duplicate = screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" });
    await vi.waitFor(() => {
      expect(duplicate).toHaveFocus();
    });
    expect(duplicate).toHaveAttribute("aria-invalid", "true");
    expect(duplicate).toHaveAccessibleDescription(
      `${CATALOGUES.fr.errors.DUPLICATE_COLUMN_LABEL} Il double l’intitulé « Elément d'OTP » de la colonne « Élément d’OTP ».`,
    );
    expect(screen.queryByRole("alert")).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
    expect(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 2" }),
    ).not.toHaveAttribute("aria-invalid");
  });

  it("tells the version stale under the form, and offers to read the page anew [WF-IHM-0110]", async () => {
    serve({
      [SET]: { problem: example("actual_cost_mapping_stale") as Problem & { status: 412 } },
    });
    shown(witness, true);
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await userEvent.click(await screen.findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("starts an empty correspondence with no label and the bar of the four columns required [WF-REF-0190-A]", async () => {
    const { container } = shown(empty, true);
    expect(screen.queryAllByRole("textbox")).toEqual([]);
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Colonnes exigées sans intitulé");
    await expectAccessible(container);
  });
});
