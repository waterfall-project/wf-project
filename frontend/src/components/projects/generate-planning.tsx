// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Engendrer le planning », on the screen of the work breakdown (FBS-4.2.1, US-0490, #1058): the
 * second step of the planning started from the encart of the project, after the work breakdown is
 * entered (WF-PRJ-0030). Offered as the revision in progress lists `generate_skeleton`, available or
 * naming what it lacks (WF-IHM-0090). It calls the same operation as the empty grid of the planning
 * (`generatePlanningSkeleton`) and reads the page anew once the server has answered — generated, so
 * that the state of the project follows (#819.6); refused with a conflict (409), so that the command
 * the server no longer offers is no longer offered (#819.5), the refusal told under it
 * (`OutcomeNotice`). Generated, the screen leads to the grid of the planning.
 *
 * A project without revision (#1358) lists the generation itself and opens the revision first
 * (`createRevision`, the rates kept), then generates on the revision it is given; the generation does
 * not open it by itself. Refused, the second call leaves the revision open with its structure empty: the
 * page is read anew, and the revision lists the command from then on. A conflict of the first — a
 * revision opened meanwhile — is read anew as well. The answer of a call that outlives the screen, or
 * the project it was made for, leads nowhere: the page the user is on is not taken away from them.
 * The button stays the same element through the reading anew, so that it keeps the focus and the
 * outcome told under it.
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { generatePlanningSkeleton } from "@/api/actions/nodes";
import { createRevision } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";

import { OPENED_REVISION } from "./start-offers";

/** The revision the planning is generated in, what the project or the revision offers, and where the grid is. */
export interface GeneratePlanningProps {
  readonly projectId: string;
  /** The revision in progress, or `undefined` for a project without one, which opens it. */
  readonly revisionId: string | undefined;
  readonly offer: CommandOffer;
  /**
   * The grid of the planning of the revision, its context kept; for a project without revision, the
   * address built with `OPENED_REVISION` in place of the revision it opens.
   */
  readonly planningHref: string;
}

/** Offer to generate the planning from the work breakdown, and lead to the grid once generated. */
export function GeneratePlanning({
  projectId,
  revisionId,
  offer,
  planningHref,
}: GeneratePlanningProps) {
  const t = useTranslations("generatePlanning");
  const router = useRouter();
  // Whether the screen is still the one the call was made from: it is not once left.
  const here = useRef(true);
  useEffect(() => {
    here.current = true;
    return () => {
      here.current = false;
    };
  }, []);
  const generate = async (): Promise<Outcome<unknown>> => {
    let target = revisionId;
    if (target === undefined) {
      const opened = await createRevision(projectId, { apply_rate_update: false });
      if (opened.kind !== "done") {
        if (opened.kind === "conflict" && here.current) {
          router.refresh();
        }
        return opened;
      }
      target = opened.data.revision_id;
      // Not stopped when the screen was left meanwhile: the revision is open, and the skeleton is
      // generated on it all the same, so that the user does not find an open revision whose
      // structure was left empty. Only the page is left alone (`here`): no reading anew, no lead.
    }
    const outcome = await generatePlanningSkeleton(projectId, target);
    if (!here.current) {
      return outcome;
    }
    if (outcome.kind === "done" || outcome.kind === "conflict" || revisionId === undefined) {
      router.refresh();
    }
    if (outcome.kind === "done") {
      router.push(planningHref.replace(OPENED_REVISION, () => target));
    }
    return outcome;
  };
  return (
    <section aria-label={t("title")} className="space-y-2">
      <h2 className="text-base font-semibold">{t("title")}</h2>
      <p className="text-sm text-muted-foreground">{t("lead")}</p>
      <Command
        offer={offer}
        label={t("label")}
        icon={commandIcon(REVISION_COMMAND_ICONS.generate_skeleton)}
        action={generate}
      />
    </section>
  );
}
