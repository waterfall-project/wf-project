// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings every project inherits from the installation (US-0250), as the server gives them:
 * the bounds of the risk matrix — three of probability, three of severity in percentage of the
 * reference budget, which delimit four levels on each axis (FBS-3.3, WF-REF-0160) —, and the
 * zone of each of its sixteen cells, placed by its rank in the order of the contract; the watch and
 * alert thresholds of the cost and schedule indices (FBS-3.4, WF-REF-0170); the longest delay
 * expected between two marked revisions, in weeks (WF-REF-0180). Read only here: a session that may
 * modify them has them with their form (`settings-forms.tsx`, EP-14/L43e).
 */
import { CalendarClock, Gauge, Grid2x2, Grid3x3 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { Signal } from "@/components/signal/signal";
import { TableCell, TableHead, TableRow } from "@/components/ui/table";
import { formatDecimal, formatPercent } from "@/i18n/format";

import { ReferenceSection } from "./section";

type RiskMatrixSettings = components["schemas"]["RiskMatrixSettings"];
type IndexThresholds = components["schemas"]["IndexThresholds"];

/**
 * A row of a table of settings: what it is, headed as a row, and its values, figures, each under
 * the heading of its column, which keys it.
 */
function SettingRow({
  name,
  values,
}: {
  readonly name: string;
  readonly values: readonly (readonly [column: string, value: string])[];
}) {
  return (
    <TableRow>
      <TableHead scope="row" className={CELL}>
        {name}
      </TableHead>
      {values.map(([column, value]) => (
        <TableCell key={column} className={`${CELL} text-right tabular-nums`}>
          {value}
        </TableCell>
      ))}
    </TableRow>
  );
}

/** The three bounds of each axis of the risk matrix, as percentages, in their order. */
export function RiskBoundsTable({ matrix }: { readonly matrix: RiskMatrixSettings }) {
  const t = useTranslations("reference.riskMatrix");
  const locale = useLocale();
  const columns = [t("first"), t("second"), t("third")];
  // Three bounds on each axis, as the contract bounds them, each under its column.
  const bounds = (values: readonly string[]) =>
    values.map((value, at) => [columns[at] ?? "", formatPercent(value, locale)] as const);
  return (
    <ReferenceSection title={t("title")} icon={Grid2x2}>
      <ListTable label={t("title")} columns={[t("axis"), ...columns]}>
        <SettingRow name={t("probability")} values={bounds(matrix.probability_bounds)} />
        <SettingRow name={t("severity")} values={bounds(matrix.severity_bounds)} />
      </ListTable>
    </ReferenceSection>
  );
}

/** The four levels of an axis of the matrix, from the lowest. */
export const LEVELS = [1, 2, 3, 4] as const;

/** A level of an axis of the matrix. */
type Level = (typeof LEVELS)[number];

/**
 * The rank of the zone of a cell in the order of the contract: by probability then by severity, each
 * from the lowest level, the cell of probability p and severity s at 4 × (p − 1) + (s − 1).
 */
export function zoneRank(probability: Level, severity: Level): number {
  return 4 * (probability - 1) + (severity - 1);
}

/**
 * The zone of each cell of the risk matrix, the highest probability at the top as a matrix of
 * risks reads: the zones come by probability then by severity, each from the lowest level, so the
 * cell of probability p and severity s is the zone of rank 4 × (p − 1) + (s − 1).
 */
export function RiskZonesTable({ matrix }: { readonly matrix: RiskMatrixSettings }) {
  const t = useTranslations("reference.riskZones");
  const severities = LEVELS.map((level) => t("severity", { level }));
  return (
    <ReferenceSection title={t("title")} icon={Grid3x3}>
      <ListTable label={t("title")} columns={[t("axes"), ...severities]}>
        {[...LEVELS].reverse().map((probability) => (
          <TableRow key={probability}>
            <TableHead scope="row" className={CELL}>
              {t("probability", { level: probability })}
            </TableHead>
            {LEVELS.map((severity) => {
              const zone = matrix.zones[zoneRank(probability, severity)];
              return (
                <TableCell key={severity} className={CELL}>
                  {zone === undefined ? null : <Signal zone={zone} />}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/** The watch and alert thresholds of the cost and schedule indices. */
export function IndexThresholdTable({ thresholds }: { readonly thresholds: IndexThresholds }) {
  const t = useTranslations("reference.indices");
  const locale = useLocale();
  const row = (watch: string, alert: string) =>
    [
      [t("watch"), formatDecimal(watch, locale)],
      [t("alert"), formatDecimal(alert, locale)],
    ] as const;
  return (
    <ReferenceSection title={t("title")} icon={Gauge}>
      <ListTable label={t("title")} columns={[t("index"), t("watch"), t("alert")]}>
        <SettingRow name={t("cost")} values={row(thresholds.cost_watch, thresholds.cost_alert)} />
        <SettingRow
          name={t("schedule")}
          values={row(thresholds.schedule_watch, thresholds.schedule_alert)}
        />
      </ListTable>
    </ReferenceSection>
  );
}

/** The longest delay expected between two marked revisions of a project in progress. */
export function ReviewDelay({ weeks }: { readonly weeks: number }) {
  const t = useTranslations("reference.reviews");
  return (
    <ReferenceSection title={t("title")} icon={CalendarClock}>
      <p className="text-sm">{t("maxWeeks", { weeks })}</p>
    </ReferenceSection>
  );
}
