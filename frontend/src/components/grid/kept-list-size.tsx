// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The number of rows per page of a journal that is no grid — the imports of actual costs, the imports
 * of a project — recorded with the preferences of its key (`GridPreferences.page_size`, WF-IHM-0060),
 * as a dense grid records its own (`kept-size.ts`): each time the page shows a size that differs from
 * the one kept, the one shown; the page finds it again when the address names none. A journal has
 * no column to hide, no width, no sort: what the account kept for the key besides is sent back as it
 * came. A write the service refuses is told where the journal stands, and may be dismissed.
 *
 * Every prop is data, never a function: a server component hands it over (défaut n° 12 de
 * `typescript.md`).
 */
"use client";

import { useCallback, useState } from "react";

import { OutcomeNotice } from "@/components/commands/outcome-notice";

import { useKeptPageSize } from "./kept-size";
import { type GridAddress, pageSizeOf } from "./query";
import { type GridPreferences, keptPageSize, useSettingsWriter } from "./settings";

/** Record the size of the pages a journal shows under the key of its grid; renders its refusal, if any. */
export function KeptListSize({
  gridKey,
  address,
  preferences,
}: {
  /** The key the preferences of the journal are kept under. */
  readonly gridKey: string;
  /** The names under which the address carries the size of its pages (`limit`). */
  readonly address: GridAddress;
  /** What the account kept for the key; none, it kept nothing. */
  readonly preferences: GridPreferences | undefined;
}) {
  const [kept, setKept] = useState(keptPageSize(preferences));
  const { recordShown, shown, outcome, clear } = useSettingsWriter(gridKey);
  const record = useCallback(
    (size: number) => {
      const sized = pageSizeOf(size);
      if (sized === undefined) {
        return;
      }
      setKept(sized);
      recordShown(() => ({ ...preferences, page_size: sized }));
      shown();
    },
    [preferences, recordShown, shown],
  );
  useKeptPageSize(address, kept, record, true);
  return <OutcomeNotice outcome={outcome} onClear={clear} dismissible />;
}
