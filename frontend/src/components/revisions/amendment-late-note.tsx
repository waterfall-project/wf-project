// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The note that says an amendment is late (US-2640): a differential not merged whose base is no
 * longer the main structure as it stands (`is_up_to_date` false), as the structure lists it — the
 * front deduces none of it. It carries no command: the gestures of the amendment stay at the
 * planning (`amendment-commands.tsx`), where the note is shown with them; the estimate shows the
 * note alone. The remaining to commit mounts it too, yet reads the main structure alone
 * (WF-RAE-0040), never a differential: the note stays unshown there.
 *
 * A server component: it reads nothing.
 */
import { useTranslations } from "next-intl";

import type { ListedStructure } from "@/components/context/structure";

/** Whether the structure is an amendment, not merged, in arrears of the main structure. */
export function isAmendmentLate(structure: ListedStructure | undefined): boolean {
  return (
    structure?.kind === "amendment" && !structure.is_merged && structure.is_up_to_date === false
  );
}

/** The note of an amendment in arrears; nothing on any other structure. */
export function AmendmentLateNote({
  structure,
}: {
  /** The structure read. */
  readonly structure: ListedStructure | undefined;
}) {
  const t = useTranslations("amendmentLate");
  if (structure === undefined || !isAmendmentLate(structure)) {
    return null;
  }
  return (
    <p role="note" className="basis-full">
      {t("note", { label: structure.label })}
    </p>
  );
}
