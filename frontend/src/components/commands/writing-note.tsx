// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
"use client";

import { useTranslations } from "next-intl";

/**
 * What a command that opens a form says while a write of the form is under way, which keeps it
 * inactive (`onWriting`): rendered then alone, for the command to be described by it. A command of a
 * cell of a dense grid, which has no room for it, says it in its tooltip (`CellCommand`).
 */
export function WritingNote({ id, writing }: { readonly id: string; readonly writing: boolean }) {
  const t = useTranslations("reference.form");
  return writing ? (
    <span id={id} className="text-xs text-muted-foreground">
      {t("writing")}
    </span>
  ) : null;
}
