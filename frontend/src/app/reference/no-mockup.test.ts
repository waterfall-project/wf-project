// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The mock-up of the reference screens is gone (US-0900, #512): no page of `app/reference/`, no
 * component of `components/reference/` names the notice of the mock-up (`MockupNotice`, its module
 * or its catalogue namespace), and no help of FBS-3 speaks of the fake back — the screens are wired
 * to the service of the reference data, and a success there is what the service kept, read anew.
 * The sources are read, as the other guards of the front read them; the paths against the service
 * play the screens (`e2e/service/reference-manager.spec.ts`). The tests of a screen, which name
 * the notice to assert its absence, are left out.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..", "..");
const HELP = join(SOURCES, "..", "help", "fr");

/** What names the notice of the mock-up in a source: the component, its module, its namespace. */
const NOTICE = /MockupNotice|mockup-notice|useTranslations\(\s*["']mockup["']|\bmockup\./;
/** What a help says of the fake back, in the words the French documentation uses for it. */
const FAKE_BACK = /faux back|service simulé|maquette|Prism|MockupNotice/i;

/** The sources of a directory of `src/`, tests left out, as paths relative to `src/`. */
function sources(directory: string): string[] {
  return readdirSync(join(SOURCES, directory), { recursive: true, withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && /\.tsx?$/.test(entry.name) && !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** The helps of the settings of the application (FBS-3), as paths. */
function helps(): string[] {
  return readdirSync(HELP)
    .filter((name) => /^FBS-3.*\.md$/.test(name))
    .map((name) => join(HELP, name));
}

describe("the reference screens, wired to the service (#512)", () => {
  it("finds the sources and the helps it guards, so that an empty search proves nothing", () => {
    expect(sources(join("app", "reference")).length).toBeGreaterThan(5);
    expect(sources(join("components", "reference")).length).toBeGreaterThan(20);
    expect(helps().length).toBeGreaterThanOrEqual(10);
  });

  it("names the notice of the mock-up in no page of app/reference nor component of components/reference", () => {
    const naming = [
      ...sources(join("app", "reference")),
      ...sources(join("components", "reference")),
    ]
      .filter((file) => NOTICE.test(readFileSync(file, "utf-8")))
      .map((file) => file.slice(SOURCES.length + 1));
    expect(naming).toEqual([]);
  });

  it("says nothing of the fake back in the helps of FBS-3", () => {
    const speaking = helps()
      .filter((file) => FAKE_BACK.test(readFileSync(file, "utf-8")))
      .map((file) => file.slice(HELP.length + 1));
    expect(speaking).toEqual([]);
  });

  it("finds the notice and the fake back where they are named", () => {
    expect(NOTICE.test('import { MockupNotice } from "@/components/shell/mockup-notice";')).toBe(
      true,
    );
    expect(NOTICE.test('const t = useTranslations("mockup");')).toBe(true);
    expect(NOTICE.test('const t = useTranslations("reference");')).toBe(false);
    expect(FAKE_BACK.test("Ces données viennent du faux back.")).toBe(true);
    expect(FAKE_BACK.test("Le service conserve ce que vous saisissez.")).toBe(false);
  });
});
