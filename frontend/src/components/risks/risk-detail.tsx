// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The detail of a risk the grid leads to (WF-RIS-0040), as the revision read holds it: its state,
 * its probability, its severity and its provision — computed, marked so (WF-RIS-0010,
 * WF-IHM-0030) —, the date of its last review; its description and its mitigation notes, as the
 * user wrote them; its provision line in the main structure, present while the risk weighs on the
 * estimate, withdrawn once it occurred, the lines merged from its own estimate bearing the
 * provision (WF-RIS-0060); and the history of its reviews, from the latest, which shows how its
 * probability and its severity moved (WF-RIS-0010). Everything as the API gives it.
 */
import { FileMinus, FileText, History, ShieldAlert } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { Actor, CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatPercent, formatPlanningDate } from "@/i18n/format";

import { ComputedAmount } from "./provision-totals";
import { CloseRiskDetail } from "./risk-cells";

/** A risk, as the contract gives it. */
export type Risk = components["schemas"]["Risk"];

/** A review of a risk, as the contract gives it. */
export type RiskReview = components["schemas"]["RiskReview"];

/** A fact of the risk: its name, and its value. */
function Fact({ name, children }: { readonly name: string; readonly children: ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}

/** A note of the risk, as the user wrote it, or said not set. */
function Note({ name, text }: { readonly name: string; readonly text: string | null | undefined }) {
  const t = useTranslations("risks.detail");
  return (
    <section aria-label={name} className="space-y-0.5">
      <h3 className="text-xs text-muted-foreground">{name}</h3>
      {text === null || text === undefined || text === "" ? (
        <p className="text-sm text-muted-foreground">{t("notSet")}</p>
      ) : (
        <p className="text-sm whitespace-pre-line">{text}</p>
      )}
    </section>
  );
}

/**
 * Where the provision line of the risk stands in the main structure: there while the API names it;
 * withdrawn at the occurrence of the risk (WF-RIS-0060); absent otherwise.
 */
function ProvisionLine({ risk }: { readonly risk: Risk }) {
  const t = useTranslations("risks.detail.provisionLine");
  const present = risk.provision_node_id !== null && risk.provision_node_id !== undefined;
  const Icon = present ? FileText : FileMinus;
  const said = present ? "present" : risk.state === "occurred" ? "withdrawn" : "absent";
  return (
    <section aria-label={t("title")} className="space-y-0.5">
      <h3 className="text-xs text-muted-foreground">{t("title")}</h3>
      <p className="flex items-start gap-1.5 text-sm">
        <Icon aria-hidden="true" className={`${ICON} mt-0.5`} />
        {t(said)}
      </p>
    </section>
  );
}

/**
 * The history of the reviews of a risk, from the latest, as the API orders them: a section of the
 * detail, its title one level under the risk's. Two reviews may share a day: a row is keyed by its
 * place in the answer.
 */
function Reviews({ reviews }: { readonly reviews: readonly RiskReview[] }) {
  const t = useTranslations("risks.detail.reviews");
  const states = useTranslations("enums.RiskState");
  const locale = useLocale();
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <History aria-hidden="true" className={ICON} />
        {t("title")}
      </h3>
      {reviews.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("none")}</p>
      ) : (
        <ListTable
          label={t("title")}
          columns={[t("reviewedOn"), t("probability"), t("severity"), t("state"), t("actor")]}
        >
          {reviews.map((review, place) => (
            <TableRow key={place}>
              <TableCell className={CELL}>
                {formatPlanningDate(review.reviewed_on, locale, "short")}
              </TableCell>
              <TableCell className={`${CELL} tabular-nums`}>
                {formatPercent(review.probability, locale)}
              </TableCell>
              <TableCell className={CELL}>
                <ComputedAmount amount={review.severity} />
              </TableCell>
              <TableCell className={CELL}>{states(review.state)}</TableCell>
              <TableCell className={CELL}>
                {review.actor === undefined ? null : <Actor actor={review.actor} />}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
    </section>
  );
}

/** What the detail of a risk shows. */
export interface RiskDetailProps {
  readonly risk: Risk;
  readonly reviews: readonly RiskReview[];
}

/** Render the detail of a risk. */
export function RiskDetail({ risk, reviews }: RiskDetailProps) {
  const t = useTranslations();
  const locale = useLocale();
  // Named by its label, not by its heading: an identifier of a server component may meet one of
  // the client components of the shell.
  return (
    <section aria-label={risk.label} className="space-y-3 rounded-md border p-3">
      <div className="flex items-start gap-2">
        <h2 className="flex min-w-0 flex-1 items-center gap-2 text-base font-semibold">
          <ShieldAlert aria-hidden="true" className={ICON} />
          {risk.label}
        </h2>
        <CloseRiskDetail />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <Fact name={t("grid.columns.state")}>{t(`enums.RiskState.${risk.state}`)}</Fact>
        <Fact name={t("grid.columns.probability")}>{formatPercent(risk.probability, locale)}</Fact>
        <Fact name={t("grid.columns.severity")}>
          <ComputedAmount amount={risk.severity} />
        </Fact>
        <Fact name={t("grid.columns.provisionAmount")}>
          <ComputedAmount amount={risk.provision_amount} />
        </Fact>
        <Fact name={t("grid.columns.lastReview")}>
          {risk.last_review_on === null || risk.last_review_on === undefined
            ? t("risks.detail.neverReviewed")
            : formatPlanningDate(risk.last_review_on, locale)}
        </Fact>
      </dl>
      <Note name={t("risks.detail.description")} text={risk.description} />
      <Note name={t("risks.detail.mitigation")} text={risk.mitigation_notes} />
      <ProvisionLine risk={risk} />
      <Reviews reviews={reviews} />
    </section>
  );
}
