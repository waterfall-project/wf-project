// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * What the screens of Waterfall leave to the identity provider (US-0350): the password, which no
 * screen asks for, shows nor lets type — the link that sets it, which `createPasswordSetupLink`
 * gives, being the one element of authentication a screen may show (WF-ADM-0140) —, and the
 * directory, which no screen sets up: the administrator federates it in the console of Keycloak
 * (WF-ADM-0180). A screen is made of the modules of `src/`, its texts of the catalogues, and its
 * reads and writes of the operations of the contract: each is read here for what would make one.
 * The paths against the service see the screens a person reaches once signed in
 * (`e2e/service/sign-in.spec.ts`, `e2e/service/password.spec.ts`).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

const SOURCES = join(import.meta.dirname, "..");
const APP = import.meta.dirname;

/** Every module of the front: the `.ts` and `.tsx` of `src/`, tests and generated left out. */
function modules(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        /\.tsx?$/.test(entry.name) &&
        !entry.name.endsWith(".d.ts") &&
        !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name))
    .filter((path) => !relative(SOURCES, path).startsWith(`api${sep}generated`));
}

/** The routes of the screens: the directories of `src/app` that hold a page, from the root. */
function screenRoutes(): string[] {
  return readdirSync(APP, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name === "page.tsx")
    .map((entry) => `/${relative(APP, entry.parentPath).split(sep).join("/")}`);
}

/** Every text of a catalogue, under the path of its key. */
function texts(catalogue: unknown, path = ""): [string, string][] {
  if (typeof catalogue === "string") {
    return [[path, catalogue]];
  }
  return Object.entries(catalogue as Record<string, unknown>).flatMap(([key, value]) =>
    texts(value, path === "" ? key : `${path}.${key}`),
  );
}

/** The paths of the operations of the contract, as the client of the front is generated from it. */
function operationPaths(): string[] {
  const schema = readFileSync(join(SOURCES, "api", "generated", "schema.d.ts"), "utf8");
  return [...schema.matchAll(/^ {4}"(\/[^"]*)": \{$/gm)].map(([, path = ""]) => path);
}

// A field that lets a password be typed, or offers one the browser kept.
const PASSWORD_FIELD =
  /type[\s=:{]*["'`]password["'`]|autoComplete[\s=:{]*["'`](?:current|new)-password/i;
// The texts of a password, in either language.
const PASSWORD_TEXT = /mot de passe|password/i;
// The one element of authentication a screen may show: the link that sets a password, and the email
// that carries it again to its holder, whom the administrator may have it sent to (`resendInvitation`,
// WF-ADM-0140). The texts of that email are named by their exact keys, never by a pattern that a
// text about a password could slip through.
const SETUP_LINK = new RegExp(
  [
    "password_link",
    "password-link",
    String.raw`^admin\.users\.resend_invitation\.command$`,
    String.raw`^admin\.users\.resent$`,
    String.raw`^commands\.resend_invitation\.help$`,
    String.raw`^columns\.users\.resend_invitation\.help$`,
    // The command of the account that has it sent again (`UserCommand`, A-04).
    String.raw`^enums\.UserCommand\.resend_invitation$`,
  ].join("|"),
);
// What would set up a directory, or the federation of one: LDAP, its binding, the provider itself.
const DIRECTORY_SETUP =
  /ldap|federat|f[ée]d[ée]ration|bind dn|identity[-_]provider|realm|keycloak/i;

describe("the password, which the identity provider asks for", () => {
  it("is asked for, shown and typed on no screen of Waterfall: no field of a password, no text but the link that sets it and the email that carries it again [WF-ADM-0140-A]", () => {
    const fields = modules().filter((path) => PASSWORD_FIELD.test(readFileSync(path, "utf8")));
    expect(fields.map((path) => relative(SOURCES, path))).toEqual([]);
    for (const [language, catalogue] of Object.entries(CATALOGUES)) {
      const said = texts(catalogue).filter(
        ([key, text]) => PASSWORD_TEXT.test(text) && !SETUP_LINK.test(key),
      );
      expect(said, language).toEqual([]);
    }
    expect(screenRoutes().filter((route) => PASSWORD_TEXT.test(route))).toEqual([]);
  });

  it("is reached by the link that sets it alone, among all the operations of the contract [WF-ADM-0140-A]", () => {
    expect(operationPaths().filter((path) => PASSWORD_TEXT.test(path))).toEqual([
      "/users/{user_id}/password-link",
    ]);
  });
});

describe("the directory, which the console of the identity provider federates", () => {
  it("is set up on no screen of Waterfall: no screen, no text, no operation of the contract for it [WF-ADM-0180-A]", () => {
    expect(screenRoutes().filter((route) => DIRECTORY_SETUP.test(route))).toEqual([]);
    expect(operationPaths().filter((path) => DIRECTORY_SETUP.test(path))).toEqual([]);
    for (const [language, catalogue] of Object.entries(CATALOGUES)) {
      const said = texts(catalogue).filter(([, text]) => DIRECTORY_SETUP.test(text));
      expect(said, language).toEqual([]);
    }
  });

  it("is named on the screens only as the origin of an account, read from the identity provider [WF-ADM-0180-A]", () => {
    const named = texts(CATALOGUES.fr).filter(([, text]) => /annuaire/i.test(text));
    expect(named.map(([key]) => key).every((key) => /origin/i.test(key))).toBe(true);
    expect(named.length).toBeGreaterThan(0);
  });
});
