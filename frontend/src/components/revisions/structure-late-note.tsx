// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The note that says a structure is late (US-2640, US-3140): a differential not merged, or the own
 * estimate of a risk whole and not consumed, whose base is no longer the main structure as it stands
 * (`is_up_to_date` false), as the structure lists it — the front deduces none of it. The note names the
 * structure and says what the update waits for: the merge for an amendment, the first entry for an own
 * estimate, which is updated then, without a question when the update signals nothing. It carries no
 * command: the gestures of the structure stay at the planning (`structure-commands.tsx`), where the
 * note is shown with them; the estimate shows the note alone. The remaining to commit does not mount
 * it: it reads the main structure alone (WF-RAE-0040), never a differential.
 *
 * A pruned own estimate is never said late: it has no base, and its grid recomposes it before anything
 * (`own-estimate-entry.tsx`). A server component: it reads nothing.
 */
import { useTranslations } from "next-intl";

import type { ListedStructure } from "@/components/context/structure";

/** Whether the structure is an amendment or a whole own estimate, not merged, in arrears of the main one. */
export function isStructureLate(structure: ListedStructure | undefined): boolean {
  if (structure === undefined || structure.is_merged || structure.is_up_to_date !== false) {
    return false;
  }
  return (
    structure.kind === "amendment" || (structure.kind === "risk" && structure.is_pruned !== true)
  );
}

/** The note of a structure in arrears; nothing on any other structure. */
export function StructureLateNote({
  structure,
}: {
  /** The structure read. */
  readonly structure: ListedStructure | undefined;
}) {
  const amendment = useTranslations("amendmentLate");
  const own = useTranslations("ownEstimateLate");
  if (structure === undefined || !isStructureLate(structure)) {
    return null;
  }
  const t = structure.kind === "risk" ? own : amendment;
  return (
    <p role="note" className="basis-full">
      {t("note", { label: structure.label })}
    </p>
  );
}
