// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The abandon of an amendment (US-2640, WF-REV-0100), from the grid of its differential: the command
 * opens a confirmation in the page, which says the differential and what it holds are deleted, the
 * main structure untouched, and that nothing undoes it (WF-IHM-0110); confirmed, the server action
 * deletes the structure (`deleteCostStructure`) from the counter the screen read, and the screen leaves
 * the address of the differential, which is no more, for the same screen on the main structure. It is
 * offered where the structure lists its `delete` command available — a differential not merged of the
 * revision in progress — and nowhere else. A counter that moved since it was read (412) offers to
 * reload the screen, which reads the structure anew.
 */
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { abandonAmendment } from "@/api/actions/revisions";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, STRUCTURE_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import type { ObjectNames } from "@/components/commands/outcome-notice";
import { structureHref } from "@/components/context/structure";

/** The amendment to abandon, where it is, and the counter the screen read of it. */
export interface AbandonedAmendment {
  readonly projectId: string;
  readonly revisionId: string;
  readonly structureId: string;
  readonly label: string;
  readonly lockVersion: number;
}

/** Offer the abandon of the amendment a grid reads, as its structure lists it. */
export function AbandonAmendmentCommand({
  offer,
  amendment,
  names,
}: {
  readonly offer: CommandOffer;
  readonly amendment: AbandonedAmendment;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("abandonAmendment");
  const helps = useTranslations("commands");
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [left, setLeft] = useState(false);
  // After the status is told, in the same commit: the screen leaves the structure that is no more.
  useEffect(() => {
    if (left) {
      router.replace(
        structureHref(pathname, new URLSearchParams(search), { structure_id: "", kind: "main" }),
      );
    }
  }, [left, router, pathname, search]);
  return (
    <ConfirmedCommand
      offer={offer}
      label={t("label")}
      help={helps("structure.delete.help")}
      icon={commandIcon(STRUCTURE_COMMAND_ICONS.delete)}
      statement={t("statement")}
      submit={t("submit")}
      names={names}
      subject={amendment.label}
      run={() =>
        abandonAmendment(
          amendment.projectId,
          amendment.revisionId,
          amendment.structureId,
          amendment.lockVersion,
        )
      }
      done={() => t("done", { label: amendment.label })}
      onDone={() => {
        setLeft(true);
      }}
    />
  );
}
