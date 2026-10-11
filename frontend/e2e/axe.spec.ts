// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The audit of axe of the accessibility of the screens (`axe.ts`), proved on pages written for it:
 * a contrast axe measured and left « incomplete » is a breach, a text it could not measure is
 * counted under its reason. A tool of the harness, which proves no requirement itself.
 */
import { expect, type Page, test } from "@playwright/test";

import { axeAudit } from "./axe";

/** A page of its own, on a white background, in the window of the harness. */
async function write(page: Page, body: string): Promise<void> {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.setContent(
    `<!doctype html><html lang="fr"><head><title>Essai</title></head><body style="background: rgb(255, 255, 255)"><main>${body}</main></body></html>`,
  );
}

test("takes a character, or a text the colour of its background, too pale for AA for a breach", async ({
  page,
}) => {
  await write(
    page,
    `<p style="color: rgb(148, 148, 148)">6</p>
     <p style="color: rgb(255, 255, 255)">Blanc sur blanc</p>
     <p style="color: rgb(0, 0, 0)">Noir sur blanc</p>`,
  );
  const { breaches } = await axeAudit(page);
  expect(breaches).toEqual([
    {
      rule: "color-contrast, left incomplete by axe",
      nodes: [
        expect.stringMatching(/>6<\/p> \(#949494 on #ffffff: 3\.0\d*, shortTextContent\)$/),
        expect.stringMatching(/Blanc sur blanc<\/p> \(#ffffff on #ffffff: 1, equalRatio\)$/),
      ],
    },
  ]);
});

test("counts a text it could not measure under its reason, and no breach: pushed out of the box that scrolls it, a character over a picture, in a figure apart", async ({
  page,
}) => {
  // Half below the edge of a box with a background, which scrolls down and hides across: axe
  // cannot tell the background of what it does not see.
  await write(
    page,
    `<div role="group" aria-label="Boîte" tabindex="0"
          style="overflow-x: hidden; overflow-y: auto; height: 40px; background: rgb(250, 250, 250)">
       <div style="height: 30px"></div>
       <p style="margin: 0; line-height: 20px; color: rgb(0, 0, 0)">Un texte plus bas</p>
       <div style="height: 60px"></div>
     </div>
     <p style="color: rgb(0, 0, 0); background-image: linear-gradient(rgb(255, 255, 255), rgb(240, 240, 240))">7</p>
     <figure aria-label="Courbe">
       <p style="color: rgb(0, 0, 0); background-image: linear-gradient(rgb(255, 255, 255), rgb(240, 240, 240))">8</p>
     </figure>`,
  );
  const { breaches, unmeasured } = await axeAudit(page);
  expect(breaches).toEqual([]);
  expect(unmeasured).toEqual({
    elmPartiallyObscured: 1,
    "shortTextContent, colours unmeasured": 1,
    "shortTextContent, colours unmeasured in a figure": 1,
  });
});
