// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { readContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { ContextBanner } from "./context-banner";
import type { Project, ProjectReading, Subproject } from "./reading";
import type { Revision } from "./read-only";
import { type ListedRevision, listedRevision } from "./revision";

// The server of Next, as far as the choice needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => REMAINING,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
// The revisions of the witness (`revisions`): the current one, a draft without a version name, the
// reference, and the offer v1.0, the most recent first.
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const REMAINING = `/projects/${PROJECT}/revisions/${CURRENT}/remaining`;
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
// The French catalogue sets a no-break space inside quotes.
const NB = "\u00a0";
const READ_CURRENT = `Changer de révision, «${NB}Révision en cours${NB}» lue`;

/** The revisions of the witness, as the reading of the context gives them. */
const REVISIONS = (example("revisions") as { items: Revision[] }).items.map(listedRevision);

/**
 * The banner of the remaining to commit of the witness, in French, at the address given; under the
 * address the screen shares, as the screens whose other parts change the address render it, or
 * alone, as the others do.
 */
function banner(
  revisions: readonly ListedRevision[] | undefined,
  search = "",
  screenShares = true,
) {
  page.search = search;
  const context = readContext(REMAINING, new URLSearchParams(search));
  if (context === undefined) {
    throw new Error(`No context at ${REMAINING}`);
  }
  const subproject = (example("subprojects") as Subproject[]).find(
    (one) => one.subproject_id === context.parameters.get("subproject_id"),
  );
  const reading: ProjectReading = {
    pathname: REMAINING,
    context,
    project: example("project") as Project,
    revision: example("revision") as Revision,
    revisions,
    edits: new Set(),
    readOnly: false,
    filters:
      subproject === undefined
        ? []
        : [{ name: "subproject_id", value: subproject.subproject_id, subproject }],
  };
  const shown = <ContextBanner reading={reading} />;
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {screenShares ? <PendingAddress>{shown}</PendingAddress> : shown}
    </NextIntlClientProvider>,
  );
}

/** The region of the banner. */
function region() {
  return screen.getByRole("region", { name: "Contexte de lecture" });
}

/** The button of the choice, named by the revision read. */
function choice(name = READ_CURRENT) {
  return within(region()).getByRole("button", { name });
}

beforeEach(() => {
  router.push.mockClear();
});

describe("the revision the banner names", () => {
  it("offers the revisions of the project, the one read checked and said to a screen reader [WF-IHM-0020-A]", async () => {
    // Depuis la même grille, il ouvre une autre révision du projet sans passer par l'historique.
    const { container } = banner(REVISIONS);
    // The revision read, named among the facts of the banner and by the button that changes it.
    expect(within(region()).getAllByRole("definition")[1]).toHaveTextContent(/^Révision en cours$/);
    expect(choice()).toHaveAttribute("aria-haspopup", "menu");
    await expectAccessible(container);
    await userEvent.click(choice());
    const menu = screen.getByRole("menu");
    // Every revision, in the order the server lists them, the reference said so.
    expect(
      within(menu)
        .getAllByRole("menuitemradio")
        .map((item) => item.textContent),
    ).toEqual(["Révision en cours", "Référence (référence)", "Offre v1.0"]);
    expect(within(menu).getByRole("menuitemradio", { checked: true })).toHaveTextContent(
      "Révision en cours",
    );
  });

  it("offers no choice on a project that has no other revision", () => {
    // The revision read alone, as a project that has not marked any lists it.
    banner(REVISIONS.filter((listed) => listed.revision_id === CURRENT));
    expect(within(region()).getByText("Révision en cours")).toBeVisible();
    expect(within(region()).queryByRole("button")).toBeNull();
  });

  it("offers no choice when the revisions are not read", () => {
    banner(undefined);
    expect(within(region()).queryByRole("button")).toBeNull();
  });
});

describe("the choice of the revision read", () => {
  it("opens the revision chosen on the same screen by the pointer, the sub-project and the date of calculation kept, and shows it checked while the server reads it [WF-IHM-0020-A]", async () => {
    // Tout écran dont le bandeau nomme une révision y offre le choix de la révision lue parmi les
    // révisions du projet ; la révision choisie s'ouvre sur le même écran, le sous-projet filtré et
    // la date de calcul conservés (US-2330).
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementationOnce(() => {
      startTransition(() => navigation);
    });
    banner(REVISIONS, `subproject_id=${SUBPROJECT}&as_of=2026-05-31&search=Revue`);
    await userEvent.click(choice());
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Offre v1.0" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `/projects/${PROJECT}/revisions/${OFFER}/remaining?subproject_id=${SUBPROJECT}&as_of=2026-05-31`,
      { scroll: false },
    );
    // The address has not changed yet: the revision chosen shows checked, never the one before.
    await userEvent.click(choice());
    expect(screen.getByRole("menuitemradio", { checked: true })).toHaveTextContent("Offre v1.0");
    await act(async () => {
      arrive();
      await navigation;
    });
  });

  it("is made at the keyboard: the button opens the menu, the arrows go from one revision to the next, Enter chooses [WF-IHM-0020-A]", async () => {
    // Les deux choix se font au clavier comme au pointeur, et la révision lue se dit à un lecteur
    // d'écran (US-2330).
    banner(REVISIONS);
    choice().focus();
    await userEvent.keyboard("{Enter}");
    const menu = screen.getByRole("menu");
    // The menu opens on the first revision; the next is the reference.
    await userEvent.keyboard("{ArrowDown}");
    const reference = within(menu).getByRole("menuitemradio", { name: "Référence (référence)" });
    expect(reference).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(router.push).toHaveBeenLastCalledWith(
      `/projects/${PROJECT}/revisions/${REFERENCE}/remaining`,
      { scroll: false },
    );
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("asks nothing for the revision read chosen again", async () => {
    banner(REVISIONS, "search=Revue");
    await userEvent.click(choice());
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Révision en cours" }));
    expect(router.push).not.toHaveBeenCalled();
  });

  it.each([
    ["under the address the screen shares", true],
    ["on a screen that shares none", false],
  ])(
    "goes on from the address last asked, %s: a filter lifted just before stays lifted",
    async (_, screenShares) => {
      // A filter lifted from its chip, the address not arrived yet: the revision chosen goes on from
      // the address asked (défaut n° 20 de `typescript.md`); the banner shares it between its chips
      // and its choices whether or not the screen shares one around it.
      banner(REVISIONS, `subproject_id=${SUBPROJECT}`, screenShares);
      await userEvent.click(within(region()).getByRole("link", { name: /^Lever le filtre/ }));
      expect(router.push).toHaveBeenLastCalledWith(REMAINING, { scroll: false });
      await userEvent.click(choice());
      await userEvent.click(screen.getByRole("menuitemradio", { name: "Offre v1.0" }));
      expect(router.push).toHaveBeenLastCalledWith(
        `/projects/${PROJECT}/revisions/${OFFER}/remaining`,
        { scroll: false },
      );
    },
  );
});
