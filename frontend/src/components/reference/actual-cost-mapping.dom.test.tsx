// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import {
  example,
  type FakeAnswers,
  fakeClient,
  type FakeTiming,
  held,
  type Problem,
} from "@/test/fixtures";

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
function serve(answers: FakeAnswers, timing?: FakeTiming) {
  const client = fakeClient(answers, timing);
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

  it("tells the version stale under the form, and offers to read the page anew [WF-IHM-0110, WF-REF-0190-A]", async () => {
    serve({
      [SET]: { problem: example("actual_cost_mapping_stale") as Problem & { status: 412 } },
    });
    shown(witness, true);
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await userEvent.click(await screen.findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("takes the bar of the columns required from the answer of the write [WF-REF-0190-A]", async () => {
    serve({ [SET]: "actual_cost_mapping_updated" });
    shown(empty, true);
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Colonnes exigées sans intitulé");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await vi.waitFor(() => {
      expect(screen.getAllByRole("status")[0]).toHaveTextContent("La correspondance est complète");
    });
  });

  it("holds the fields and the commands while the write is under way, and sends it once [WF-REF-0190-A]", async () => {
    const answer = held();
    const client = serve({ [SET]: "actual_cost_mapping_updated" }, answer.timing);
    shown(witness, true);
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    const sending = screen.getByRole("button", { name: "Enregistrement…" });
    expect(sending).toBeDisabled();
    expect(sending).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("form", { name: "Correspondance de l’extraction des coûts réels" }),
    ).toHaveAttribute("aria-busy", "true");
    for (const field of screen.getAllByRole("textbox")) {
      expect(field).toBeDisabled();
    }
    expect(screen.getByRole("button", { name: "Déclarer une colonne conservée" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Retirer la colonne conservée 1" })).toBeDisabled();
    fireEvent.submit(
      screen.getByRole("form", { name: "Correspondance de l’extraction des coûts réels" }),
    );
    answer.release();
    await vi.waitFor(() => {
      expect(screen.getByText("Correspondance enregistrée.")).toBeInTheDocument();
    });
    expect(client.calls).toHaveLength(1);
  });

  it("is no longer busy in the commit that shows the refusal, nor in the one that says the correspondence saved [WF-REF-0190-A]", async () => {
    serve({
      [SET]: [
        { problem: example("actual_cost_mapping_duplicate") as Problem & { status: 422 } },
        "actual_cost_mapping_updated",
      ],
    });
    const { container } = shown(witness, true);
    const form = screen.getByRole("form", {
      name: "Correspondance de l’extraction des coûts réels",
    });
    await userEvent.click(screen.getByRole("button", { name: "Déclarer une colonne conservée" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" }),
      "Élément d'OTP",
    );
    const refusal = atCommit(
      document.body,
      () => document.querySelector("[aria-invalid]") !== null,
      () => form.getAttribute("aria-busy"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await vi.waitFor(() => {
      expect(document.querySelector("[aria-invalid]")).not.toBeNull();
    });
    expect(refusal.stop()).toEqual(["false"]);
    const saved = atCommit(
      document.body,
      () => screen.queryByText("Correspondance enregistrée.") !== null,
      () => container.querySelector("form")?.getAttribute("aria-busy") ?? null,
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    await vi.waitFor(() => {
      expect(screen.getByText("Correspondance enregistrée.")).toBeInTheDocument();
    });
    expect(saved.stop()).toEqual(["false"]);
  });

  it("keeps the refusal at its label when a label before it is removed, and drops it once the label is typed again [WF-REF-0190-A]", async () => {
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
    await vi.waitFor(() => {
      expect(
        screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" }),
      ).toHaveAttribute("aria-invalid", "true");
    });
    await userEvent.click(screen.getByRole("button", { name: "Retirer la colonne conservée 1" }));
    const refused = screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 2" });
    expect(refused).toHaveValue("Élément d'OTP");
    expect(refused).toHaveAttribute("aria-invalid", "true");
    expect(refused).toHaveAccessibleDescription(/Il double/);
    expect(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 1" }),
    ).not.toHaveAttribute("aria-invalid");
    await userEvent.type(refused, "s");
    expect(refused).not.toHaveAttribute("aria-invalid");
    expect(refused).not.toHaveAttribute("aria-describedby");
    expect(screen.queryByText(/Il double/)).toBeNull();
  });

  it("starts an empty correspondence with no label and the bar of the four columns required [WF-REF-0190-A]", async () => {
    const { container } = shown(empty, true);
    expect(screen.queryAllByRole("textbox")).toEqual([]);
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Colonnes exigées sans intitulé");
    await expectAccessible(container);
  });

  it("gives the focus back to the control that held it after a write saved, and after a version stale (#1515) [WF-REF-0190-A]", async () => {
    serve({
      [SET]: [
        "actual_cost_mapping_updated",
        { problem: example("actual_cost_mapping_stale") as Problem & { status: 412 } },
      ],
    });
    shown(witness, true);
    const field = screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 1" });
    await userEvent.click(field);
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(screen.getByText("Correspondance enregistrée.")).toBeInTheDocument();
    });
    await vi.waitFor(() => {
      expect(
        screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 1" }),
      ).toHaveFocus();
    });
    const save = screen.getByRole("button", { name: "Enregistrer la correspondance" });
    await userEvent.click(save);
    await screen.findByRole("button", { name: "Recharger" });
    expect(save).toHaveFocus();
  });

  it("gives the focus to the command that saves when the control that held it is not one the form finds again (#1515) [WF-REF-0190-A]", async () => {
    serve({ [SET]: "actual_cost_mapping_updated" });
    shown(witness, true);
    const remove = screen.getByRole("button", { name: "Retirer la colonne conservée 1" });
    remove.focus();
    expect(remove).toHaveFocus();
    fireEvent.submit(
      screen.getByRole("form", { name: "Correspondance de l’extraction des coûts réels" }),
    );
    await vi.waitFor(() => {
      expect(screen.getByText("Correspondance enregistrée.")).toBeInTheDocument();
    });
    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: "Enregistrer la correspondance" })).toHaveFocus();
    });
  });

  it("leaves the second refusal of a label in the notice under the form, the first being said at the label (#1516) [WF-REF-0190-A]", async () => {
    const duplicate = example("actual_cost_mapping_duplicate") as Problem & { status: 422 };
    const [first] = duplicate.fields ?? [];
    serve({
      [SET]: {
        problem: {
          ...duplicate,
          fields: [first, { ...first, code: "VALIDATION_FAILED", params: {} }],
        } as Problem & { status: 422 },
      },
    });
    shown(witness, true);
    await userEvent.click(screen.getByRole("button", { name: "Déclarer une colonne conservée" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Intitulé de la colonne conservée 3" }),
      "Élément d'OTP",
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la correspondance" }));
    const label = await screen.findByRole("textbox", {
      name: "Intitulé de la colonne conservée 3",
    });
    await vi.waitFor(() => {
      expect(label).toHaveAttribute("aria-invalid", "true");
    });
    expect(label).toHaveAccessibleDescription(/Il double/);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
