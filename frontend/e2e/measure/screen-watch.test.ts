// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
// @vitest-environment happy-dom
/**
 * The script that watches a screen of the project (`screen-watch.ts`, US-2420), played in a
 * document: a tool of the measure, which covers no requirement of its own and cites none.
 *
 * The condition `windowed` (the top of the section or of its chart within the window) is not
 * covered here: happy-dom lays nothing out, and `getBoundingClientRect` answers a zero box, always
 * within the window. The measure itself, in a browser, is its test.
 */
import { beforeEach, describe, expect, it } from "vitest";

import { armScreen, type Watched } from "./screen-watch";

const ARMED = "wfTestArmed";
const ADDRESS = String.raw`\/indicators(\?|$)`;
const CHART: Watched = {
  name: "Coûts cumulés",
  chart: true,
  windowed: false,
  empty: "^Rien à tracer",
};

/** Give an element what React gives it when it takes it over. */
function hydrate(element: Element): void {
  Object.assign(element, { __reactProps$test: {} });
}

/** A page under the address, its `main` holding the markup. */
function page(path: string, markup: string): void {
  (window as unknown as { happyDOM: { setURL(url: string): void } }).happyDOM.setURL(
    `http://localhost${path}`,
  );
  document.body.innerHTML = `<main>${markup}</main>`;
}

const slot = () => (window as unknown as Record<string, number | null | undefined>)[ARMED];

/** Let a few frames pass. */
const frames = () => new Promise((resolve) => setTimeout(resolve, 80));

function arm(sections: readonly Watched[] = [CHART]): void {
  armScreen({ sections, address: ADDRESS, armed: ARMED });
}

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("armScreen", () => {
  it("takes a section whose chart is drawn, with no button in it", async () => {
    page(
      "/indicators",
      `<section aria-label="Coûts cumulés"><div role="img"><svg><path d="M0 0"/></svg></div></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    arm();
    await frames();
    expect(slot()).toEqual(expect.any(Number));
  });

  it("takes a section that says it has nothing to draw, hydrated, with no button in it", async () => {
    page(
      "/indicators",
      `<section aria-label="Coûts cumulés"><p>Rien à tracer : aucune ligne.</p></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    arm();
    await frames();
    expect(slot()).toEqual(expect.any(Number));
  });

  it("waits for the hydration of the section, in either state", async () => {
    page(
      "/indicators",
      `<section aria-label="Coûts cumulés"><p>Rien à tracer : aucune ligne.</p></section>`,
    );
    arm();
    await frames();
    expect(slot()).toBeNull();
    hydrate(document.querySelector("section") as Element);
    await frames();
    expect(slot()).toEqual(expect.any(Number));
  });

  it("waits for a chart that is not drawn yet", async () => {
    page(
      "/indicators",
      `<section aria-label="Coûts cumulés"><div role="img"><svg></svg></div></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    arm();
    await frames();
    expect(slot()).toBeNull();
  });

  it("does not take a section whose chart is not drawn for a paragraph that is not its empty state", async () => {
    page(
      "/indicators",
      `<section aria-label="Coûts cumulés"><p>Une note</p><div role="img"><svg></svg></div></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    arm();
    await frames();
    expect(slot()).toBeNull();
    page("/indicators", `<section aria-label="Coûts cumulés"><p>Une note</p></section>`);
    hydrate(document.querySelector("section") as Element);
    await frames();
    expect(slot()).toBeNull();
  });

  it("does not take a section of the screen before, nor one outside the main", async () => {
    page(
      "/planning",
      `<section aria-label="Coûts cumulés"><p>Rien à tracer : aucune ligne.</p></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    arm();
    await frames();
    expect(slot()).toBeNull();
    page("/indicators", "");
    document.body.insertAdjacentHTML(
      "beforeend",
      `<section aria-label="Coûts cumulés"><p>Rien à tracer : aucune ligne.</p></section>`,
    );
    hydrate(document.querySelector("section") as Element);
    await frames();
    expect(slot()).toBeNull();
  });
});
