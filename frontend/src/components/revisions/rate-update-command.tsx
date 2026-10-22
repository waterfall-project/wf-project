// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The application of the rate update the API proposes to the current revision (WF-REV-0060, C-362):
 * the command stands under the proposal, and opens a confirmation that presents what changes —
 * category by category, the previous rate and the proposed one, each category kept or refused by a
 * box — before it applies it. A revision marked keeps the rates and the amounts it calculated
 * (WF-REF-0130): the proposal is read for the current revision alone, and the server refuses the
 * rest (409). The revision is sent in the version read, and read again once the update is applied,
 * so that the amounts of its lines and of its totals follow.
 *
 * No command of the revision says the update beforehand: the proposal presents it, and the refusal of
 * the server alone names the condition that lacks.
 */
"use client";

import { Coins } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useId, useState } from "react";

import { applyRateUpdate } from "@/api/actions/revisions";
import type { components } from "@/api/generated/schema";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { formatMoney } from "@/i18n/format";

/** A category of the proposal. */
type ProposedCategory = components["schemas"]["RateUpdateProposal"]["categories"][number];

/** The revision the update applies to, the version read, and the categories proposed. */
export interface ApplyRateUpdateProps {
  readonly projectId: string;
  readonly revisionId: string;
  readonly lockVersion: number;
  /** How the screen names the revision, which a refusal and the history of the messages cite. */
  readonly name: string;
  readonly categories: readonly ProposedCategory[];
}

/** Offer the application of the rates proposed, confirmed category by category. */
export function ApplyRateUpdateCommand({
  projectId,
  revisionId,
  lockVersion,
  name,
  categories,
}: ApplyRateUpdateProps) {
  const t = useTranslations("revisionCommands.rateUpdate");
  const locale = useLocale();
  const legend = useId();
  const [refused, setRefused] = useState<ReadonlySet<string>>(new Set());
  const retained = categories.filter(({ cost_category_id: id }) => !refused.has(id));
  return (
    <ConfirmedCommand
      offer={{ is_available: true, missing_conditions: [] }}
      label={t("label")}
      icon={<Coins aria-hidden="true" />}
      statement={t("statement")}
      submit={t("submit")}
      ready={retained.length > 0}
      names={{ [revisionId]: name }}
      subject={name}
      run={() =>
        applyRateUpdate(projectId, revisionId, {
          categoryIds: retained.map(({ cost_category_id: id }) => id),
          lockVersion,
        })
      }
      done={() => t("done", { count: retained.length })}
    >
      <fieldset aria-labelledby={legend} className="space-y-1">
        <legend id={legend} className="font-medium">
          {t("categories")}
        </legend>
        {categories.map((category) => (
          <label key={category.cost_category_id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!refused.has(category.cost_category_id)}
              onChange={(event) => {
                const next = new Set(refused);
                if (event.target.checked) {
                  next.delete(category.cost_category_id);
                } else {
                  next.add(category.cost_category_id);
                }
                setRefused(next);
              }}
            />
            {t("change", {
              category: category.label,
              previous: formatMoney(category.previous_amount, locale),
              proposed: formatMoney(category.proposed_amount, locale),
            })}
          </label>
        ))}
      </fieldset>
      {retained.length === 0 ? (
        <p role="alert" className="text-destructive">
          {t("noneRetained")}
        </p>
      ) : null}
    </ConfirmedCommand>
  );
}
