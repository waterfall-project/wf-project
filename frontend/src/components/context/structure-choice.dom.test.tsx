// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { readContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { ContextBanner } from "./context-banner";
import type { Project, ProjectReading, Subproject } from "./reading";
import { listedStructure, type StructureChoices } from "./structure";

// The server of Next, as far as the choice needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PLANNING,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const PLANNING = `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102/planning`;
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
// The structures of the current revision (`structures`): the main one, the amendment 2, and the
// own estimates of the three risks.
const MAIN = "01926f3a-7c00-7000-8000-000000000201";
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
// The French catalogue sets a no-break space inside quotes.
const NB = " ";

type CostStructure = components["schemas"]["CostStructure"];

/** The structures of an example, the one given read. */
function choices(name: "structures" | "structures_without_tasks", read: string): StructureChoices {
  const listed = (example(name) as CostStructure[]).map(listedStructure);
  const found = listed.find((structure) => structure.structure_id === read);
  if (found === undefined) {
    throw new Error(`No structure ${read} in ${name}`);
  }
  return { read: found, listed };
}

/** The banner of the planning of the witness, in French, at the address `search` gives. */
function banner(structure: StructureChoices, search = "") {
  page.search = search;
  const context = readContext(PLANNING, new URLSearchParams(search));
  if (context === undefined) {
    throw new Error(`No context at ${PLANNING}`);
  }
  const subproject = (example("subprojects") as Subproject[]).find(
    (one) => one.subproject_id === context.parameters.get("subproject_id"),
  );
  const reading: ProjectReading = {
    pathname: PLANNING,
    context,
    project: example("project") as Project,
    revision: undefined,
    edits: new Set(),
    readOnly: false,
    filters:
      subproject === undefined
        ? []
        : [{ name: "subproject_id", value: subproject.subproject_id, subproject }],
  };
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ContextBanner reading={reading} structure={structure} />
    </NextIntlClientProvider>,
  );
}

/** The region of the banner. */
function region() {
  return screen.getByRole("region", { name: "Contexte de lecture" });
}

/** Open the menu of the structures from its button, named by the structure read. */
async function openChoice(read: string): Promise<HTMLElement> {
  await userEvent.click(
    within(region()).getByRole("button", { name: `Changer de structure, «${NB}${read}${NB}» lue` }),
  );
  return screen.getByRole("menu");
}

beforeEach(() => {
  router.push.mockClear();
});

describe("the structure the banner names", () => {
  it("names the differential a grid is opened on, and its kind, and offers the structures of the revision [WF-IHM-0020-A]", async () => {
    // Une grille ouverte sur une structure différentielle nomme cette structure.
    const { container } = banner(choices("structures", AMENDMENT));
    expect(within(region()).getByText("Avenant 2 — reprise des essais")).toBeVisible();
    expect(within(region()).getByText("Avenant")).toBeVisible();
    await expectAccessible(container);
    const menu = await openChoice("Avenant 2 — reprise des essais");
    // The structures in the order the server lists them, the merged risk said so, each kind but
    // the main one under its name, the one read checked.
    expect(
      within(menu)
        .getAllByRole("menuitemradio")
        .map((item) => item.textContent),
    ).toEqual([
      "Structure principale",
      "Avenant 2 — reprise des essais",
      "Risque de reprise du câblage",
      "Retard de livraison des armoires (fusionnée)",
      "Indisponibilité de l'automaticien",
    ]);
    expect(within(menu).getByRole("menuitemradio", { checked: true })).toHaveTextContent(
      "Avenant 2 — reprise des essais",
    );
    const amendments = within(menu).getByRole("group", { name: "Avenant" });
    expect(within(amendments).getAllByRole("menuitemradio")).toHaveLength(1);
    const risks = within(menu).getByRole("group", { name: "Devis de risque" });
    expect(within(risks).getAllByRole("menuitemradio")).toHaveLength(3);
  });

  it("names the main structure to a screen reader alone, which the head of the grid names", () => {
    banner(choices("structures", MAIN));
    const named = within(region()).getByText("Structure principale");
    expect(named).toHaveClass("sr-only");
    expect(within(region()).queryByText("Avenant")).toBeNull();
  });

  it("offers no choice on a revision that has no other structure", () => {
    banner(choices("structures_without_tasks", "01926f3a-7c00-7000-8000-000000000207"));
    expect(within(region()).queryByRole("button")).toBeNull();
  });
});

describe("the choice of the structure", () => {
  it("reads the structure chosen by the address, the rest of it kept, and shows it checked while the server reads it", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementationOnce(() => {
      startTransition(() => navigation);
    });
    banner(choices("structures", MAIN), "search=Revue");
    const menu = await openChoice("Structure principale");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "Avenant 2 — reprise des essais" }),
    );
    expect(router.push).toHaveBeenLastCalledWith(
      `${PLANNING}?search=Revue&structure=${AMENDMENT}`,
      { scroll: false },
    );
    // The address has not changed yet: the structure chosen shows checked, never the one before.
    const reopened = await openChoice("Structure principale");
    expect(within(reopened).getByRole("menuitemradio", { checked: true })).toHaveTextContent(
      "Avenant 2 — reprise des essais",
    );
    await act(async () => {
      arrive();
      await navigation;
    });
  });

  it("takes the parameter off the address for the main structure, which reads by default", async () => {
    banner(choices("structures", AMENDMENT), `structure=${AMENDMENT}&search=Revue`);
    const menu = await openChoice("Avenant 2 — reprise des essais");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "Structure principale" }),
    );
    expect(router.push).toHaveBeenLastCalledWith(`${PLANNING}?search=Revue`, { scroll: false });
  });

  it("leaves the grid on the structure it reads when a filter of the context is lifted", () => {
    banner(choices("structures", AMENDMENT), `subproject_id=${SUBPROJECT}&structure=${AMENDMENT}`);
    const lift = within(region()).getByRole("link", { name: /^Lever le filtre/ });
    expect(lift).toHaveAttribute("href", `${PLANNING}?structure=${AMENDMENT}`);
  });
});
