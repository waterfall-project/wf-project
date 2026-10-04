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
 */
import { Banknote } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type ReactNode, useId } from "react";

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

/** A section of the screen under its title. */
function Section({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-2">
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

/** A sentence the screen says in place of a figure: that it has none. */
function Said({ children }: { readonly children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/** The tracking of the milestones: its diagram, or that no milestone is tracked. */
export function MilestoneSection({
  tracking,
  provenance,
}: {
  readonly tracking: MilestoneTracking;
  readonly provenance: ChartProvenance;
}) {
  const t = useTranslations("projectIndicators.milestones");
  return (
    <Section title={t("title")}>
      {tracking.milestones.length === 0 ? (
        <Said>{t("none")}</Said>
      ) : (
        <MilestoneChart tracking={tracking} provenance={provenance} />
      )}
    </Section>
  );
}

/**
 * The cumulative costs, and the command that shifts them by the payment delays or takes the shift
 * back: the curves are named as the API says they are — shifted or not —, not as asked.
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
      <Link
        href={addressWith(address, PAYMENT_DELAYS, shifted ? undefined : "true")}
        scroll={false}
        className={buttonVariants({ variant: "outline", size: "sm" })}
      >
        <Banknote aria-hidden="true" />
        {shifted ? t("undelay") : t("delay")}
      </Link>
      <CurveSeriesChart
        curves={curves}
        title={shifted ? t("chartTitleDelayed") : t("chartTitle")}
        description={shifted ? t("descriptionDelayed") : t("description")}
        file={shifted ? t("fileDelayed") : t("file")}
        provenance={provenance}
      />
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
      <CurveSeriesChart
        curves={curves}
        title={t("chartTitle")}
        description={t("description")}
        file={t("file")}
        provenance={provenance}
      />
    </Section>
  );
}
