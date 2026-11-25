// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the amendment or of the own estimate of a risk a grid reads (US-0510, US-2640,
 * US-3140), each as the structure — or, for the merge, the revision — lists it, and none on any other
 * structure. The own estimate has the note of its delay and its update alone: it is neither merged nor
 * abandoned, its risk occurring or being deleted. For an amendment: « Contractualiser l’avenant », « Mettre
 * à jour l’avenant » and « Abandonner l’avenant ». A differential in arrears (`is_up_to_date` false) says
 * so, offers its update, and does not offer the merge, which the service refuses (409) before the
 * update (#4034): the front deduces none of it but the word of the structure.
 *
 * A server component: it reads nothing, hands the client commands their data.
 */
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import type { ListedStructure } from "@/components/context/structure";

import { AbandonAmendmentCommand } from "./abandon-amendment-command";
import { isStructureLate, StructureLateNote } from "./structure-late-note";
import { MergeAmendmentCommand } from "./merge-amendment-command";
import { RebaseStructureCommand } from "./rebase-structure-command";

type StructureCommand = components["schemas"]["StructureCommand"];

/**
 * The offer of a command the structure lists available. The grid screen (`grid-screen.ts`) keeps from
 * `available_commands` only the commands that are available — the others, with their missing
 * conditions, are dropped there, the grid reading as it does a structure it cannot write —, so the
 * set this component receives holds nothing else: a command in it is offered, one missing from it is
 * not offered at all, which is the word of the structure, not a deduction of the front.
 */
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };

/** Where the amendment is. */
export interface AmendmentAddress {
  readonly projectId: string;
  readonly revisionId: string;
}

/** The commands of the amendment or own estimate the grid reads; nothing on any other structure. */
export function StructureCommands({
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
  const amendment = structure?.kind === "amendment" ? structure : undefined;
  const own = structure?.kind === "risk" && !structure.is_merged ? structure : undefined;
  const read = amendment ?? own;
  if (read === undefined) {
    return null;
  }
  const late = isStructureLate(amendment);
  const names = { [read.structure_id]: read.label };
  const where = {
    projectId: revision.projectId,
    revisionId: revision.revisionId,
    structureId: read.structure_id,
    label: read.label,
    nature: amendment === undefined ? ("risk" as const) : ("amendment" as const),
  };
  return (
    <div className="flex flex-wrap items-start gap-x-2 gap-y-2">
      <StructureLateNote structure={read} />
      {amendment === undefined ? null : (
        <MergeAmendmentCommand
          key={`merge:${amendment.structure_id}`}
          offer={late ? undefined : mergeOffer}
          amendment={where}
          merged={amendment.is_merged}
          names={names}
        />
      )}
      {commands.has("rebase") ? (
        <RebaseStructureCommand
          key={`rebase:${read.structure_id}`}
          offer={AVAILABLE}
          structure={where}
          names={names}
        />
      ) : null}
      {amendment !== undefined && commands.has("delete") ? (
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
