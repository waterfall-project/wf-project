// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
} from "@/test/fixtures";

import type { CostCategory, CostType } from "./cost-grids";
import type { NatureChoice } from "./cost-kinds";
import { CostCategoryList, CostTypeList } from "./cost-lists";

// The server of Next, as far as the lists need it: the fake back, the page rendered again once an
// object is created, the address they read and the navigations they ask.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(),
}));

const TYPES = "POST /reference/cost-types";
const TYPE = "PATCH /reference/cost-types/{cost_type_id}";
const TYPE_ACTIVATION = "PUT /reference/cost-types/{cost_type_id}/activation";
const CATEGORIES = "POST /reference/cost-categories";
const CATEGORY = "PATCH /reference/cost-categories/{cost_category_id}";
const CATEGORY_ACTIVATION = "PUT /reference/cost-categories/{cost_category_id}/activation";

const NO_QUERY = { sort: undefined, search: undefined };
const types = example("cost_types") as { items: CostType[]; meta: ListPage };
const categories = example("volume/cost_categories_page") as {
  items: CostCategory[];
  meta: ListPage;
};
/** The first categories of the volumes: the subcontracting first, under the disbursements. */
const first = (example("volume/cost_categories") as { items: CostCategory[] }).items.slice(0, 3);

/** The natures of the witness, as the page offers them to a category: the labour one deactivated. */
const NATURES: readonly NatureChoice[] = types.items.map((nature) => ({
  id: nature.cost_type_id,
  code: nature.code,
  label: nature.label,
  active: nature.code !== "MO",
}));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [TYPES]: { example: "cost_type_created", status: 201 },
      [TYPE]: "cost_type_updated",
      [TYPE_ACTIVATION]: "cost_type_deactivated",
      [CATEGORIES]: { example: "cost_category_created", status: 201 },
      [CATEGORY]: "cost_category_updated",
      [CATEGORY_ACTIVATION]: "cost_category_deactivated",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The list of the natures of the witness, for a session that may modify the cost settings. */
function natures(rows: readonly CostType[] = types.items, editable = true) {
  return inFrench(
    <CostTypeList
      rows={rows}
      page={types.meta}
      query={NO_QUERY}
      preferences={undefined}
      state={undefined}
      readsInactive
      editable={editable}
      kinds={[]}
    />,
  );
}

/** The list of the categories, for a session that may modify the cost settings. */
function categoryList(rows: readonly CostCategory[] = first) {
  return inFrench(
    <CostCategoryList
      rows={rows}
      page={{ ...categories.meta, offset: 0 }}
      query={NO_QUERY}
      preferences={undefined}
      state={undefined}
      readsInactive
      editable
      natures={NATURES}
      nature={undefined}
    />,
  );
}

/** The calls the lists made of the fake back. */
function writes(client: FakeClient) {
  return client.calls.map(({ route, path, body }) => ({ route, path, body }));
}

/** What the regions of the screen announce, a dialog closed. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The open dialog, by its name. */
function dialog(name: string): HTMLElement {
  return screen.getByRole("dialog", { name });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the creation of a nature or a category", () => {
  it.each([
    ["Main-d’œuvre", "labor"],
    ["Hors main-d’œuvre", "non_labor"],
    ["Provision", "provision"],
  ])(
    "creates a nature of the type %s the form offers, and reads the page anew [WF-REF-0030-A]",
    async (shown, kind) => {
      const client = serve();
      render(natures());
      await userEvent.click(screen.getByRole("button", { name: "Nouvelle nature" }));
      const form = dialog("Nouvelle nature de coût");
      // Une nature de chacun des trois types peut être créée.
      const type = within(form).getByRole("combobox", { name: "Type" });
      expect(
        within(type)
          .getAllByRole("option")
          .map((option) => option.textContent),
      ).toEqual(["Choisir…", "Main-d’œuvre", "Hors main-d’œuvre", "Provision"]);
      expect(within(form).getByRole("textbox", { name: "Code" })).toHaveFocus();
      await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), " FRN ");
      await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
      await userEvent.selectOptions(type, shown);
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      await vi.waitFor(() => {
        expect(refresh).toHaveBeenCalledOnce();
      });
      expect(writes(client)).toEqual([
        {
          route: TYPES,
          path: "/reference/cost-types",
          body: { code: "FRN", label: "Fournitures", kind },
        },
      ]);
      // The dialog closes, and the list says what the server created; it adds no row itself.
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(announced()).toContain("«\u00a0Fournitures\u00a0» créée.");
      expect(screen.getByRole("grid", { name: "Natures de coût" })).not.toHaveTextContent(
        "Fournitures",
      );
    },
  );

  it("refuses at its fields what the form requires before asking anything, a category without a nature among them [WF-REF-0040-A]", async () => {
    const client = serve();
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const form = dialog("Nouvelle catégorie de coût");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const code = within(form).getByRole("textbox", { name: "Code" });
    expect(code).toHaveAttribute("aria-invalid", "true");
    expect(code).toHaveAccessibleDescription("Une valeur est requise.");
    expect(code).toHaveFocus();
    // La création d'une catégorie sans nature est refusée.
    await userEvent.type(code, "FRN-001");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const nature = within(form).getByRole("combobox", { name: "Nature" });
    expect(nature).toHaveAccessibleDescription("Une valeur est requise.");
    expect(nature).toHaveFocus();
    expect(code).not.toHaveAttribute("aria-invalid");
    expect(client.calls).toEqual([]);
  });

  it("offers to attach a category to the active natures alone [WF-REF-0010-A]", async () => {
    serve();
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const nature = within(dialog("Nouvelle catégorie de coût")).getByRole("combobox", {
      name: "Nature",
    });
    // Un objet désactivé n'apparaît plus dans les listes de choix : the labour nature is not offered.
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "DEB · Débours", "PRV · Provision"]);
  });

  it("creates a category under the nature chosen, an empty accounting code sent as none", async () => {
    const client = serve();
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const form = dialog("Nouvelle catégorie de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "FRN-001");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Nature" }),
      "DEB · Débours",
    );
    await userEvent.type(within(form).getByRole("textbox", { name: "Code comptable" }), "  ");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)[0]?.body).toEqual({
      code: "FRN-001",
      label: "Fournitures",
      cost_type_id: "01926f3a-7c00-7000-8000-000000000462",
      accounting_code: null,
    });
    await vi.waitFor(() => {
      expect(announced()).toContain("«\u00a0Petites fournitures\u00a0» créée.");
    });
  });

  it("says the refusal of a nature whose code exists already, the form kept to be corrected [WF-REF-0030-A]", async () => {
    serve({ [TYPES]: { problem: { code: "ALREADY_EXISTS", status: 409 } } });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle nature" }));
    const form = dialog("Nouvelle nature de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "DEB");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Débours");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Type" }),
      "Provision",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    // La création d'une nature dont le code existe déjà est refusée.
    expect(await within(form).findByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
    expect(within(form).getByRole("textbox", { name: "Code" })).toHaveValue("DEB");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the refusal of a category whose accounting code exists already [WF-REF-0040-A]", async () => {
    serve({ [CATEGORIES]: { problem: { code: "ALREADY_EXISTS", status: 409 } } });
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const form = dialog("Nouvelle catégorie de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "FRN-001");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Nature" }),
      "DEB · Débours",
    );
    await userEvent.type(within(form).getByRole("textbox", { name: "Code comptable" }), "604001");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    // La création d'une catégorie dont le code comptable existe déjà est refusée.
    expect(await within(form).findByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
  });

  it("says each refusal by field at its field, the first taking the focus, and under the form what points at none", async () => {
    serve({
      [TYPES]: {
        problem: {
          code: "VALIDATION_FAILED",
          status: 422,
          fields: [
            { pointer: "/label", code: "VALUE_TOO_LONG" },
            { pointer: "/code", code: "VALUE_OUT_OF_RANGE", params: { minimum: 7 } },
            { pointer: "/query/limit", code: "NUMBER_INVALID" },
          ],
        },
      },
    });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle nature" }));
    const form = dialog("Nouvelle nature de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "FRN");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Type" }),
      "Provision",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const code = within(form).getByRole("textbox", { name: "Code" });
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAccessibleDescription(
      "La valeur sort des limites admises. Valeur minimale\u00a0: 7.",
    );
    expect(within(form).getByRole("textbox", { name: "Libellé" })).toHaveAccessibleDescription(
      "La valeur est trop longue.",
    );
    // Under the form, the refusal without the fields said at theirs: no minimum said twice.
    expect(within(form).getByRole("alert")).toHaveTextContent(
      /^Les données saisies ne sont pas valides\.$/,
    );
    expect(code).toHaveAttribute("aria-required", "true");
    await expectAccessible(form);
  });
});

describe("the modification of a nature or a category", () => {
  it("modifies a category from the version read, and its row shows what the server answers", async () => {
    const client = serve();
    render(categoryList());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Sous-traitance\u00a0»");
    expect(within(form).getByRole("textbox", { name: "Code" })).toHaveValue("ACH-001");
    expect(within(form).getByRole("combobox", { name: "Nature" })).toHaveValue(
      "01926f3a-7c00-7000-8000-000000000462",
    );
    expect(within(form).getByRole("textbox", { name: "Code comptable" })).toHaveValue("604001");
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    await userEvent.clear(label);
    await userEvent.type(label, "Sous-traitance générale");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(announced()).toContain("«\u00a0Sous-traitance générale\u00a0» enregistrée.");
    });
    expect(writes(client)).toEqual([
      {
        route: CATEGORY,
        path: "/reference/cost-categories/01926f3a-7c00-7000-8000-000000000401",
        body: {
          code: "ACH-001",
          label: "Sous-traitance générale",
          cost_type_id: "01926f3a-7c00-7000-8000-000000000462",
          accounting_code: "604001",
          lock_version: 1,
        },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(refresh).toHaveBeenCalledOnce();
    const grid = screen.getByRole("grid", { name: "Catégories de coût" });
    expect(grid.querySelector('td[data-row="0"][data-column="label"]')).toHaveTextContent(
      "Sous-traitance générale",
    );
    // Modified again, it is from the version the server answered.
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance générale\u00a0»" }),
    );
    await userEvent.click(
      within(dialog("Modifier «\u00a0Sous-traitance générale\u00a0»")).getByRole("button", {
        name: "Enregistrer",
      }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ lock_version: 2 });
  });

  it("keeps the deactivated nature a category is attached to, among the active ones offered", async () => {
    serve();
    const [labour] = (example("volume/cost_categories_page") as { items: CostCategory[] }).items;
    if (labour === undefined) {
      throw new Error("the page holds a category of labour");
    }
    render(categoryList([labour]));
    await userEvent.click(
      screen.getByRole("button", { name: `Modifier «\u00a0${labour.label}\u00a0»` }),
    );
    const nature = within(dialog(`Modifier «\u00a0${labour.label}\u00a0»`)).getByRole("combobox", {
      name: "Nature",
    });
    expect(nature).toHaveValue(labour.cost_type_id);
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "DEB · Débours", "PRV · Provision", "MO · Main-d'œuvre (désactivée)"]);
  });

  it("says the refusal of the type of a nature whose category is employed [WF-REF-0030-A]", async () => {
    const client = serve({ [TYPE]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    render(natures());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Main-d'œuvre\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Main-d'œuvre\u00a0»");
    // The rule is said before the type is changed.
    expect(form).toHaveAccessibleDescription(
      "Le code, unique, le libellé et le type sont requis. Le type ne change plus dès qu’une catégorie rattachée est employée.",
    );
    const type = within(form).getByRole("combobox", { name: "Type" });
    expect(type).toHaveValue("labor");
    await userEvent.selectOptions(type, "Hors main-d’œuvre");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    // La modification du type est refusée pour une nature dont une catégorie est employée.
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération.",
    );
    expect(client.calls[0]?.body).toEqual({
      code: "MO",
      label: "Main-d'œuvre",
      kind: "non_labor",
      lock_version: 1,
    });
    // The row stays as the page read it.
    expect(screen.getByRole("grid", { name: "Natures de coût", hidden: true })).toHaveTextContent(
      "Main-d’œuvre",
    );
  });

  it("says the version stale, and reading the page anew closes the form", async () => {
    serve({
      [TYPE]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 2 } },
      },
    });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Débours\u00a0»" }));
    const form = dialog("Modifier «\u00a0Débours\u00a0»");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes the form on Cancel, asking nothing, and offers no command to a session that may only read", async () => {
    const client = serve();
    const { rerender } = render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Débours\u00a0»" }));
    await userEvent.click(
      within(dialog("Modifier «\u00a0Débours\u00a0»")).getByRole("button", { name: "Annuler" }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
    const read = example("cost_types_reader") as { items: CostType[] };
    rerender(natures(read.items, false));
    expect(screen.queryByRole("button", { name: /^(Nouvelle|Modifier|Désactiver)/ })).toBeNull();
  });
});

describe("a write whose dialog is closed, and the focus", () => {
  /** A promise the test settles, which holds the answer of the server until then. */
  function held() {
    const settles: (() => void)[] = [];
    const until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    return {
      until,
      release: () => {
        for (const settle of settles) {
          settle();
        }
      },
    };
  }

  it("says the write under way on its button, and once the dialog is closed says what the server did in the list", async () => {
    const answer = held();
    serve({}, { hold: () => answer.until });
    render(categoryList());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Sous-traitance\u00a0»");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const sending = within(form).getByRole("button", { name: "Envoi…" });
    expect(sending).toHaveAttribute("aria-busy", "true");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    answer.release();
    await vi.waitFor(() => {
      expect(announced()).toContain("«\u00a0Sous-traitance générale\u00a0» enregistrée.");
    });
    expect(
      screen
        .getByRole("grid", { name: "Catégories de coût" })
        .querySelector('td[data-row="0"][data-column="label"]'),
    ).toHaveTextContent("Sous-traitance générale");
  });

  it("tells above the list a refusal answered once the dialog is closed", async () => {
    const answer = held();
    serve(
      { [CATEGORY]: { problem: { code: "PERMISSION_MISSING", status: 403 } } },
      { hold: () => answer.until },
    );
    render(categoryList());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    await userEvent.click(
      within(dialog("Modifier «\u00a0Sous-traitance\u00a0»")).getByRole("button", {
        name: "Enregistrer",
      }),
    );
    await userEvent.keyboard("{Escape}");
    answer.release();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("tells a refusal answered once the dialog is closed beside another refusal of the list, neither in the place of the other", async () => {
    const answer = held();
    serve(
      {
        [TYPE]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } },
        [TYPE_ACTIVATION]: { problem: { code: "PERMISSION_MISSING", status: 403 } },
      },
      { hold: (route) => (route === TYPE ? answer.until : undefined) },
    );
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Débours\u00a0»" }));
    await userEvent.click(
      within(dialog("Modifier «\u00a0Débours\u00a0»")).getByRole("button", { name: "Enregistrer" }),
    );
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    answer.release();
    await vi.waitFor(() => {
      expect(screen.getAllByRole("alert")).toHaveLength(2);
    });
    const [refused, late] = screen.getAllByRole("alert");
    if (refused === undefined || late === undefined) {
      throw new Error("two refusals are told");
    }
    expect(refused).toHaveTextContent("Vous n’avez pas la permission nécessaire.");
    expect(late).toHaveTextContent("L’état actuel ne permet pas cette opération.");
    // Each is dismissed on its own.
    await userEvent.click(within(refused).getByRole("button", { name: "Fermer l’avis" }));
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });

  it("tells the refusal of the same command on the same row once, the last in place of the one before, each dismissal described by its refusal", async () => {
    serve({
      [TYPE_ACTIVATION]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 2 } },
      },
    });
    render(natures());
    const deactivate = screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" });
    await userEvent.click(deactivate);
    expect(await screen.findByRole("alert")).toHaveTextContent("Quelqu’un a modifié");
    await userEvent.click(deactivate);
    await vi.waitFor(() => {
      expect(screen.getAllByRole("alert")).toHaveLength(1);
    });
    expect(screen.getByRole("button", { name: "Fermer l’avis" })).toHaveAccessibleDescription(
      "Quelqu’un a modifié cette donnée entre-temps\u202f; rechargez-la pour voir sa dernière version.",
    );
  });

  it("keeps in a row the first of two answers at one version, whatever the order they are answered in", async () => {
    const modification = held();
    const activation = held();
    serve(
      {},
      {
        hold: (route) =>
          route === TYPE
            ? modification.until
            : route === TYPE_ACTIVATION
              ? activation.until
              : undefined,
      },
    );
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Débours\u00a0»" }));
    await userEvent.click(
      within(dialog("Modifier «\u00a0Débours\u00a0»")).getByRole("button", { name: "Enregistrer" }),
    );
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }));
    // The deactivation answered first, at the version 2: the row shows it.
    activation.release();
    const row = () =>
      screen.getByRole("grid", { name: "Natures de coût" }).querySelector("tbody tr");
    await vi.waitFor(() => {
      expect(row()).toHaveTextContent("Désactivé");
    });
    // The modification answered after, at the same version 2: the row keeps the answer it shows.
    modification.release();
    await vi.waitFor(() => {
      expect(announced()).toContain("«\u00a0Débours et achats\u00a0» enregistrée.");
    });
    expect(row()).toHaveTextContent("Désactivé");
    expect(row()).not.toHaveTextContent("Débours et achats");
  });

  it("gives the focus back to the list once its dialog is closed, the page read anew no longer holding the row", async () => {
    const answer = held();
    serve({}, { hold: () => answer.until });
    const { rerender } = render(categoryList());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    await userEvent.click(
      within(dialog("Modifier «\u00a0Sous-traitance\u00a0»")).getByRole("button", {
        name: "Enregistrer",
      }),
    );
    // A reading that no longer retains the subcontracting arrives meanwhile.
    rerender(categoryList(first.slice(1)));
    answer.release();
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    const grid = screen.getByRole("grid", { name: "Catégories de coût" });
    expect(grid.contains(document.activeElement)).toBe(true);
  });

  it("gives the focus back to the command of the creation once its dialog is closed by Escape", async () => {
    serve();
    render(natures());
    const create = screen.getByRole("button", { name: "Nouvelle nature" });
    await userEvent.click(create);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(create).toHaveFocus();
  });

  it.each(["Annuler", "Enregistrer"])(
    "gives the focus back to the cell of the row once its dialog is closed by %s, the grid one stop",
    async (button) => {
      serve();
      render(natures());
      await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Débours\u00a0»" }));
      await userEvent.click(
        within(dialog("Modifier «\u00a0Débours\u00a0»")).getByRole("button", { name: button }),
      );
      await vi.waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
      expect(document.querySelector('td[data-row="0"][data-column="modify"]')).toHaveFocus();
    },
  );
});

describe("the activation of a nature or a category", () => {
  it("deactivates a nature from the version read, its row then as the server answers it, deactivated and offering its reactivation", async () => {
    const client = serve();
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }));
    expect(
      await screen.findByRole("button", { name: "Réactiver «\u00a0Débours\u00a0»" }),
    ).toBeInTheDocument();
    expect(writes(client)).toEqual([
      {
        route: TYPE_ACTIVATION,
        path: "/reference/cost-types/01926f3a-7c00-7000-8000-000000000462/activation",
        body: { is_active: false, lock_version: 1 },
      },
    ]);
    const grid = screen.getByRole("grid", { name: "Natures de coût" });
    expect(grid.querySelector('td[data-row="0"][data-column="state"]')).toHaveTextContent(
      "Désactivé",
    );
    expect(announced()).toContain("«\u00a0Débours\u00a0» désactivée.");
    // The page is read anew: the natures are what the categories are attached to (WF-REF-0010).
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("keeps the answer of the server in its row until a reading catches up with its version", async () => {
    serve();
    const [disbursements, ...others] = types.items;
    if (disbursements === undefined) {
      throw new Error("the witness has natures");
    }
    const { rerender } = render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }));
    const state = () => document.querySelector('td[data-row="0"][data-column="state"]');
    await vi.waitFor(() => {
      expect(state()).toHaveTextContent("Désactivé");
    });
    // A reading of the version read before the answer (1, the fake back): the answer (2) stays.
    rerender(natures([{ ...disbursements }, ...others]));
    expect(state()).toHaveTextContent("Désactivé");
    // A reading newer than the answer (3): the reading prevails.
    rerender(natures([{ ...disbursements, label: "Débours relus", lock_version: 3 }, ...others]));
    expect(state()).not.toHaveTextContent("Désactivé");
    expect(document.querySelector('td[data-row="0"][data-column="label"]')).toHaveTextContent(
      "Débours relus",
    );
  });

  it("reactivates a deactivated category by its own activation, from the version read", async () => {
    const client = serve();
    const [category] = first;
    if (category === undefined) {
      throw new Error("the volumes hold a category");
    }
    const deactivated = {
      ...category,
      is_active: false,
      available_commands: [
        { command: "reactivate" as const, is_available: true, missing_conditions: [] },
      ],
    };
    render(categoryList([deactivated]));
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Sous-traitance\u00a0»" }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(writes(client)[0]).toEqual({
      route: CATEGORY_ACTIVATION,
      path: "/reference/cost-categories/01926f3a-7c00-7000-8000-000000000401/activation",
      body: { is_active: true, lock_version: 1 },
    });
  });

  it("says the refusal of a deactivation above the list, the row as the page read it", async () => {
    serve({ [TYPE_ACTIVATION]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    expect(
      screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }),
    ).toBeInTheDocument();
  });

  // The contract lists the activation of a nature or a category always available: the branch is the
  // one every object of the reference data shares, proven on a nature that would list it otherwise.
  it("presents an activation listed unavailable with its conditions, and a press says them without asking anything", async () => {
    const client = serve();
    const [disbursements, ...others] = types.items;
    if (disbursements === undefined) {
      throw new Error("the witness has natures");
    }
    const held = {
      ...disbursements,
      available_commands: [
        {
          command: "deactivate" as const,
          is_available: false,
          missing_conditions: ["calendar_not_default" as const],
        },
      ],
    };
    render(natures([held, ...others]));
    const command = screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(
      within(screen.getByRole("region", { name: "Natures de coût" }))
        .getAllByRole("status")
        .map((status) => status.textContent),
    ).toContain(
      "La désactivation de «\u00a0Débours\u00a0» est indisponible. Condition non remplie\u00a0: calendrier autre que celui par défaut.",
    );
    expect(client.calls).toEqual([]);
  });

  it("presses the deactivation from the keyboard, Enter on the cell of the state, the grid one stop", async () => {
    const client = serve();
    render(natures());
    const cell = document.querySelector<HTMLElement>('td[data-row="0"][data-column="state"]');
    expect(
      screen.getByRole("button", { name: "Désactiver «\u00a0Débours\u00a0»" }),
    ).toHaveAttribute("tabindex", "-1");
    cell?.focus();
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
  });
});
