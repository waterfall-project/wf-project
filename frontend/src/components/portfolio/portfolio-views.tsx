// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The figures and the tables of the views of the portfolio (FBS-2.2 to FBS-2.7), each as the server
 * computes it on the perimeter retained: its performance (WF-PTF-0070), the structure of its costs
 * (WF-PTF-0080), its risks (WF-PTF-0090), its aggregated workload (WF-PTF-0060) and the health of
 * its steering (WF-PTF-0110). Nothing is summed, averaged, divided, sorted nor filtered here
 * (WF-ARC-0020): a sum is marked computed, Σ (WF-IHM-0030), a value the server could not compute is
 * said so with its reason, never zero, and a zone is the one the server classes, shown by the one
 * signal (WF-IHM-0070). Every figure carries the date of calculation of its view, under its title
 * (`PortfolioHeader`). Each project named opens (WF-PTF-0030). Nothing is entered: the views
 * consolidate, they do not modify.
 */
import Link from "next/link";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputedAmount, ComputedTotal } from "@/components/computed-amount";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { RiskMatrixView } from "@/components/risks/risk-matrix";
import { Signal } from "@/components/signal/signal";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal, formatMonth, formatPercent } from "@/i18n/format";

import { ComputableValue, Figure, ViewSection } from "./portfolio-value";

type Schemas = components["schemas"];
type IndexValue = Schemas["IndexValue"];
type AmountByKey = Schemas["AmountByKey"];

/** A link that opens a project of the portfolio (WF-PTF-0030). */
function ProjectLink({ id, label }: { readonly id: string; readonly label: string }) {
  return (
    <Link href={`/projects/${id}`} className="underline-offset-2 hover:underline">
      {label}
    </Link>
  );
}

/** An index of the portfolio, its zone by the one signal; its value or why it has none. */
function PortfolioIndex({ name, index }: { readonly name: string; readonly index: IndexValue }) {
  const locale = useLocale();
  return (
    <Figure name={name}>
      <span className="inline-flex items-center gap-3">
        <ComputableValue value={index.value} format={(value) => formatDecimal(value, locale)} />
        {index.zone === null ? null : <Signal zone={index.zone} />}
      </span>
    </Figure>
  );
}

/** An amount the server may leave out: marked computed, or nothing. */
function Amount({ amount }: { readonly amount: string | null | undefined }) {
  return amount === null || amount === undefined ? null : <ComputedAmount amount={amount} />;
}

/** Render the indices, the variances, the projections and the distribution by zone. */
export function PerformanceView({
  performance,
}: {
  readonly performance: Schemas["PortfolioPerformance"];
}) {
  const t = useTranslations();
  const format = useFormatter();
  const { projections } = performance;
  const rows = [
    [
      "atBudget",
      <ComputedAmount key="at" amount={projections.at_budget} />,
      projections.variance_at_budget,
    ],
    [
      "projectManager",
      <ComputedAmount key="pm" amount={projections.project_manager} />,
      projections.variance_project_manager,
    ],
    [
      "atObservedRate",
      <ComputableValue
        key="rate"
        value={projections.at_observed_rate}
        format={(value) => <ComputedAmount amount={value} />}
      />,
      projections.variance_at_observed_rate,
    ],
  ] as const;
  return (
    <>
      <ViewSection title={t("portfolio.performance.indices")}>
        <dl className="flex flex-wrap gap-x-10 gap-y-3">
          <PortfolioIndex name={t("indicator.names.costIndex")} index={performance.cost_index} />
          <PortfolioIndex
            name={t("indicator.names.scheduleIndex")}
            index={performance.schedule_index}
          />
          <Figure name={t("projectIndicators.figures.costVariance")}>
            <Amount amount={performance.cost_variance} />
          </Figure>
          <Figure name={t("projectIndicators.figures.scheduleVariance")}>
            <Amount amount={performance.schedule_variance} />
          </Figure>
          <Figure name={t("projectIndicators.figures.referenceBudget")}>
            <Amount amount={performance.reference_budget} />
          </Figure>
        </dl>
      </ViewSection>
      <ViewSection title={t("portfolio.performance.projections")}>
        <ListTable
          label={t("portfolio.performance.projections")}
          columns={[
            t("projectIndicators.projections.hypothesis"),
            t("projectIndicators.projections.amount"),
            t("projectIndicators.projections.variance"),
          ]}
        >
          {rows.map(([name, amount, variance]) => (
            <TableRow key={name}>
              <TableCell className={CELL}>{t(`portfolio.performance.${name}`)}</TableCell>
              <TableCell className={`${CELL} tabular-nums`}>{amount}</TableCell>
              <TableCell className={`${CELL} tabular-nums`}>
                <Amount amount={variance} />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      </ViewSection>
      <ViewSection title={t("portfolio.performance.distribution")}>
        <ListTable
          label={t("portfolio.performance.distribution")}
          columns={[
            t("portfolio.performance.index"),
            t("portfolio.performance.zone"),
            t("portfolio.performance.projects"),
          ]}
        >
          {performance.zone_distribution.map((entry) => (
            <TableRow key={`${entry.index}-${entry.zone}`}>
              <TableCell className={CELL}>
                {t(`enums.PortfolioPerformance.zone_distribution.index.${entry.index}`)}
              </TableCell>
              <TableCell className={CELL}>
                <Signal zone={entry.zone} />
              </TableCell>
              <TableCell className={`${CELL} tabular-nums`}>
                {format.number(entry.project_count)}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      </ViewSection>
    </>
  );
}

/** A breakdown by key — a nature of cost, a node of organisation —: amount and share of each. */
function Breakdown({
  title,
  keyName,
  parts,
}: {
  readonly title: string;
  readonly keyName: string;
  readonly parts: readonly AmountByKey[];
}) {
  const t = useTranslations("portfolio.costStructure");
  const locale = useLocale();
  return (
    <ViewSection title={title}>
      <ListTable label={title} columns={[keyName, t("amount"), t("share")]}>
        {parts.map((part) => (
          <TableRow key={part.key}>
            <TableCell className={CELL}>{part.label ?? t("unnamed")}</TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              <ComputedAmount amount={part.amount} />
            </TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {part.share === undefined ? null : formatPercent(part.share, locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ViewSection>
  );
}

/** Render the structure of the costs: by nature on the budget and the remaining, labour by node. */
export function CostStructureView({
  structure,
}: {
  readonly structure: Schemas["PortfolioCostStructure"];
}) {
  const t = useTranslations("portfolio.costStructure");
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("noActualCost")}</p>
      <div className="grid gap-6 lg:grid-cols-2">
        <Breakdown
          title={t("budget")}
          keyName={t("nature")}
          parts={structure.budget_by_cost_type}
        />
        <Breakdown
          title={t("remaining")}
          keyName={t("nature")}
          parts={structure.remaining_by_cost_type}
        />
      </div>
      <Breakdown title={t("labor")} keyName={t("orgNode")} parts={structure.labor_by_org_node} />
    </>
  );
}

/** Render the risks: their total, the heaviest with their project, the matrix, the period. */
export function PortfolioRisksView({ risks }: { readonly risks: Schemas["PortfolioRisks"] }) {
  const t = useTranslations("portfolio.risks");
  return (
    <>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        <ComputedTotal name={t("identifiedTotal")} amount={risks.identified_total} />
        <ComputedTotal name={t("occurred")} amount={risks.period_outcome.occurred_provisions} />
        <ComputedTotal name={t("dismissed")} amount={risks.period_outcome.dismissed_provisions} />
      </dl>
      <div className="space-y-6">
        <ViewSection title={t("heaviest")}>
          <ListTable label={t("heaviest")} columns={[t("risk"), t("project"), t("provision")]}>
            {risks.heaviest.map((risk) => (
              <TableRow key={risk.risk_id}>
                <TableCell className={CELL}>{risk.label}</TableCell>
                <TableCell className={CELL}>
                  <ProjectLink id={risk.project_id} label={risk.project_label} />
                </TableCell>
                <TableCell className={`${CELL} tabular-nums`}>
                  <ComputedAmount amount={risk.provision_amount} />
                </TableCell>
              </TableRow>
            ))}
          </ListTable>
        </ViewSection>
        <div className="max-w-3xl">
          <RiskMatrixView matrix={risks.matrix} />
        </div>
      </div>
    </>
  );
}

/** Render the aggregated workload: for each role, its capacity and, month by month, its load. */
export function WorkloadView({ workload }: { readonly workload: Schemas["PortfolioWorkload"] }) {
  const t = useTranslations("portfolio.workload");
  const locale = useLocale();
  // The months of the first role head the columns: the contract does not say that every role has
  // the same months (#326).
  const months = workload.roles[0]?.months.map((month) => month.month) ?? [];
  if (workload.roles.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("none")}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <ListTable
        label={t("title")}
        columns={[t("role"), t("capacity"), ...months.map((month) => formatMonth(month, locale))]}
      >
        {workload.roles.map((role) => (
          <TableRow key={role.resource_role_id}>
            <TableCell className={CELL}>{role.label}</TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {role.capacity_monthly_hours === undefined
                ? null
                : t("hours", { hours: formatDecimal(role.capacity_monthly_hours, locale) })}
            </TableCell>
            {role.months.map((month) => (
              <TableCell key={month.month} className={`${CELL} tabular-nums`}>
                <span className="flex flex-col">
                  <span>{t("hours", { hours: formatDecimal(month.hours, locale) })}</span>
                  <span className="inline-flex items-center gap-1">
                    {month.zone === undefined ? null : <Signal zone={month.zone} variant="icon" />}
                    <ComputableValue
                      value={month.load_ratio}
                      format={(ratio) => formatPercent(ratio, locale)}
                    />
                  </span>
                </span>
              </TableCell>
            ))}
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/** Render the signals of the health of the steering, each with its project, which it opens. */
export function PilotHealthView({ health }: { readonly health: Schemas["PilotHealth"] }) {
  const t = useTranslations();
  if (health.signals.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("portfolio.pilotHealth.none")}</p>;
  }
  return (
    <ListTable
      label={t("portfolio.pilotHealth.signals")}
      columns={[
        t("portfolio.pilotHealth.project"),
        t("portfolio.pilotHealth.signal"),
        t("portfolio.pilotHealth.zone"),
      ]}
    >
      {health.signals.map((signal, rank) => (
        // A project may give the same signal twice — two milestones overdue —: its rank tells them
        // apart.
        <TableRow key={`${signal.project_id}-${signal.code}-${rank.toString()}`}>
          <TableCell className={CELL}>
            <ProjectLink id={signal.project_id} label={signal.project_label} />
          </TableCell>
          <TableCell className={CELL}>
            {t(`enums.PilotHealth.signals.code.${signal.code}`)}
          </TableCell>
          <TableCell className={CELL}>
            <Signal zone={signal.zone} />
          </TableCell>
        </TableRow>
      ))}
    </ListTable>
  );
}
