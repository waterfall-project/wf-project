// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the own estimate of a risk, in the page of the planning or of the estimate (US-3140):
 * mounted anew for the structure it reads, under what recomposes and updates it (`own-estimate-entry.tsx`);
 * any other structure — the main one, a differential, an own estimate consumed by its risk — leaves
 * its grid as it is. The structure says what is to do, by the commands it lists (`recompose`) and by
 * those it lists unavailable for the sole reason that it is out of date (`GridScreen.gated`): the front
 * deduces nothing.
 *
 * A server component: it reads nothing, and hands the client component its data.
 */
import type { ReactNode } from "react";

import type { ListedStructure } from "@/components/context/structure";

import { OwnEstimateEntry } from "./own-estimate-entry";

/** The commands of entry of a structure, as the grid screen lists them. */
type Commands = ReadonlySet<string>;

/** Where the own estimate is. */
export interface OwnEstimateAddress {
  readonly projectId: string;
  readonly revisionId: string;
}

/** Wrap a grid in what the own estimate of a risk it reads asks; the grid alone otherwise. */
export function OwnEstimateScope({
  structure,
  commands,
  gated,
  revision,
  children,
}: {
  /** The structure read. */
  readonly structure: ListedStructure;
  /** The commands the structure lists available. */
  readonly commands: Commands;
  /** The entry commands it lists unavailable for the sole reason that it is out of date. */
  readonly gated: Commands;
  readonly revision: OwnEstimateAddress;
  readonly children: ReactNode;
}) {
  if (structure.kind !== "risk" || structure.is_merged) {
    return <>{children}</>;
  }
  return (
    <OwnEstimateEntry
      key={structure.structure_id}
      estimate={{ ...revision, structureId: structure.structure_id, label: structure.label }}
      late={gated.size > 0}
      recompose={commands.has("recompose")}
    >
      {children}
    </OwnEstimateEntry>
  );
}
