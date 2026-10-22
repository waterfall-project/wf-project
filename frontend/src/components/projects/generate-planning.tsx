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
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { generatePlanningSkeleton } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";

/** The revision the planning is generated in, what the revision offers, and where the grid is. */
export interface GeneratePlanningProps {
  readonly projectId: string;
  readonly revisionId: string;
  readonly offer: CommandOffer;
  /** The grid of the planning of the revision, its context kept. */
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
  const generate = async (): Promise<Outcome<unknown>> => {
    const outcome = await generatePlanningSkeleton(projectId, revisionId);
    if (outcome.kind === "done" || outcome.kind === "conflict") {
      router.refresh();
    }
    if (outcome.kind === "done") {
      router.push(planningHref);
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
