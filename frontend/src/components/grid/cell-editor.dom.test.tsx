// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { CellEditor } from "./cell-editor";
import type { EntryKind } from "./columns";

// The entry of a cell, opened on its value: the whole value is selected, what is typed replaces it,
// and a key of the cursor lifts the selection to correct it (WF-IHM-0040-A, #3122). Opened on a
// character typed, the caret stays after it.

const KINDS: readonly {
  readonly name: string;
  readonly kind: EntryKind;
  readonly text: string;
}[] = [
  { name: "text", kind: { type: "text", maxLength: undefined }, text: "Câblage des armoires" },
  { name: "number", kind: { type: "decimal", nullable: false }, text: "1 234,5" },
  { name: "date", kind: { type: "date" }, text: "31/12/2026" },
];

/** The entry of a cell, in French, that nothing waits on. */
function entry(kind: EntryKind, text: string, typed?: string) {
  const onValidate = vi.fn(() => true);
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <CellEditor
        kind={kind}
        label="Champ"
        text={text}
        typed={typed}
        invalid={undefined}
        onValidate={onValidate}
        onAbandon={vi.fn()}
      />
    </NextIntlClientProvider>,
  );
  return { field: screen.getByRole<HTMLInputElement>("textbox", { name: "Champ" }), onValidate };
}

describe("the entry of a cell, opened on its value", () => {
  it.each(KINDS)(
    "selects the whole value of a $name, and what is typed replaces it [WF-IHM-0040-A]",
    async ({ kind, text }) => {
      const { field, onValidate } = entry(kind, text);
      expect(field).toHaveFocus();
      expect(field.selectionStart).toBe(0);
      expect(field.selectionEnd).toBe(text.length);
      await userEvent.keyboard("42{Enter}");
      expect(onValidate).toHaveBeenCalledWith("42", "down");
    },
  );

  it.each(KINDS)(
    "lifts the selection of a $name at a key of the cursor, to correct the value without erasing it [WF-IHM-0040-A]",
    async ({ kind, text }) => {
      const { field, onValidate } = entry(kind, text);
      await userEvent.keyboard("{End}7{Enter}");
      expect(field.selectionStart).toBe(field.selectionEnd);
      expect(onValidate).toHaveBeenCalledWith(`${text}7`, "down");
    },
  );

  it.each(KINDS)(
    "lifts the selection of a $name at a click in the field [WF-IHM-0040-A]",
    async ({ kind, text }) => {
      const { field } = entry(kind, text);
      await userEvent.click(field);
      expect(field.selectionStart).toBe(field.selectionEnd);
    },
  );

  it.each(KINDS)(
    "keeps the caret of a $name after the character that opened it, which the next key does not erase [WF-IHM-0040-A]",
    async ({ kind }) => {
      const { field, onValidate } = entry(kind, "5", "5");
      expect(field.selectionStart).toBe(1);
      expect(field.selectionEnd).toBe(1);
      await userEvent.keyboard("6{Enter}");
      expect(onValidate).toHaveBeenCalledWith("56", "down");
    },
  );

  it("has no text to select in a list, which takes the focus and keeps its choice [WF-IHM-0040-A]", () => {
    const kind: EntryKind = {
      type: "choice",
      nullable: false,
      choices: () => [{ id: "a", label: "Alpha", active: true }],
    };
    const onValidate = vi.fn(() => true);
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <CellEditor
          kind={kind}
          label="Choix"
          text="a"
          typed={undefined}
          invalid={undefined}
          onValidate={onValidate}
          onAbandon={vi.fn()}
        />
      </NextIntlClientProvider>,
    );
    const list = screen.getByRole("combobox", { name: "Choix" });
    expect(list).toHaveFocus();
    expect(list).toHaveValue("a");
  });
});
