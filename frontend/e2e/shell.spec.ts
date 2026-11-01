// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Route, test } from "@playwright/test";

import { compile } from "./compile";
import { openMenu, setExpanded } from "./hydration";

// The session of the fake back is Camille Martin's, whose role grants the whole catalogue of
// permissions: every function is offered, and the menu of the account.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("the side bar folds into a rail of icons, whose entries keep their names in a tooltip, and stays folded", async ({
  page,
}) => {
  // The screen its rail leads to, reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/admin/users");
  await page.goto("/portfolio/projects");
  const bar = page.getByRole("banner");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  // Pressed once React answers it: its name says which way it goes, its state where the bar is.
  await setExpanded(bar.getByRole("button", { name: /la barre latérale$/ }), false);

  // Folded, the bar is a rail as wide as its icons, and each entry still names itself.
  await expect.poll(async () => (await nav.boundingBox())?.width).toBeLessThanOrEqual(48);
  await nav.getByRole("link", { name: "Projets", exact: true }).hover();
  await expect(page.getByRole("tooltip")).toHaveText("Projets");

  // The next visit finds it as the user left it; a block pressed in the rail unfolds it on its
  // functions.
  await page.reload();
  await expect(bar.getByRole("button", { name: "Déplier la barre latérale" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await setExpanded(nav.getByRole("button", { name: "Administration" }), true);
  await expect(bar.getByRole("button", { name: "Replier la barre latérale" })).toBeVisible();
  await nav.getByRole("link", { name: "Gestion des utilisateurs" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Gestion des utilisateurs");
});

test("folded into a rail on the page of a leaf, the bar shows its function alone as the path, and no Tab stops on a leaf", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/workload`);
  const bar = page.getByRole("banner");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  const leaf = nav.getByRole("link", { name: "Plan de charge", exact: true });
  const parent = nav.getByRole("link", { name: "Chiffrage et devis", exact: true });
  await expect(leaf).toBeVisible();
  await setExpanded(bar.getByRole("button", { name: /la barre latérale$/ }), false);
  await expect.poll(async () => (await nav.boundingBox())?.width).toBeLessThanOrEqual(48);

  await expect(leaf).toBeHidden();
  await expect(parent).toBeVisible();
  await expect(parent).toHaveAttribute("aria-current", "true");

  // From the first entry of the bar on, Tab goes entry by entry until it leaves the bar: never
  // to a leaf, which the rail hides.
  await nav.getByRole("link").first().focus();
  let left = false;
  for (let step = 0; step < 80 && !left; step += 1) {
    const where = await page.evaluate(() => {
      const active = document.activeElement;
      return {
        inBar: active?.closest("nav[aria-label='Fonctions']") != null,
        inLeaves: active?.closest("[data-slot=sidebar-menu-sub]") != null,
      };
    });
    left = !where.inBar;
    expect(where.inLeaves).toBe(false);
    if (!left) {
      await page.keyboard.press("Tab");
    }
  }
  // Eighty steps that never left the bar would prove nothing of the leaves past them.
  expect(left).toBe(true);
});

test("an open block of the FBS is not painted as the page shown", async ({ page }) => {
  await page.goto("/portfolio/projects");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  const block = nav.getByRole("button", { name: "Portefeuille", exact: true });
  const current = nav.getByRole("link", { name: "Portefeuille de projets" });
  await expect(block).toHaveAttribute("aria-expanded", "true");
  await expect(current).toHaveAttribute("aria-current", "page");
  // Nothing under the pointer: each shows its own background.
  await page.mouse.move(900, 600);
  const background = (element: HTMLElement) => getComputedStyle(element).backgroundColor;
  expect(await block.evaluate(background)).not.toBe(await current.evaluate(background));
});

test("the bar keeps the search, the tasks and the account at its right where the address leads nowhere", async ({
  page,
}) => {
  await page.goto("/admin/nobody");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Introuvable");
  const bar = page.getByRole("banner");
  await expect(bar.getByRole("navigation", { name: "Fil d’Ariane" })).toHaveCount(0);
  const account = await bar.getByRole("button", { name: "Compte de Camille Martin" }).boundingBox();
  const width = page.viewportSize()?.width ?? 0;
  expect((account?.x ?? 0) + (account?.width ?? 0)).toBeGreaterThan(width - 40);
});

test("the bar shows where the page sits, and the side bar names the project its screen reads", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/risks`);
  const crumbs = page.getByRole("banner").getByRole("navigation", { name: "Fil d’Ariane" });
  await expect(crumbs.getByRole("link", { name: "Projets" })).toHaveAttribute("href", "/");
  await expect(
    crumbs.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toHaveAttribute("href", `/projects/${PROJECT}?revision_id=${REVISION}`);
  await expect(crumbs.getByText("Gestion des risques")).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("button", { name: "Modernisation du poste de commande PRJ-001 En cours" }),
  ).toBeVisible();
});

test("the menu of the account leads to the pages of the account", async ({ page }) => {
  // The page reached from the menu, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/account/avatar");
  await page.goto("/");
  await openMenu(
    page.getByRole("button", { name: "Compte de Camille Martin" }),
    page.getByRole("menu"),
  );
  await expect(page.getByRole("menuitem", { name: "Se déconnecter" })).not.toHaveAttribute(
    "aria-disabled",
  );
  await expect(page.getByRole("menuitem", { name: "Changer le mot de passe" })).toHaveCount(0);
  await page.getByRole("menuitem", { name: "Changer l’avatar" }).click();

  await expect(page).toHaveURL("/account/avatar");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Changer l’avatar");
  await expect(page.getByLabel("Image PNG ou JPEG")).toBeVisible();
  await expect(page).toHaveTitle("Changer l’avatar — Waterfall");
});

test("a page of the account clicked in the menu while its prefetch is on its way keeps its title (#1499)", async ({
  page,
}) => {
  await compile(page.request, "/account/avatar");
  // The prefetch of the page down to its loading boundary — an RSC request marked as a prefetch,
  // for no segment — held on the network until the click has fallen, as the load of four workers
  // holds it. Next 16.4.3 then kept the empty head of the pending prefetch, and the title of the
  // page was lost for good (vercel/next.js#98684): the menu of the account no longer prefetches.
  let release: () => void = () => undefined;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/account/avatar*", async (route) => {
    const headers = route.request().headers();
    if (
      headers.rsc === "1" &&
      headers["next-router-prefetch"] === "1" &&
      headers["next-router-segment-prefetch"] === undefined
    ) {
      await released;
    }
    await route.fallback();
  });
  await page.goto("/");
  await openMenu(
    page.getByRole("button", { name: "Compte de Camille Martin" }),
    page.getByRole("menu"),
  );
  // Hovered first, as a pointer does. Next prefetches a link when it enters the viewport, and
  // reschedules that prefetch at a higher priority on hover (not in a development build, which
  // skips it): the hover is here to let a link that prefetches send its prefetch before the click.
  // Without the fix, it has in nearly every run at four workers (62 out of 64); in the others it
  // goes out during the click, too late to be held across it, and the run passes.
  await page.getByRole("menuitem", { name: "Changer l’avatar" }).hover();
  await expect(page.getByRole("menuitem", { name: "Se déconnecter" })).not.toHaveAttribute(
    "aria-disabled",
  );
  await page.getByRole("menuitem", { name: "Changer l’avatar" }).click();
  release();

  await expect(page).toHaveURL("/account/avatar");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Changer l’avatar");
  await expect(page).toHaveTitle("Changer l’avatar — Waterfall");
});

test("the bar tells the refusal of a write whose screen was left by « Précédent » before it answered (#863)", async ({
  page,
}) => {
  await compile(page.request, "/account");
  // The screen of the account reached by the router, in the same document: « Précédent » leaves it
  // without loading another.
  await page.goto("/");
  await openMenu(
    page.getByRole("button", { name: "Compte de Camille Martin" }),
    page.getByRole("menu"),
  );
  await page.getByRole("menuitem", { name: "Mon compte" }).click();
  await expect(page).toHaveURL("/account");
  // The record of the preferences held on its way to the server of Next, then cut: the server
  // action fails, and the screen that made it is gone by then.
  let cut: () => void = () => undefined;
  const held = new Promise<void>((resolve) => {
    cut = resolve;
  });
  const handlers = new Set<Promise<void>>();
  const record = async (route: Route): Promise<void> => {
    if (route.request().headers()["next-action"] === undefined) {
      await route.continue();
      return;
    }
    await held;
    await route.abort();
  };
  const account = (route: Route): Promise<void> => {
    const handled = record(route);
    handlers.add(handled);
    const settled = (): void => {
      handlers.delete(handled);
    };
    handled.then(settled, settled);
    return handled;
  };
  await page.route("**/account", account);
  // A choice made before React hydrated the page is lost: it is made again until it holds.
  const dark = page.getByRole("radio", { name: "Sombre" });
  await expect(async () => {
    await dark.click();
    await expect(dark).toBeChecked({ timeout: 500 });
  }).toPass();
  const sent = page.waitForRequest((request) => request.headers()["next-action"] !== undefined);
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await sent;

  await page.goBack();
  await expect(page).toHaveURL("/");
  // The record is held by a local state, not a transition (#1484): the router shows the home at
  // once, the record still under way, and the screen of the account goes with what would tell its
  // refusal — released, the write is told by the bar once refused, not before.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  await expect(page.getByRole("heading", { name: "Mon compte" })).toHaveCount(0);
  const bar = page.getByRole("banner");
  await expect(bar.getByRole("alert")).toHaveCount(0);
  cut();
  const alert = bar.getByRole("alert");
  await expect(alert).toHaveText(
    /^Une modification qui n’est plus affichée a été refusée\s: elle n’est pas enregistrée\./,
  );
  await alert.getByRole("button", { name: "Fermer l’avis" }).click();
  await expect(alert).toHaveCount(0);
  // The route is taken away once its handlers are done, as `holdScripts` does (#1721).
  while (handlers.size > 0) {
    await Promise.allSettled([...handlers]);
  }
  await page.unroute("**/account", account);
});
