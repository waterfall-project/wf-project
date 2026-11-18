// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { BASE_PARAMETER, readContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { ContextBanner } from "./context-banner";
import type { Project, ProjectReading } from "./reading";
import type { Revision } from "./read-only";
import { baseOptions, type ListedRevision, listedRevision } from "./revision";

// The server of Next, as far as the choice needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => ESTIMATE,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
// The revisions of the witness (`revisions`): the current one, a copy of the reference, the
// reference, and the offer v1.0, the most recent first.
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const IN_PROJECT = `/projects/${PROJECT}/revisions`;
const ESTIMATE = `${IN_PROJECT}/${CURRENT}/estimate`;
// The French catalogue sets a no-break space inside quotes.
const NB = "\u00a0";

/** The revisions of the witness, as the reading of the context gives them. */
const REVISIONS = (example("revisions") as { items: Revision[] }).items.map(listedRevision);

/**
 * The banner of the estimate of the current revision of the witness, in French, at the address
 * given, under the address the screen shares, the bases offered as the grid gives them.
 */
function banner(search = "", listed: readonly ListedRevision[] | "unread" = REVISIONS) {
  const revisions = listed === "unread" ? undefined : listed;
  page.search = search;
  const context = readContext(ESTIMATE, new URLSearchParams(search));
  if (context === undefined) {
    throw new Error(`No context at ${ESTIMATE}`);
  }
  const revision = example("revision") as Revision;
  const reading: ProjectReading = {
    pathname: ESTIMATE,
    context,
    project: example("project") as Project,
    revision,
    revisions,
    edits: new Set(),
    readOnly: false,
    filters: [],
  };
  const base = { chosen: context.base, offered: baseOptions(revisions ?? [], revision) };
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ContextBanner reading={reading} base={base} />
      </PendingAddress>
    </NextIntlClientProvider>,
  );
}

/** The region of the banner. */
function region() {
  return screen.getByRole("region", { name: "Contexte de lecture" });
}

/** The facts the banner names, as a screen reader reads them. */
function facts(): (string | null)[] {
  return within(region())
    .getAllByRole("definition")
    .map((fact) => fact.textContent);
}

/** A button of the banner, by its name. */
function button(name: string) {
  return within(region()).getByRole("button", { name });
}

const CHOOSE = "Choisir une base de comparaison";
const CHANGE_REFERENCE = `Changer de base, «${NB}Référence${NB}» comparée`;

beforeEach(() => {
  router.push.mockClear();
});

describe("the base the banner offers", () => {
  it("is chosen among the marked revisions from the estimate of the revision under way, without leaving the screen, which names it and lifts it without opening any panel [WF-IHM-0020-A]", async () => {
    // Depuis la grille de devis de la révision en cours, l'utilisateur choisit une révision marquée
    // pour base sans quitter l'écran ; l'écran la nomme, et la comparaison se lève sans ouvrir aucun
    // panneau.
    const unchosen = banner();
    await userEvent.click(button(CHOOSE));
    const menu = screen.getByRole("menu");
    // The revision read is a copy of the reference, offered first; the revision under way never.
    expect(
      within(menu)
        .getAllByRole("menuitemradio")
        .map((item) => item.textContent),
    ).toEqual(["Référence (référence)", "Offre v1.0"]);
    expect(within(menu).queryByRole("menuitemradio", { checked: true })).toBeNull();
    await userEvent.click(within(menu).getByRole("menuitemradio", { name: "Offre v1.0" }));
    expect(router.push).toHaveBeenLastCalledWith(`${ESTIMATE}?${BASE_PARAMETER}=${OFFER}`, {
      scroll: false,
    });

    // The address read anew names the base: the banner names it, and lifts it by a link of its own.
    unchosen.unmount();
    const { container } = banner(`${BASE_PARAMETER}=${OFFER}`);
    expect(facts()).toContain(`Comparée à «${NB}Offre v1.0${NB}»`);
    const lift = within(region()).getByRole("link", {
      name: `Lever la comparaison avec «${NB}Offre v1.0${NB}»`,
    });
    expect(lift).toHaveAttribute("href", ESTIMATE);
    await expectAccessible(container);
    await userEvent.click(lift);
    expect(router.push).toHaveBeenLastCalledWith(ESTIMATE, { scroll: false });
  });

  it("is said to a screen reader, its menu accessible once open [WF-IHM-0020-A]", async () => {
    // Les deux choix se font au clavier comme au pointeur, et la révision lue comme la base se
    // disent à un lecteur d'écran (US-2330).
    const { baseElement } = banner(`${BASE_PARAMETER}=${REFERENCE}`);
    // The base is a fact of the banner, named to a screen reader by its term.
    expect(within(region()).getByText("Base de comparaison").closest("dt")).not.toBeNull();
    expect(button(CHANGE_REFERENCE)).toHaveAttribute("aria-haspopup", "menu");
    await userEvent.click(button(CHANGE_REFERENCE));
    expect(screen.getByRole("menuitemradio", { checked: true })).toHaveTextContent(
      "Référence (référence)",
    );
    await expectAccessible(baseElement);
  });

  it("is chosen at the keyboard: the button opens the menu, the arrows go from one base to the next, Enter chooses [WF-IHM-0020-A]", async () => {
    banner("search=Revue");
    button(CHOOSE).focus();
    await userEvent.keyboard("{Enter}");
    const menu = screen.getByRole("menu");
    await userEvent.keyboard("{ArrowDown}");
    const offer = within(menu).getByRole("menuitemradio", { name: "Offre v1.0" });
    expect(offer).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(router.push).toHaveBeenLastCalledWith(
      `${ESTIMATE}?search=Revue&${BASE_PARAMETER}=${OFFER}`,
      { scroll: false },
    );
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("shows the base chosen checked while the server reads it", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementationOnce(() => {
      startTransition(() => navigation);
    });
    banner(`${BASE_PARAMETER}=${REFERENCE}`);
    await userEvent.click(button(CHANGE_REFERENCE));
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Offre v1.0" }));
    await userEvent.click(button(CHANGE_REFERENCE));
    expect(screen.getByRole("menuitemradio", { checked: true })).toHaveTextContent("Offre v1.0");
    await act(async () => {
      arrive();
      await navigation;
    });
  });

  it("names a base the project does not list as unnamed, and still lifts it", () => {
    banner(`${BASE_PARAMETER}=${OFFER}`, "unread");
    expect(facts()).toContain(`Comparée à «${NB}sans nom${NB}»`);
    const lift = `Lever la comparaison avec «${NB}sans nom${NB}»`;
    expect(within(region()).getByRole("link", { name: lift })).toHaveAttribute("href", ESTIMATE);
    expect(within(region()).queryByRole("button", { name: CHOOSE })).toBeNull();
  });

  it("is not offered when the project has no marked revision but the one read", () => {
    const alone = REVISIONS.filter((listed) => listed.revision_id === CURRENT);
    banner("", alone);
    expect(within(region()).queryByRole("button", { name: CHOOSE })).toBeNull();
    expect(within(region()).queryByText("Base de comparaison")).toBeNull();
  });
});

describe("the revision read chosen in a comparison", () => {
  it("keeps the base for any other revision, and lifts the comparison for the base itself [WF-IHM-0020-A]", async () => {
    // Choisir pour révision lue la base d'une comparaison active lève la comparaison ; toute autre
    // révision choisie garde la base (décision de l'auteur du 2026-11-15).
    const readCurrent = `Changer de révision, «${NB}Révision en cours${NB}» lue`;
    banner(`${BASE_PARAMETER}=${REFERENCE}`);
    await userEvent.click(button(readCurrent));
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Offre v1.0" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${IN_PROJECT}/${OFFER}/estimate?${BASE_PARAMETER}=${REFERENCE}`,
      { scroll: false },
    );
  });

  it("lifts the comparison when the base is chosen for revision read [WF-IHM-0020-A]", async () => {
    banner(`${BASE_PARAMETER}=${REFERENCE}`);
    await userEvent.click(button(`Changer de révision, «${NB}Révision en cours${NB}» lue`));
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Référence (référence)" }));
    expect(router.push).toHaveBeenLastCalledWith(`${IN_PROJECT}/${REFERENCE}/estimate`, {
      scroll: false,
    });
  });
});
