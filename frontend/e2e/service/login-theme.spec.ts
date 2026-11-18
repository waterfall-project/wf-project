// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The login pages in the charter of the front (EP-25, US-2190): the theme `waterfall` of the
 * realm, and of the external provider of development, takes the primary colour, the pills and the
 * background of the charter in both modes, and keeps the contrast AA — axe, and the borders of the
 * controls and the error text, measured. Played with the workstation light, then dark: the theme
 * follows `prefers-color-scheme`. By measures of what the browser paints, never by captures.
 */
import { expect, type Page, test } from "@playwright/test";

import { axeAudit } from "../axe";
import { heldToTheContract } from "./contract";
import { EXTERNAL, expectSignInPage, REALM, under } from "./realm";

heldToTheContract();

/** The tokens of the charter (`frontend/src/theme/globals.css`), as the browser computes them. */
const CHARTER = {
  light: { background: "rgb(243, 245, 248)", primary: "rgb(20, 35, 59)" },
  dark: { background: "rgb(11, 17, 27)", primary: "rgb(214, 224, 238)" },
} as const;

/** The least contrast of a border of a control that must be seen, and of a text (WCAG 1.4.11, 1.4.3). */
const BORDER = 3;
const TEXT = 4.5;

/** A colour as `getComputedStyle` writes it: `rgb(r, g, b)`, opaque. */
function channels(colour: string): [number, number, number] {
  const found = /^rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)$/.exec(colour);
  if (found === null || (found[4] !== undefined && Number(found[4]) !== 1)) {
    throw new Error(`a colour that is not opaque: ${colour}`);
  }
  return [Number(found[1]), Number(found[2]), Number(found[3])];
}

function luminance(colour: string): number {
  const [r, g, b] = channels(colour).map((value) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(one: string, other: string): number {
  const [high, low] = [luminance(one), luminance(other)].sort((a, b) => b - a) as [number, number];
  return (high + 0.05) / (low + 0.05);
}

/** The borders asked 3:1, by selector, on the card: the fields, the language, the secondary and external buttons. */
const BORDERED = [
  ".pf-v5-c-form-control",
  ".pf-v5-c-login__main-header-utilities .pf-v5-c-form-control",
  ".pf-v5-c-button.pf-m-secondary",
  "#kc-social-providers .pf-v5-c-button",
  ".pf-v5-c-input-group .pf-v5-c-button.pf-m-control",
];

/** The texts of an error, which ask 4.5:1 on the card. */
const ERRORS = [
  ".pf-v5-c-helper-text__item.pf-m-error",
  ".pf-v5-c-form__helper-text",
  ".pf-v5-c-alert.pf-m-danger .pf-v5-c-alert__title",
  ".pf-v5-c-alert.pf-m-info .pf-v5-c-alert__title",
  ".pf-v5-c-alert.pf-m-success .pf-v5-c-alert__title",
  ".pf-v5-c-alert.pf-m-warning .pf-v5-c-alert__title",
];

interface Painted {
  readonly selector: string;
  readonly border: string;
  readonly color: string;
}

/** What the page paints for the selectors: the borders and the colours of each visible element. */
async function painted(page: Page, selectors: readonly string[]): Promise<Painted[]> {
  return page.evaluate((asked) => {
    const seen: { selector: string; border: string; color: string }[] = [];
    for (const selector of asked) {
      for (const element of document.querySelectorAll(selector)) {
        const box = element.getBoundingClientRect();
        if (box.width === 0 || box.height === 0) {
          continue;
        }
        const style = getComputedStyle(element);
        seen.push({ selector, border: style.borderTopColor, color: style.color });
      }
    }
    return seen;
  }, selectors);
}

/** The audit and the measures of one page of the theme, in the mode of the workstation. */
async function judge(page: Page, name: string, expected: readonly string[] = []): Promise<void> {
  const card = await page
    .locator(".pf-v5-c-login__main")
    .evaluate((element) => getComputedStyle(element).backgroundColor);
  const { breaches } = await axeAudit(page);
  expect(breaches, `${name}: the rules of axe for WCAG A and AA`).toEqual([]);
  const borders = await painted(page, BORDERED);
  for (const each of borders) {
    expect(
      contrast(each.border, card),
      `${name}: the border of ${each.selector} on the card`,
    ).toBeGreaterThanOrEqual(BORDER);
  }
  for (const selector of expected) {
    expect(
      borders.some((each) => each.selector === selector),
      `${name}: a ${selector} to measure`,
    ).toBe(true);
  }
  for (const each of await painted(page, ERRORS)) {
    expect(
      contrast(each.color, card),
      `${name}: the text of ${each.selector} on the card`,
    ).toBeGreaterThanOrEqual(TEXT);
  }
}

/** An alert of each severity Keycloak writes, as its template writes them, over the form. */
async function alerts(page: Page): Promise<void> {
  await page.evaluate(() => {
    const kinds = [
      ["info", "fa-info-circle", "Information"],
      ["success", "fa-check-circle", "Succès"],
      ["warning", "fa-exclamation-triangle", "Avertissement"],
    ] as const;
    const body = document.querySelector(".pf-v5-c-login__main-body") ?? document.body;
    for (const [kind, icon, text] of kinds) {
      const alert = document.createElement("div");
      alert.className = `pf-v5-c-alert pf-m-inline pf-m-${kind}`;
      alert.innerHTML = `<div class="pf-v5-c-alert__icon"><i class="fas fa-fw ${icon}" aria-hidden="true"></i></div><h4 class="pf-v5-c-alert__title"><span class="pf-v5-screen-reader">${text} :</span> Un message ${kind}</h4>`;
      body.prepend(alert);
    }
  });
}

for (const mode of ["light", "dark"] as const) {
  test.describe(`a workstation in ${mode} mode, on the login pages`, () => {
    test.use({ colorScheme: mode, locale: "fr-FR", ignoreHTTPSErrors: true });

    test(`US-2190: the sign-in page of the realm, a field in error, the forgotten password and the page of the external provider, in ${mode} mode, take the charter — primary, pills, background — and keep the contrast AA: axe, the borders of the controls at 3:1 and the error text at 4.5:1 measured`, async ({
      page,
    }) => {
      test.setTimeout(90_000);
      await page.goto("/login");
      await expectSignInPage(page);
      await expect(page.locator("html")).toHaveClass(
        mode === "dark" ? /pf-v5-theme-dark/ : /^((?!pf-v5-theme-dark).)*$/,
      );

      // The first criterion: the primary colour, the pills, the background of the charter.
      await expect(page.locator("body")).toHaveCSS("background-color", CHARTER[mode].background);
      const primary = page.getByRole("button", { name: "Connexion", exact: true });
      await expect(primary).toHaveCSS("background-color", CHARTER[mode].primary);
      const radius = await primary.evaluate((button) => getComputedStyle(button).borderRadius);
      expect(Number.parseFloat(radius)).toBeGreaterThanOrEqual(1000);
      const field = page.locator("input[name=username]").locator("xpath=..");
      expect(
        Number.parseFloat(await field.evaluate((box) => getComputedStyle(box).borderRadius)),
      ).toBeGreaterThanOrEqual(1000);

      await judge(page, "the sign-in page", [
        ".pf-v5-c-form-control",
        ".pf-v5-c-login__main-header-utilities .pf-v5-c-form-control",
        "#kc-social-providers .pf-v5-c-button",
      ]);

      // The states: a disabled primary button is not the primary colour; the alerts of every
      // severity, whose icons Keycloak writes, keep the contrast.
      await primary.evaluate((button) => {
        button.setAttribute("disabled", "");
      });
      expect(
        contrast(
          await primary.evaluate((button) => getComputedStyle(button).backgroundColor),
          CHARTER[mode].primary,
        ),
        "the disabled primary button differs from the enabled one",
      ).toBeGreaterThan(1.05);
      await primary.evaluate((button) => {
        button.removeAttribute("disabled");
      });
      await alerts(page);
      await judge(page, "the alerts of every severity");

      // A field in error: a wrong password.
      await page.goto("/login");
      await expectSignInPage(page);
      await page.getByLabel("Courriel").or(page.getByLabel("Email")).fill("nobody@example.test");
      await page
        .getByLabel("Mot de passe", { exact: true })
        .or(page.getByLabel("Password", { exact: true }))
        .fill("not-the-password");
      await page.getByRole("button", { name: /^(Connexion|Sign In)$/ }).click();
      await expect(page.locator(".pf-v5-c-alert.pf-m-danger, .pf-m-error").first()).toBeVisible();
      await judge(page, "the sign-in page in error", [".pf-v5-c-form-control"]);

      // The forgotten password, and its answer.
      await page.getByRole("link", { name: /oublié|Forgot/i }).click();
      await expect(page).toHaveURL(under(`${REALM}/login-actions/reset-credentials`));
      await judge(page, "the forgotten password", [
        ".pf-v5-c-form-control",
        ".pf-v5-c-login__main-header-utilities .pf-v5-c-form-control",
        ".pf-v5-c-button.pf-m-secondary",
      ]);
      await page.locator("input[name=username]").fill("nobody@example.test");
      await page.locator("input[name=username]").press("Enter");
      await expect(page.locator(".pf-v5-c-alert")).toBeVisible();
      await judge(page, "the forgotten password, answered");

      // The external provider of development, in its own realm, same theme (third criterion).
      await page.goto("/login");
      await expectSignInPage(page);
      await page.getByRole("link", { name: EXTERNAL.provider ?? "" }).click();
      await expect(page).toHaveURL(/\/realms\/external\//);
      await expect(page.locator("body")).toHaveCSS("background-color", CHARTER[mode].background);
      await expect(page.getByRole("button", { name: /^(Connexion|Sign In)$/ })).toHaveCSS(
        "background-color",
        CHARTER[mode].primary,
      );
      await judge(page, "the page of the external provider", [".pf-v5-c-form-control"]);
      await page.locator("input[name=username]").fill("nobody");
      await page.locator("input[name=password]").fill("not-the-password");
      await page.getByRole("button", { name: /^(Connexion|Sign In)$/ }).click();
      await expect(page.locator(".pf-v5-c-alert.pf-m-danger, .pf-m-error").first()).toBeVisible();
      await judge(page, "the page of the external provider, in error");
    });
  });
}
