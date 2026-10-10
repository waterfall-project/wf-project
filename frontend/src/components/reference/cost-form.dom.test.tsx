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
import type { Locale } from "@/i18n/locale";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";

import type { CostCategory, CostType } from "./cost-grids";
import { type NatureChoice, natureChoice } from "./cost-kinds";
import { CostCategoryList, CostTypeList } from "./cost-lists";

// The form of a nature and of a category (EP-02/L42g): what a modification may change, as the
// commands of the object say it, and the refusals of the server said at their fields, each
// answered by an example of the contract. The rest of the commands of the lists is proven by
// `cost-commands.dom.test.tsx`.
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
const CATEGORIES = "POST /reference/cost-categories";
const CATEGORY = "PATCH /reference/cost-categories/{cost_category_id}";

const NO_QUERY = { sort: undefined, search: undefined };
const types = example("cost_types") as { items: CostType[]; meta: ListPage };
const volumes = (example("volume/cost_categories") as { items: CostCategory[] }).items;
/** The first categories of the volumes: the subcontracting first, under the disbursements. */
const first = volumes.slice(0, 3);
/** The one category of provision for risks, as the volumes give it. */
const provision = volumes.find((category) => category.code === "PRV-001");
/** A category the server created today under the disbursements, attached to no line nor rate. */
const created = example("cost_category_created") as CostCategory;

/** The natures of the witness, as the page offers them to a category, every one active. */
const ACTIVE: readonly NatureChoice[] = types.items.map(natureChoice);

/** A refusal of the contract, by the name of its example and its status. */
function refusal<S extends number>(name: string, status: S): Problem & { status: S } {
  return { ...(example(name) as Problem), status };
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}) {
  const client = fakeClient({
    [TYPES]: { example: "cost_type_created", status: 201 },
    [TYPE]: "cost_type_updated",
    [CATEGORIES]: { example: "cost_category_created", status: 201 },
    [CATEGORY]: "cost_category_updated",
    ...answers,
  });
  server.client = client;
  return client;
}

/** A part of the screen, in French unless told, sharing the address last asked as the page does. */
function inFrench(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The list of the natures, for a session that may modify the cost settings. */
function natures(rows: readonly CostType[] = types.items) {
  return inFrench(
    <CostTypeList
      rows={rows}
      page={types.meta}
      query={NO_QUERY}
      preferences={undefined}
      state={undefined}
      readsInactive
      editable
      kinds={[]}
    />,
  );
}

/** The list of the categories, for a session that may modify the cost settings. */
function categoryList(
  rows: readonly CostCategory[] = first,
  offered: readonly NatureChoice[] = ACTIVE,
  every?: readonly NatureChoice[],
  locale: Locale = "fr",
) {
  return inFrench(
    <CostCategoryList
      rows={rows}
      page={{ limit: 50, offset: 0, total: rows.length }}
      query={NO_QUERY}
      preferences={undefined}
      state={undefined}
      readsInactive
      editable
      natures={offered}
      every={every}
      nature={undefined}
    />,
    locale,
  );
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
});

describe("the refusals by field of the server", () => {
  it("says at its field the refusal of a nature whose code exists already, naming the nature that holds it, the form kept to be corrected [WF-REF-0030-A]", async () => {
    serve({ [TYPES]: { problem: refusal("cost_type_code_taken", 409) } });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle nature" }));
    const form = dialog("Nouvelle nature de coût");
    const code = within(form).getByRole("textbox", { name: "Code" });
    await userEvent.type(code, "DEB");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Type" }),
      "Hors main-d’œuvre",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    // La création d'une nature dont le code existe déjà est refusée.
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAttribute("aria-invalid", "true");
    expect(code).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par «\u00a0DEB · Débours\u00a0».",
    );
    expect(code).toHaveValue("DEB");
    // Said at its field, the refusal is not told again under the form.
    expect(within(form).queryByRole("alert")).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says at each field the code and the accounting code of a category that exist already, each naming the category that holds it [WF-REF-0040-A]", async () => {
    serve({ [CATEGORIES]: { problem: refusal("cost_category_codes_taken", 409) } });
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const form = dialog("Nouvelle catégorie de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "ACH-002");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Câbles armés");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Nature" }),
      "DEB · Débours",
    );
    await userEvent.type(within(form).getByRole("textbox", { name: "Code comptable" }), "604001");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    // La création d'une catégorie dont le code comptable existe déjà est refusée.
    const code = within(form).getByRole("textbox", { name: "Code" });
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par «\u00a0ACH-002 · Matériel électrique\u00a0».",
    );
    expect(
      within(form).getByRole("textbox", { name: "Code comptable" }),
    ).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par «\u00a0ACH-001 · Sous-traitance\u00a0».",
    );
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("says generically the category that holds an accounting code taken when the list does not show it", async () => {
    serve({ [CATEGORY]: { problem: refusal("cost_category_accounting_code_taken", 409) } });
    const [subcontracting] = first;
    if (subcontracting === undefined) {
      throw new Error("the volumes hold the subcontracting");
    }
    render(categoryList([subcontracting]));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Sous-traitance\u00a0»");
    const accounting = within(form).getByRole("textbox", { name: "Code comptable" });
    await userEvent.clear(accounting);
    await userEvent.type(accounting, "604002");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(accounting).toHaveFocus();
    });
    expect(accounting).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par une autre catégorie.",
    );
  });

  it("says at their fields a nature the reference data does not have, an inactive one, and an accounting code the server requires", async () => {
    serve({
      [CATEGORIES]: [
        { problem: refusal("cost_category_creation_refused", 422) },
        {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields: [{ pointer: "/cost_type_id", code: "INACTIVE_REFERENCE_OBJECT" }],
          },
        },
      ],
    });
    render(categoryList());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle catégorie" }));
    const form = dialog("Nouvelle catégorie de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "FRN-001");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    const nature = within(form).getByRole("combobox", { name: "Nature" });
    await userEvent.selectOptions(nature, "PRV · Provision");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code comptable" }), "606001");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(nature).toHaveFocus();
    });
    expect(nature).toHaveAccessibleDescription("Nature de coût inconnue.");
    expect(
      within(form).getByRole("textbox", { name: "Code comptable" }),
    ).toHaveAccessibleDescription("Une valeur est requise.");
    // The fields are refused before the write is over: the button says it until then, and a press
    // meanwhile sends nothing.
    await userEvent.click(await within(form).findByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(nature).toHaveAccessibleDescription("Cet élément du référentiel est désactivé.");
    });
  });

  it("says at their fields a code too long and a name required, as the server judges them", async () => {
    serve({ [TYPES]: { problem: refusal("cost_type_creation_refused", 422) } });
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle nature" }));
    const form = dialog("Nouvelle nature de coût");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "FRN");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Fournitures");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Type" }),
      "Hors main-d’œuvre",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const code = within(form).getByRole("textbox", { name: "Code" });
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAccessibleDescription("La valeur est trop longue.");
    expect(within(form).getByRole("textbox", { name: "Libellé" })).toHaveAccessibleDescription(
      "Une valeur est requise.",
    );
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("says at its field the name of a category the server finds too long", async () => {
    serve({ [CATEGORY]: { problem: refusal("cost_category_update_refused", 422) } });
    render(categoryList());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Sous-traitance\u00a0»");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    await vi.waitFor(() => {
      expect(label).toHaveFocus();
    });
    expect(label).toHaveAccessibleDescription("La valeur est trop longue.");
  });
});

describe("the type of a nature, as its commands say it", () => {
  it("presents fixed the type of a nature whose category is employed, rated and a role's, saying the conditions it lacks, and sends it as it is [WF-REF-0030-A] [WF-IHM-0090-A]", async () => {
    const client = serve();
    render(natures());
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Main-d'œuvre\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Main-d'œuvre\u00a0»");
    // La modification du type est refusée pour une nature dont une catégorie est employée, porte un
    // taux ou est rattachée à un rôle de ressource : the form offers no other type, and says why.
    expect(within(form).queryByRole("combobox", { name: "Type" })).toBeNull();
    const type = within(form).getByRole("textbox", { name: "Type" });
    expect(type).toHaveAttribute("readonly");
    expect(type).toHaveValue("Main-d’œuvre");
    expect(type).toHaveAccessibleDescription(
      "Le type ne se modifie pas. Conditions non remplies\u00a0: aucune catégorie de la nature employée, aucune catégorie de la nature portant un taux horaire et aucune catégorie de la nature rattachée à un rôle de ressource.",
    );
    expect(form).toHaveAccessibleDescription(
      "Le code, unique, et le libellé sont requis\u202f; le type de cette nature ne se modifie pas.",
    );
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    await userEvent.clear(label);
    await userEvent.type(label, "Main-d’œuvre interne");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual({
      code: "MO",
      label: "Main-d’œuvre interne",
      kind: "labor",
      lock_version: 1,
    });
    await expectAccessible(form);
  });

  it("presents fixed the type of the nature of provision for risks, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    serve();
    render(natures());
    await userEvent.click(screen.getByRole("button", { name: "Modifier «\u00a0Provision\u00a0»" }));
    expect(
      within(dialog("Modifier «\u00a0Provision\u00a0»")).getByRole("textbox", { name: "Type" }),
    ).toHaveAccessibleDescription(
      "Le type ne se modifie pas. Condition non remplie\u00a0: aucune catégorie de la nature employée.",
    );
  });

  it("offers the type of a nature that lists its change available, and says the refusal of the server that finds a category employed meanwhile [WF-REF-0030-A] [WF-IHM-0090-A]", async () => {
    const supplies = example("cost_type_created") as CostType;
    const client = serve({ [TYPE]: { problem: refusal("cost_type_kind_refused", 409) } });
    render(natures([supplies]));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Fournitures\u00a0»" }),
    );
    const form = dialog("Modifier «\u00a0Fournitures\u00a0»");
    expect(form).toHaveAccessibleDescription("Le code, unique, le libellé et le type sont requis.");
    const type = within(form).getByRole("combobox", { name: "Type" });
    expect(type).not.toHaveAccessibleDescription();
    await userEvent.selectOptions(type, "Main-d’œuvre");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    // La modification du type est refusée pour une nature dont une catégorie est employée.
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : aucune catégorie de la nature employée.",
    );
    expect(client.calls[0]?.body).toEqual({
      code: "FRN",
      label: "Fournitures",
      kind: "labor",
      lock_version: 1,
    });
    // The row stays as the page read it.
    expect(screen.getByRole("grid", { name: "Natures de coût", hidden: true })).toHaveTextContent(
      "Hors main-d’œuvre",
    );
  });
});

describe("the nature of a category, as its commands say it", () => {
  it("offers a category a nature of another type only when it lists that command available, and says the conditions it lacks otherwise [WF-IHM-0090-A]", async () => {
    serve();
    const [subcontracting] = first;
    if (subcontracting === undefined) {
      throw new Error("the volumes hold the subcontracting");
    }
    render(categoryList([created, subcontracting], ACTIVE));
    const options = (name: string) => {
      const nature = within(dialog(`Modifier «\u00a0${name}\u00a0»`)).getByRole("combobox", {
        name: "Nature",
      });
      return {
        nature,
        shown: within(nature)
          .getAllByRole("option")
          .map((option) => option.textContent),
      };
    };
    // Created today, attached to no line nor rate: every active nature.
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Petites fournitures\u00a0»" }),
    );
    const free = options("Petites fournitures");
    expect(free.shown).toEqual([
      "Choisir…",
      "DEB · Débours",
      "MO · Main-d'œuvre",
      "PRV · Provision",
    ]);
    expect(free.nature).not.toHaveAccessibleDescription();
    await userEvent.keyboard("{Escape}");
    // Employed by the estimate of the witness: the natures of its own type alone, and why.
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const held = options("Sous-traitance");
    expect(held.shown).toEqual(["Choisir…", "DEB · Débours"]);
    expect(held.nature).toHaveAccessibleDescription(
      "Seules les natures du même type sont proposées. Condition non remplie\u00a0: catégorie employée par aucune ligne.",
    );
  });

  it("offers a labour category that roles are attached to the natures of its type alone, saying the three conditions it lacks [WF-REF-0040-A] [WF-IHM-0090-A]", async () => {
    serve();
    const engineering = volumes.find((category) => category.code === "MO-001");
    if (engineering === undefined) {
      throw new Error("the volumes hold the electrical engineering");
    }
    render(categoryList([engineering], ACTIVE));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Ingénierie électrique\u00a0»" }),
    );
    const nature = within(dialog("Modifier «\u00a0Ingénierie électrique\u00a0»")).getByRole(
      "combobox",
      { name: "Nature" },
    );
    // Le rattachement d'une catégorie employée à une nature d'un autre type est refusé, de même que
    // celui d'une catégorie qui porte un taux, ou à laquelle un rôle de ressource est rattaché, à une
    // nature hors main-d'œuvre. The roles the refusal names (EP-14/L42r) are the next lot's to say.
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "MO · Main-d'œuvre"]);
    expect(nature).toHaveAccessibleDescription(
      "Seules les natures du même type sont proposées. Conditions non remplies\u00a0: catégorie employée par aucune ligne, catégorie sans taux horaire et catégorie rattachée à aucun rôle de ressource.",
    );
  });

  it("offers the category of provision for risks the natures of its type alone, saying the condition it lacks", async () => {
    serve();
    if (provision === undefined) {
      throw new Error("the volumes hold the provisions for risks");
    }
    render(categoryList([provision], ACTIVE));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Provisions pour risques\u00a0»" }),
    );
    const nature = within(dialog("Modifier «\u00a0Provisions pour risques\u00a0»")).getByRole(
      "combobox",
      { name: "Nature" },
    );
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "PRV · Provision"]);
    expect(nature).toHaveAccessibleDescription(
      "Seules les natures du même type sont proposées. Condition non remplie\u00a0: catégorie employée par aucune ligne.",
    );
  });

  it("offers a category under a deactivated nature the active natures of its type, as every nature read gives it", async () => {
    serve();
    const [subcontracting] = first;
    if (subcontracting === undefined) {
      throw new Error("the volumes hold the subcontracting");
    }
    // The disbursements deactivated, left out of the natures offered; the supplies, created today,
    // of the same type.
    const supplies = natureChoice(example("cost_type_created") as CostType);
    const actives = [supplies, ...ACTIVE.filter((choice) => choice.code !== "DEB")];
    const every = [
      ...ACTIVE.map((choice) => ({ ...choice, active: choice.code !== "DEB" })),
      supplies,
    ];
    render(categoryList([subcontracting], actives, every));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const nature = within(dialog("Modifier «\u00a0Sous-traitance\u00a0»")).getByRole("combobox", {
      name: "Nature",
    });
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "FRN · Fournitures", "DEB · Débours (désactivée)"]);
    expect(nature).toHaveAccessibleDescription(
      "Seules les natures du même type sont proposées. Condition non remplie\u00a0: catégorie employée par aucune ligne.",
    );
  });

  it("offers a category whose nature the page does not read its own nature alone, saying its type cannot be read", async () => {
    serve();
    const [subcontracting] = first;
    if (subcontracting === undefined) {
      throw new Error("the volumes hold the subcontracting");
    }
    // A session that may not read the deactivated natures: none gives the type of the disbursements.
    const actives = ACTIVE.filter((choice) => choice.code !== "DEB");
    const { unmount } = render(categoryList([subcontracting], actives));
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier «\u00a0Sous-traitance\u00a0»" }),
    );
    const nature = within(dialog("Modifier «\u00a0Sous-traitance\u00a0»")).getByRole("combobox", {
      name: "Nature",
    });
    expect(
      within(nature)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Choisir…", "Débours (désactivée)"]);
    expect(nature).toHaveAccessibleDescription(
      "Le type de la nature désactivée n’est pas lisible\u00a0: seule elle est proposée. Condition non remplie\u00a0: catégorie employée par aucune ligne.",
    );
    unmount();
    render(categoryList([subcontracting], actives, undefined, "en"));
    await userEvent.click(screen.getByRole("button", { name: "Modify “Sous-traitance”" }));
    expect(
      within(dialog("Modify “Sous-traitance”")).getByRole("combobox", { name: "Cost type" }),
    ).toHaveAccessibleDescription(
      "The type of the deactivated nature cannot be read: it alone is offered. Unmet condition: category employed by no line.",
    );
  });

  it.each([
    ["cost_category_kind_refused", "catégorie employée par aucune ligne"],
    ["cost_category_rated_kind_refused", "catégorie sans taux horaire"],
  ])(
    "says the refusal %s of a category attached to a nature of another type, naming the condition it lacks [WF-IHM-0090-A]",
    async (name, condition) => {
      const client = serve({ [CATEGORY]: { problem: refusal(name, 409) } });
      render(categoryList([created], ACTIVE));
      await userEvent.click(
        screen.getByRole("button", { name: "Modifier «\u00a0Petites fournitures\u00a0»" }),
      );
      const form = dialog("Modifier «\u00a0Petites fournitures\u00a0»");
      await userEvent.selectOptions(
        within(form).getByRole("combobox", { name: "Nature" }),
        "MO · Main-d'œuvre",
      );
      await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
      // Tout refus nomme la condition manquante.
      expect(await within(form).findByRole("alert")).toHaveTextContent(
        `L’état actuel ne permet pas cette opération. Condition non remplie : ${condition}.`,
      );
      expect(client.calls[0]?.body).toMatchObject({
        cost_type_id: "01926f3a-7c00-7000-8000-000000000461",
      });
      expect(refresh).not.toHaveBeenCalled();
    },
  );
});
