// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The walk by the keyboard of the accessibility of the screens (`tab-walk.ts`), proved on pages
 * written for it: each fault it must name, named, and what it must let pass, let pass. A tool of
 * the harness, which proves no requirement itself.
 */
import { expect, type Page, test } from "@playwright/test";

import { lost, walkByTab } from "./tab-walk";

/** A page of its own, written in the window of the harness. */
async function write(page: Page, body: string): Promise<void> {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.setContent(`<!doctype html><html lang="fr"><body>${body}</body></html>`);
}

test("names what a narrower window takes out of the reach of the keyboard", async ({ page }) => {
  await write(
    page,
    `<style>@media (max-width: 1000px) { .wide { display: none; } }</style>
     <button>Toujours</button><button class="wide">Large seulement</button><a href="#">Lien</a>`,
  );
  const wide = await walkByTab(page);
  await page.setViewportSize({ width: 911, height: 512 });
  const narrow = await walkByTab(page);
  expect(wide.reached).toContain("button « Large seulement »");
  expect(narrow.missed).toEqual([]);
  expect(lost(wide.reached, narrow.reached)).toEqual(["button « Large seulement »"]);
});

test("takes an indicator of the focus for one only when the focus brings it, and it shows", async ({
  page,
}) => {
  await write(
    page,
    `<style>
       button { outline: none; margin: 8px; }
       #black:focus-visible { outline: 2px solid rgb(0, 0, 0); }
       #inset:focus-visible { box-shadow: inset 0 0 0 2px rgb(0, 0, 255); }
       #cut:focus-visible { outline: 2px solid rgb(0, 0, 255); }
       #inner:focus-visible { outline: 2px solid rgb(0, 0, 255); outline-offset: -2px; }
     </style>
     <button id="black">Contour noir</button>
     <button style="box-shadow: 0 0 0 2px rgb(0, 0, 255)">Anneau permanent</button>
     <button id="inset" style="padding: 0">
       <span style="display: block; padding: 8px; background: rgb(240, 240, 240)">Anneau dessous</span>
     </button>
     <div style="overflow: auto; width: 150px; border: 1px solid rgb(0, 0, 0)">
       <button id="cut" style="display: block; box-sizing: border-box; width: 150px; margin: 0">
         Contour coupé
       </button>
     </div>
     <button id="inner" style="border: 0; padding: 0">
       <span style="position: relative; display: block; padding: 8px; background: rgb(240, 240, 240)">
         Contour dessous
       </span>
     </button>`,
  );
  const walk = await walkByTab(page);
  expect(walk.reached).toHaveLength(5);
  expect(walk.unmarked).toEqual([
    "button « Anneau permanent »",
    "button « Anneau dessous »",
    "button « Contour coupé »",
    "button « Contour dessous »",
  ]);
});

test("takes a transparent outline for no indicator of the focus", async ({ page }) => {
  await write(
    page,
    `<style>#t:focus-visible { outline: 2px solid transparent; }</style>
     <button>Visible</button><button id="t">Transparent</button>`,
  );
  const walk = await walkByTab(page);
  expect(walk.unmarked).toEqual(["button « Transparent »"]);
});

test("judges an element born during the walk once it is left, and says when it cannot", async ({
  page,
}) => {
  await write(
    page,
    `<button>Avant</button>
     <div id="group" role="radiogroup" aria-label="Choix" tabindex="0"></div>
     <div id="gone" tabindex="0" aria-label="Passage"></div>
     <button>Après</button>
     <script>
       const group = document.getElementById("group");
       group.addEventListener("focus", () => {
         const radio = document.createElement("button");
         radio.setAttribute("role", "radio");
         radio.tabIndex = -1;
         radio.style.outline = "none";
         radio.textContent = "Oui";
         group.replaceChildren(radio);
         radio.focus();
       });
       const gone = document.getElementById("gone");
       gone.addEventListener("focus", () => {
         const button = document.createElement("button");
         button.textContent = "Éphémère";
         button.addEventListener("blur", () => button.remove());
         gone.replaceChildren(button);
         button.focus();
       });
     </script>`,
  );
  const walk = await walkByTab(page);
  expect(walk.reached).toEqual([
    "button « Avant »",
    "radio « Oui »",
    "button « Éphémère »",
    "button « Après »",
  ]);
  expect(walk.unmarked).toEqual(["radio « Oui »"]);
  expect(walk.unjudged).toEqual(["button « Éphémère »"]);
});

test("sees an element only when nothing hides it: a transparent ancestor, a layer the pointer passes through", async ({
  page,
}) => {
  await write(
    page,
    `<button>Visible</button>
     <div style="opacity: 0"><button>Transparent</button></div>
     <div style="position: relative; display: inline-block">
       <button>Recouvert</button>
       <div style="position: absolute; inset: 0; background: rgb(255, 255, 255); pointer-events: none"></div>
     </div>
     <div style="overflow: hidden; width: 10px; height: 10px">
       <button style="position: fixed; top: 200px; left: 200px">Fixe</button>
     </div>
     <a href="#" style="position: absolute; left: -9999px">Hors champ</a>`,
  );
  const walk = await walkByTab(page);
  expect(walk.reached).toHaveLength(5);
  expect(walk.unseen).toEqual([
    "button « Transparent », hidden or transparent",
    "button « Recouvert », under div «  »",
    "a « Hors champ », out of the window",
  ]);
});

test("names a transparent layer that takes the pointer from an element, not one it passes through", async ({
  page,
}) => {
  await write(
    page,
    `<div style="position: relative; display: inline-block">
       <button>Capté</button><div style="position: absolute; inset: 0"></div>
     </div>
     <div style="position: relative; display: inline-block">
       <button>Traversé</button><div style="position: absolute; inset: 0; pointer-events: none"></div>
     </div>`,
  );
  const walk = await walkByTab(page);
  expect(walk.unseen).toEqual([]);
  expect(walk.covered).toEqual(["button « Capté », under div «  »"]);
});

test("names what lies beyond the edge of a box that hides it, and the links and buttons out of the order of the keyboard but in a widget of their own", async ({
  page,
}) => {
  await write(
    page,
    `<div style="overflow: hidden; width: 200px; white-space: nowrap">
       <span style="display: inline-block; width: 300px"></span><button>Au-delà</button>
     </div>
     <div style="overflow-x: hidden; overflow-y: auto; height: 40px">
       <div style="height: 100px"></div><button>Plus bas</button>
     </div>
     <div style="overflow: hidden; width: 200px">
       <div id="far" style="overflow: auto; width: 600px; white-space: nowrap">
         <span style="display: inline-block; width: 400px"></span><button>Loin</button><span
           style="display: inline-block; width: 600px"></span>
       </div>
     </div>
     <button tabindex="-1">Hors du clavier</button>
     <div role="toolbar" aria-label="Outils"><button>Un</button><button tabindex="-1">Deux</button></div>
     <div role="toolbar" aria-label="Sans arrêt">
       <button tabindex="-1">Trois</button><button tabindex="-1">Quatre</button>
     </div>
     <div inert>
       <div role="toolbar" aria-label="Inerte"><button tabindex="-1">Cinq</button></div>
     </div>
     <script>document.getElementById("far").scrollLeft = 250;</script>`,
  );
  // Scrolled before the walk, the box of « Loin » still shows it where its edge would cut it.
  const walk = await walkByTab(page);
  expect(walk.clipped).toEqual(["button « Au-delà »", "button « Loin »"]);
  expect(walk.untabbable).toEqual(["button « Hors du clavier »"]);
  expect(walk.stopless).toEqual(["toolbar « Sans arrêt »"]);
});

test("names what Tab may reach and never reaches, a loop back to the first taking it away", async ({
  page,
}) => {
  await write(
    page,
    `<button>A</button><button id="b">B</button><button>C</button><button>D</button>
     <script>
       document.getElementById("b").addEventListener("keydown", (event) => {
         if (event.key === "Tab") {
           event.preventDefault();
           document.querySelector("button").focus();
         }
       });
     </script>`,
  );
  const walk = await walkByTab(page);
  expect(walk.trapped).toBeUndefined();
  expect(walk.reached).toEqual(["button « A »", "button « B »"]);
  expect(walk.missed).toEqual(["button « C »", "button « D »"]);
});

test("takes a field made of fields for no trap, and a loop that never comes back to the first for one", async ({
  page,
}) => {
  await write(
    page,
    `<label>Date <input type="date"></label><button>Après</button>
     <div id="loop"><button>Boucle A</button><button>Boucle B</button></div>
     <script>
       document.querySelectorAll("#loop button")[1].addEventListener("keydown", (event) => {
         if (event.key === "Tab") {
           event.preventDefault();
           document.querySelectorAll("#loop button")[0].focus();
         }
       });
     </script>`,
  );
  const walk = await walkByTab(page);
  expect(walk.trapped).toBe("button « Boucle A »");
  expect(walk.reached).toEqual([
    "input « Date »",
    "button « Après »",
    "button « Boucle A »",
    "button « Boucle B »",
  ]);
});

test("takes an element that keeps the focus on Tab for a trap", async ({ page }) => {
  await write(
    page,
    `<button>Avant</button><textarea aria-label="Notes"></textarea>
     <script>
       document.querySelector("textarea").addEventListener("keydown", (event) => {
         if (event.key === "Tab") {
           event.preventDefault();
           event.target.setRangeText("\\t", event.target.selectionStart, event.target.selectionEnd, "end");
         }
       });
     </script>`,
  );
  const walk = await walkByTab(page);
  expect(walk.trapped).toBe("textarea « Notes », holding the focus");
});

test("takes a widget that hands the focus to one of its items for reached, and nothing else", async ({
  page,
}) => {
  await write(
    page,
    `<button>Avant</button>
     <div id="group" role="radiogroup" aria-label="Choix" tabindex="0">
       <button role="radio" aria-checked="true" tabindex="-1">Oui</button>
     </div>
     <div id="card" role="button" tabindex="0" aria-label="Carte"><a href="#">Ouvrir</a></div>
     <button>Après</button>
     <script>
       const group = document.getElementById("group");
       group.addEventListener("focus", () => group.querySelector("button").focus());
       const card = document.getElementById("card");
       card.addEventListener("focus", () => card.querySelector("a").focus());
     </script>`,
  );
  const walk = await walkByTab(page);
  expect(walk.reached).toEqual([
    "button « Avant »",
    "radio « Oui »",
    "a « Ouvrir »",
    "button « Après »",
  ]);
  expect(walk.missed).toEqual(["button « Carte »"]);
});
