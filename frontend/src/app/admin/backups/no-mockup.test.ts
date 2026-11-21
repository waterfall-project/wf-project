// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the backups is wired to the service (US-2910, #512, #519, #588): no source of its
 * page nor of its components names the notice of the mock-up (`MockupNotice`, its module or its
 * catalogue namespace), and its help (FBS-1.4, in French and in English) speaks of no fake back. The sources are read, as the
 * guard of the reference screens does (`app/reference/no-mockup.test.ts`); the paths against the
 * service play the screen (`e2e/service/backup-schedule.spec.ts`). Tests, which name the notice to
 * assert its absence, are left out.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..", "..", "..");
const NOTICE = /MockupNotice|mockup-notice|useTranslations\(\s*["']mockup["']|\bmockup\./;
const FAKE_BACK = /faux back|service simulé|maquette|fake back|mock-?up|Prism|MockupNotice/i;

/** The sources of a directory of `src/` that keep a name, tests left out, as paths. */
function directory(path: string, keep: (name: string) => boolean): string[] {
  return readdirSync(join(SOURCES, path), { withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && /\.tsx?$/.test(entry.name) && !entry.name.includes(".test."),
    )
    .filter((entry) => keep(entry.name))
    .map((entry) => join(SOURCES, path, entry.name));
}

/** The sources of the screen: its page and the components `backup-*` of the administration. */
function sources(): string[] {
  return [
    ...directory(join("app", "admin", "backups"), () => true),
    ...directory(join("components", "admin"), (name) => name.startsWith("backup-")),
  ];
}

describe("the screen of the backups, wired to the service (US-2910)", () => {
  it("finds the sources it guards, so that an empty search proves nothing", () => {
    expect(sources().length).toBeGreaterThanOrEqual(6);
  });

  it("names the notice of the mock-up in none of them [US-2910]", () => {
    expect(
      sources()
        .filter((file) => NOTICE.test(readFileSync(file, "utf-8")))
        .map((file) => file.slice(SOURCES.length + 1)),
    ).toEqual([]);
  });

  it.each(["fr", "en"])(
    "says nothing of the fake back in its help, in %s [US-2910]",
    (language) => {
      const help = readFileSync(join(SOURCES, "..", "help", language, "FBS-1.4.md"), "utf-8");
      expect(FAKE_BACK.test(help)).toBe(false);
    },
  );
});
