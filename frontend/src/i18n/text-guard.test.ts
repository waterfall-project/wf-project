// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The rules of eslint.config.mjs against text written in the code, tried on trapped
 * snippets: text meant for the user, in JSX or in an attribute a user reads, must be
 * refused as an error — which fails `make lint-front`, and so the chain; text read from the
 * catalogues must pass. The network guard shares no-restricted-syntax with them, whose
 * options a block replaces whole: both must hold in the same file.
 *
 * A snippet is linted as the text of an existing file of the project, so that the typed
 * rules find it; nothing is written to the disk.
 */
import { join } from "node:path";

import { ESLint, type Linter } from "eslint";
import tseslint from "typescript-eslint";
import { beforeAll, describe, expect, it } from "vitest";

const ROOT = join(import.meta.dirname, "../..");

// A server component and a client component of the project, both in TSX.
const PAGE = "src/app/page.tsx";
const COMPONENT = "src/components/shell/language-selector.tsx";

const TEXT = "Write the text in the catalogues of messages/, and read it with next-intl.";
const NETWORK = "Call the API through the generated client, src/api/client.ts.";

// The rules the text guard is made of.
const GUARD = new Set(["react/jsx-no-literals", "no-restricted-syntax"]);

const HEADER = 'import Image from "next/image";\nimport { useTranslations } from "next-intl";\n';

/** A component around some JSX, reading its texts from the catalogues. */
function component(jsx: string, directive = ""): string {
  return [
    directive,
    HEADER,
    "/** A component. */",
    "export function Trap({ ok }: { ok: boolean }) {",
    '  const t = useTranslations("app");',
    `  return ${jsx};`,
    "}",
  ].join("\n");
}

// Text in JSX, however it is written.
const IN_JSX: readonly string[] = [
  "<p>Bonjour</p>",
  '<p>{"Bonjour"}</p>',
  "<p>{`Bonjour`}</p>",
  '<p>{ok ? "Oui" : t("name")}</p>',
  '<p>\n    {t("name")} :\n  </p>',
  '<p>{"Total : " + t("name")}</p>',
  '<p>{t("name") + " (" + t("name") + ")"}</p>',
];

// An attribute a user reads, written as a literal, or as a literal in one of its branches.
const IN_ATTRIBUTES: readonly string[] = [
  '<button type="button" aria-label="Fermer" />',
  '<abbr title="Fin à début">{t("name")}</abbr>',
  '<img src="/logo.svg" alt="Waterfall" />',
  '<input placeholder="Rechercher" />',
  '<input placeholder={"Rechercher"} />',
  "<input placeholder={`Rechercher`} />",
  '<button type="button" aria-label={ok ? t("name") : "Fermer"} />',
  '<button type="button" aria-label={ok && "Fermer"} />',
  '<button type="button" title={`${t("name")} (1)`} />',
  '<button type="button" aria-label={"Fermer " + t("name")} />',
  '<div role="slider" aria-valuenow={3} aria-valuetext="trois sur dix" />',
  '<section aria-roledescription="diapositive" />',
  '<button type="button" aria-description="Ferme la fenêtre" />',
  '<div role="textbox" aria-placeholder="Rechercher" />',
  '<select><option value="fr" label="Français" /></select>',
  '<input type="submit" value="Envoyer" />',
  '<input type="reset" value={"Effacer"} />',
  '<input type="button" value={ok ? "Oui" : t("name")} />',
];

// What a component may write: texts read from the catalogues, attributes no one reads, an
// empty alt for a decorative image, and values chosen by code rather than read.
const ALLOWED: readonly string[] = [
  '<p>{t("name")}</p>',
  '<button type="button" className="primary" aria-label={t("name")} />',
  '<img src="/logo.svg" alt="" />',
  '<abbr title={t(ok ? "name" : "name")}>{t("name")}</abbr>',
  '<p>\n    {t("name")}\n  </p>',
  '<p>{t("name").length + 1}</p>',
  '<input type="text" value="fr" readOnly />',
  '<Image src="/logo.svg" alt="" width={10} height={10} placeholder="blur" />',
  '<Image src="/logo.svg" alt="" width={10} height={10} placeholder="empty" />',
  '<Image src="/logo.svg" alt="" width={10} height={10} placeholder="data:image/png;base64,iVBORw0KGgo=" />',
];

let eslint: ESLint;
let actions: ESLint;

beforeAll(() => {
  eslint = new ESLint({ cwd: ROOT });
  actions = new ESLint({ cwd: ROOT, overrideConfig: tseslint.configs.disableTypeChecked });
});

/** The messages of the text guard on a snippet written in a file, and the fatal ones. */
async function lint(code: string, file = PAGE, linter = eslint): Promise<Linter.LintMessage[]> {
  const [result] = await linter.lintText(code, { filePath: file });
  const messages = result?.messages ?? [];
  return messages.filter((m) => m.fatal === true || GUARD.has(m.ruleId ?? ""));
}

/** The rule, severity and message of each finding. */
function findings(messages: readonly Linter.LintMessage[]): [string | null, number, string][] {
  return messages.map((m) => [m.ruleId, m.severity, m.message]);
}

describe("the text guard", { timeout: 60_000 }, () => {
  it.each(IN_JSX)(
    "refuses the text %j written in the JSX of a component [WF-QUA-0070-A]",
    async (jsx) => {
      const messages = await lint(component(jsx));
      // Severity 2 is an error: it fails `make lint-front`, and so the chain. The text of
      // JSX is react/jsx-no-literals'; a branch of a child, the selectors of TEXT_SYNTAX.
      expect(messages.map((m) => [m.fatal ?? false, m.severity])).toContainEqual([false, 2]);
      expect(messages.map((m) => m.message)).toContainEqual(
        expect.stringMatching(
          /^(Strings not allowed in JSX files|Write the text in the catalogues)/,
        ),
      );
    },
  );

  it.each(IN_ATTRIBUTES)(
    "refuses the attribute in %j, written in the code [WF-QUA-0070-A]",
    async (jsx) => {
      expect(findings(await lint(component(jsx)))).toContainEqual([
        "no-restricted-syntax",
        2,
        TEXT,
      ]);
    },
  );

  it("refuses them in a client component too [WF-QUA-0070-A]", async () => {
    const code = component('<p title="Langue">Langue</p>', '"use client";');
    const rules = (await lint(code, COMPONENT)).map((m) => m.ruleId);
    expect(rules).toEqual(
      expect.arrayContaining(["react/jsx-no-literals", "no-restricted-syntax"]),
    );
  });

  it.each(ALLOWED)("lets %j through", async (jsx) => {
    expect(await lint(component(jsx))).toEqual([]);
  });

  it("holds beside the network guard, in the same file [WF-QUA-0070-A]", async () => {
    const code = [
      'export const got = await import("got");',
      component('<button type="button" aria-label="Fermer" />'),
    ].join("\n");
    const messages = findings(await lint(code));
    expect(messages).toContainEqual(["no-restricted-syntax", 2, TEXT]);
    expect(messages).toContainEqual(["no-restricted-syntax", 2, NETWORK]);
  });

  it("holds in the server actions, whose block redefines the rule [WF-QUA-0070-A]", async () => {
    const code = [
      '"use server";',
      'export const got = await import("got");',
      '/** A trap. */\nexport async function trap() {\n  return <input placeholder="Nom" />;\n}',
    ].join("\n");
    const messages = findings(await lint(code, "src/api/actions/trap.tsx", actions));
    expect(messages).toContainEqual(["no-restricted-syntax", 2, TEXT]);
    expect(messages).toContainEqual(["no-restricted-syntax", 2, NETWORK]);
  });
});
