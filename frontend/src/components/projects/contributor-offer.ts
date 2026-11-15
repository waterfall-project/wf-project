// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import type { ContributorEditing } from "./contributor-commands";

/**
 * Whether the card of the contributors draws the command that modifies the list (#3417): the project
 * lists it, and it is unavailable — with the conditions it lacks — or the list is read whole, which
 * the dialog starts from. The one decision: the card reserves its place by it, and the command draws
 * itself by it. Kept out of the module of the commands, which is `"use client"`: a function of it
 * would reach the server screen as a reference (typescript.md, defect 12).
 */
export function offersModification(
  editing: Pick<ContributorEditing, "offer" | "whole"> | undefined,
): boolean {
  const offer = editing?.offer;
  return offer !== undefined && (!offer.is_available || editing?.whole?.lock_version != null);
}
