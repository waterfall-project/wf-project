// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the amendment a grid reads (US-0510, US-2640), each as the structure — or, for the
 * merge, the revision — lists it, and none on any other structure: « Contractualiser l’avenant », « Mettre
 * à jour l’avenant » and « Abandonner l’avenant ». A differential in arrears (`is_up_to_date` false) says
 * so, offers its update, and does not offer the merge, which the service refuses (409) before the
 * update (#4034): the front deduces none of it but the word of the structure.
 *
 * A server component: it reads nothing, hands the client commands their data.
 */
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import type { ListedStructure } from "@/components/context/structure";

import { AbandonAmendmentCommand } from "./abandon-amendment-command";
import { MergeAmendmentCommand } from "./merge-amendment-command";
import { RebaseAmendmentCommand } from "./rebase-amendment-command";

type StructureCommand = components["schemas"]["StructureCommand"];

/** What the structure lists available, which the screen offers as a command that is. */
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };

/** Where the amendment is. */
export interface AmendmentAddress {
  readonly projectId: string;
  readonly revisionId: string;
}

/** The commands of the amendment the grid reads; nothing on any other structure. */
export function AmendmentCommands({
  structure,
  version,
  commands,
  mergeOffer,
  revision,
}: {
  /** The structure read. */
  readonly structure: ListedStructure | undefined;
  /** The counter of the structure read, which the abandon carries. */
  readonly version: number;
  /** The commands the structure lists available. */
  readonly commands: ReadonlySet<StructureCommand>;
  /** The merge as the revision lists it. */
  readonly mergeOffer: CommandOffer | undefined;
  readonly revision: AmendmentAddress;
}) {
  const t = useTranslations("amendmentLate");
  const amendment = structure?.kind === "amendment" ? structure : undefined;
  if (amendment === undefined) {
    return null;
  }
  const late = !amendment.is_merged && amendment.is_up_to_date === false;
  const names = { [amendment.structure_id]: amendment.label };
  const where = {
    projectId: revision.projectId,
    revisionId: revision.revisionId,
    structureId: amendment.structure_id,
    label: amendment.label,
  };
  return (
    <div className="space-y-2">
      {late ? <p role="note">{t("note", { label: amendment.label })}</p> : null}
      <MergeAmendmentCommand
        key={`merge:${amendment.structure_id}`}
        offer={late ? undefined : mergeOffer}
        amendment={where}
        merged={amendment.is_merged}
        names={names}
      />
      {commands.has("rebase") ? (
        <RebaseAmendmentCommand
          key={`rebase:${amendment.structure_id}`}
          offer={AVAILABLE}
          amendment={where}
          names={names}
        />
      ) : null}
      {commands.has("delete") ? (
        <AbandonAmendmentCommand
          key={`abandon:${amendment.structure_id}`}
          offer={AVAILABLE}
          amendment={{ ...where, lockVersion: version }}
          names={names}
        />
      ) : null}
    </div>
  );
}
