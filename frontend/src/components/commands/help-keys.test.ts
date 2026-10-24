// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the helps of the commands (US-0580/L2, #1137): each `commands.<command>.help` of the
 * catalogue is read by a component, and its tooltip says it. A help nothing reads is a sentence
 * written for no command — the command it was written for stayed without a tooltip, or is not
 * a command of the front: it is wired or removed from both catalogues.
 *
 * A key is read when a source names it whole (`"modify.help"`, `commands.workload.help`), or when a
 * source builds the key from the name of the command (`` `${command}.help` ``) and names the command
 * in a string. The commands of a project and of a revision, whose keys the sources build from the
 * contract, are read from the tables that build them: the exits, the imports, and the commands the
 * list of a revision presents itself.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import { isListed } from "@/components/commands/object-commands";
import { EXIT_STATES } from "@/components/commands/exits";
import { IMPORT_COMMAND } from "@/components/exchanges/offers";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";

const SOURCES = join(import.meta.dirname, "..", "..");

/** The sources of the front that run: tests, generated client and fixtures left out. */
function sources(): string {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        /\.tsx?$/.test(entry.name) &&
        !entry.name.includes(".test.") &&
        !entry.parentPath.includes(join("src", "api", "generated")) &&
        !entry.parentPath.includes(join("src", "test")),
    )
    .map((entry) => readFileSync(join(entry.parentPath, entry.name), "utf8"))
    .join("\n");
}

type Helps = Readonly<Record<string, unknown>>;

/** The paths below `commands` of the keys that end in a `help`, `modify.help`, `project.update.help`. */
function helpPaths(commands: Helps, prefix = ""): string[] {
  return Object.entries(commands).flatMap(([name, value]) => {
    if (typeof value !== "object" || value === null) {
      return [];
    }
    const record = value as Helps;
    return "help" in record ? [`${prefix}${name}`] : helpPaths(record, `${prefix}${name}.`);
  });
}

/** Whether a source names the key whole, or names the command where it builds the key from it. */
function isRead(path: string, text: string): boolean {
  const [group, command] = path.split(".");
  if (command !== undefined && (group === "project" || group === "revision")) {
    const listed: readonly string[] =
      group === "project"
        ? [...Object.keys(EXIT_STATES), ...Object.values(IMPORT_COMMAND)]
        : Object.keys(REVISION_COMMAND_ICONS).filter((name) => isListed(name as never));
    return listed.includes(command) || text.includes(`${path}.help`);
  }
  const whole = new RegExp(`(?:["'\`]|commands\\.)${path.replace(".", "\\.")}\\.help`);
  const built = new RegExp(`["']${path}["']`);
  return whole.test(text) || (text.includes("}.help") && built.test(text));
}

describe("the helps of the commands of the catalogue", () => {
  const text = sources();

  it.each([
    ["fr", fr],
    ["en", en],
  ])("in %s, every help is read by a component", (_language, catalogue) => {
    const unread = helpPaths(catalogue.commands as Helps).filter((path) => !isRead(path, text));
    expect(unread).toEqual([]);
  });

  it("holds the same helps in both languages", () => {
    expect(helpPaths(en.commands as Helps).sort()).toEqual(helpPaths(fr.commands as Helps).sort());
  });
});
