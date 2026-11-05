// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the harness of the screens opens by a gesture (`opened.ts`), proved on a page written for
 * it: the triggers it plays and those it leaves, the cell whose editor it opens. A tool of the
 * harness, which proves no requirement itself.
 */
import { expect, test } from "@playwright/test";

import { openers } from "./opened";

test("plays each trigger of a dialog or a menu shown and enabled once, a trigger a grid repeats on its first row alone, and the first cell of each grid that takes an entry", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.setContent(
    `<!doctype html><html lang="fr"><body>
       <button aria-haspopup="dialog">Nouveau</button>
       <button aria-haspopup="menu">Colonnes</button>
       <button aria-haspopup="menu">Colonnes</button>
       <button aria-haspopup="dialog" disabled>Inactif</button>
       <button aria-haspopup="dialog" aria-disabled="true">Indisponible</button>
       <button aria-haspopup="dialog" hidden>Caché</button>
       <button>Simple</button>
       <table role="grid" aria-label="Grille">
         <tr>
           <td data-column="label" aria-readonly="true">A</td>
           <td data-column="amount" aria-readonly="true" aria-haspopup="dialog">1</td>
           <td data-column="hours">2</td>
           <td data-column="roles"><button aria-haspopup="dialog">Rôles de A</button></td>
         </tr>
         <tr>
           <td data-column="label" aria-readonly="true">B</td>
           <td data-column="amount" aria-readonly="true" aria-haspopup="dialog">3</td>
           <td data-column="hours">4</td>
           <td data-column="roles"><button aria-haspopup="dialog">Rôles de B</button></td>
         </tr>
       </table>
       <table role="grid" aria-label="Lecture"><tr><td data-column="label" aria-readonly="true">C</td></tr></table>
     </body></html>`,
  );
  const found = await openers(page, true);
  expect(found.map(({ opens, said }) => [opens, said])).toEqual([
    ["dialog", "the trigger of the dialog « Nouveau »"],
    ["menu", "the trigger of the menu « Colonnes »"],
    ["dialog", "the trigger of the dialog « Rôles de A »"],
    ["editor", "the editor of the cell hours of the grid « Grille »"],
  ]);
  await expect(found[3]?.at ?? page.locator("none")).toHaveText("2");
});

test("plays the triggers of the shell — outside main, or marked data-shell — only where asked, those of the screen always, and the cells of the grids", async ({
  page,
}) => {
  await page.setContent(
    `<!doctype html><html lang="fr"><body>
       <header><button aria-haspopup="menu">Compte</button></header>
       <main>
         <h1>Écran <button aria-haspopup="dialog" data-shell="">Aide</button></h1>
         <button aria-haspopup="dialog">Nouveau</button>
         <table role="grid" aria-label="Grille"><tr><td data-column="hours">2</td></tr></table>
       </main>
     </body></html>`,
  );
  const named = async (shell: boolean) =>
    (await openers(page, shell)).map(({ said, shell: inShell }) => [said, inShell]);
  expect(await named(false)).toEqual([
    ["the trigger of the dialog « Nouveau »", false],
    ["the editor of the cell hours of the grid « Grille »", false],
  ]);
  expect(await named(true)).toEqual([
    ["the trigger of the menu « Compte »", true],
    ["the trigger of the dialog « Aide »", true],
    ["the trigger of the dialog « Nouveau »", false],
    ["the editor of the cell hours of the grid « Grille »", false],
  ]);
});
