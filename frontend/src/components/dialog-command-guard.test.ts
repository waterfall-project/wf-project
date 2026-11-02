// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the commands that open a dialog (WF-IHM-0100-A, US-0710/L1, #1558): the harness of
 * what a gesture opens (`e2e/opened.ts`) finds a dialog by the command that says it opens one,
 * `aria-haspopup="dialog"` — the dialogs of the front open by a state, not by a `DialogTrigger`,
 * which would say it. A command that opens a dialog and does not say so escapes the harness
 * without a sound. So a source that renders a `<Dialog` or an `<AlertDialog` driven by an `open`
 * must hold a command that says `aria-haspopup="dialog"`, or be listed below with the reason the
 * dialog is opened otherwise: by a gesture that is no button, or by a command of another file.
 *
 * The reading is of the text: a tag at the head of a line, an `open` among its first lines. A
 * listed source that no longer needs its entry is reported as well, so that the list stays true.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..");
const PRIMITIVES = join(SOURCES, "components", "ui");
const SAYS = 'aria-haspopup="dialog"';

/** The sources whose dialog is not opened by a command of their own, each with its reason. */
const OTHERWISE_OPENED: Readonly<Record<string, string>> = {
  "components/grid/structure-gestures.tsx":
    "TimelineForm and GestureDialog are opened by gestures of the grid, not by a button of this source",
  "components/grid/paste-dialog.tsx": "the paste of a block is opened by Ctrl+V, not by a button",
  "components/reference/reference-form.tsx":
    "the form is mounted by the commands of reference/commands.tsx and settings-forms.tsx, which bear aria-haspopup",
  "components/admin/user-dialogs.tsx":
    "the dialogs are mounted by the commands of user-commands.tsx and user-cells.tsx, which bear aria-haspopup",
  "components/admin/restore-dialog.tsx":
    "the dialog is mounted by the command of backup-commands.tsx, which bears aria-haspopup",
};

function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return path === PRIMITIVES ? [] : sources(path);
    }
    return entry.name.endsWith(".tsx") && !entry.name.includes(".test.") ? [path] : [];
  });
}

/** Whether the source renders a dialog driven by an `open`. */
function rendersDialog(text: string): boolean {
  const lines = text.split("\n");
  return lines.some(
    (line, index) =>
      /^\s*<(Dialog|AlertDialog)\b/.test(line) &&
      lines.slice(index, index + 4).some((near) => /^\s*open(=|\s*$)/.test(near)),
  );
}

describe("the commands that open a dialog", () => {
  const found = sources(SOURCES)
    .map((path) => ({ name: relative(SOURCES, path), text: readFileSync(path, "utf8") }))
    .filter(({ text }) => rendersDialog(text));

  it("a source that renders a dialog says it opens one, or is listed as opened otherwise [WF-IHM-0100-A]", () => {
    const silent = found
      .filter(({ name, text }) => !text.includes(SAYS) && !(name in OTHERWISE_OPENED))
      .map(({ name }) => name);
    expect(silent).toEqual([]);
  });

  it("the list holds only sources that render a dialog and say nothing [WF-IHM-0100-A]", () => {
    const stale = Object.keys(OTHERWISE_OPENED).filter(
      (name) => !found.some((source) => source.name === name && !source.text.includes(SAYS)),
    );
    expect(stale).toEqual([]);
  });
});
