// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sections of the screen of the indicators below the cards (US-0240): the tracking of the
 * milestones (FBS-4.8.6), the cumulative costs and their option shifted by the payment delays
 * (FBS-4.8.7), and the curves of earned value (FBS-4.8.8), each offered for export as a PNG
 * image that names the project, the revision and the date of calculation (WF-IHM-0130).
 *
 * The option of the payment delays is a parameter of the address of the screen, which the server
 * reads and sends to the API — the front shifts nothing and computes nothing (WF-ARC-0020); the
 * command keeps the other parameters of the address, the filters of the context among them.
 *
 * The cumulative costs and the curves of earned value are read for the sub-project the address
 * filters (`scope`); a curve with nothing to draw — a sub-project no line and no actual cost belong
 * to — says so rather than drawing a zero, and so does each series without a point under a chart
 * whose other series have some. The tracking of the milestones is computed for the project alone:
 * it follows milestones, which a sub-project does not have (WF-IND-0020). When the address filters
 * one, it says it covers the whole project, never in silence (WF-IHM-0020) — the banner says the
 * sub-project restricts every figure but it.
 */
import { Banknote, Info } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ChartProvenance } from "@/components/chart/chart";
import { buttonVariants } from "@/components/ui/button";

import { type CurveSeries, CurveSeriesChart } from "./curve-series-chart";
import { type MilestoneTracking, MilestoneChart } from "./milestone-chart";

/** The parameter of the address that shifts the cumulative costs by the payment delays. */
export const PAYMENT_DELAYS = "payment_delays";

/** The address of the screen: its path, and its parameters as Next hands them, in their order. */
export interface ScreenAddress {
  readonly pathname: string;
  readonly parameters: readonly (readonly [string, string])[];
}

/** The address of the screen with one parameter set, or removed when no value is given. */
function addressWith(address: ScreenAddress, name: string, value: string | undefined): string {
  const query = new URLSearchParams(
    address.parameters.filter(([key]) => key !== name).map(([key, kept]) => [key, kept]),
  );
  if (value !== undefined) {
    query.set(name, value);
  }
  const text = query.toString();
  return text === "" ? address.pathname : `${address.pathname}?${text}`;
}

/** A section of the screen under its title, named by it (`aria-label`, #251). */
function Section({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  return (
    <section aria-label={title} className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

/** A sentence the screen says in place of a figure: that it has none. */
function Said({ children }: { readonly children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/**
 * What the tracking of the milestones says when the address filters a sub-project: that it covers
 * the whole project, a sub-project having no milestones (WF-IND-0020).
 */
function WholeProject({ children }: { readonly children: ReactNode }) {
  return (
    <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <Info aria-hidden="true" className="size-4 shrink-0" />
      {children}
    </p>
  );
}

/**
 * Whether a curve has nothing to draw — the scope of a sub-project no line and no actual cost
 * belong to: every series without a point —, which the screen says rather than drawing a zero.
 */
function isEmptyCurve(curves: CurveSeries): boolean {
  return curves.series.every((series) => series.points.length === 0);
}

/**
 * A curve, or, when it has nothing to draw, that it has not; under the chart, each series without a
 * point among others that have some — the reference budget of a scope no reference budgets —, said
 * by its name rather than drawn as a zero.
 */
function CurveOrNothing({
  curves,
  children,
}: {
  readonly curves: CurveSeries;
  readonly children: ReactNode;
}) {
  const t = useTranslations();
  if (isEmptyCurve(curves)) {
    return <Said>{t("projectIndicators.curves.empty")}</Said>;
  }
  const empty = curves.series.filter((series) => series.points.length === 0);
  return (
    <>
      {children}
      {empty.map((series) => (
        <Said key={series.name}>
          {t("projectIndicators.curves.seriesEmpty", {
            series: t(`enums.CurveSeries.series.name.${series.name}`),
          })}
        </Said>
      ))}
    </>
  );
}

/** The tracking of the milestones: its diagram, or that no milestone is tracked. */
export function MilestoneSection({
  tracking,
  provenance,
  wholeProject = false,
}: {
  readonly tracking: MilestoneTracking;
  readonly provenance: ChartProvenance;
  /** Whether the address filters a sub-project, which has no milestones to track. */
  readonly wholeProject?: boolean;
}) {
  const t = useTranslations("projectIndicators");
  return (
    <Section title={t("milestones.title")}>
      {wholeProject ? <WholeProject>{t("wholeProject.milestones")}</WholeProject> : null}
      {tracking.milestones.length === 0 ? (
        <Said>{t("milestones.none")}</Said>
      ) : (
        <MilestoneChart tracking={tracking} provenance={provenance} />
      )}
    </Section>
  );
}

/**
 * The cumulative costs, for the sub-project the address filters, and the command that shifts them
 * by the payment delays or takes the shift back: the curves are named as the API says they are —
 * shifted or not —, not as asked. A curve with nothing to draw has nothing to shift: the command is
 * not offered; shifted, it keeps the one that takes the shift back, the way out of it.
 */
export function CostCurveSection({
  curves,
  address,
  provenance,
}: {
  readonly curves: CurveSeries;
  readonly address: ScreenAddress;
  readonly provenance: ChartProvenance;
}) {
  const t = useTranslations("projectIndicators.costCurve");
  const shifted = curves.payment_delays;
  return (
    <Section title={t("title")}>
      {isEmptyCurve(curves) && !shifted ? null : (
        <Link
          href={addressWith(address, PAYMENT_DELAYS, shifted ? undefined : "true")}
          scroll={false}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          <Banknote aria-hidden="true" />
          {shifted ? t("undelay") : t("delay")}
        </Link>
      )}
      <CurveOrNothing curves={curves}>
        <CurveSeriesChart
          curves={curves}
          title={shifted ? t("chartTitleDelayed") : t("chartTitle")}
          description={shifted ? t("descriptionDelayed") : t("description")}
          file={shifted ? t("fileDelayed") : t("file")}
          provenance={provenance}
        />
      </CurveOrNothing>
    </Section>
  );
}

/** The curves of earned value. */
export function EarnedValueSection({
  curves,
  provenance,
}: {
  readonly curves: CurveSeries;
  readonly provenance: ChartProvenance;
}) {
  const t = useTranslations("projectIndicators.earnedValue");
  return (
    <Section title={t("title")}>
      <CurveOrNothing curves={curves}>
        <CurveSeriesChart
          curves={curves}
          title={t("chartTitle")}
          description={t("description")}
          file={t("file")}
          provenance={provenance}
        />
      </CurveOrNothing>
    </Section>
  );
}
