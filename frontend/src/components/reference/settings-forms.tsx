// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings every project inherits from the installation, and their forms (EP-14/L43e), in the
 * dialog of the forms of the reference data (`ReferenceForm`), offered to a session that holds the
 * permission of modification of the screen's function (WF-ADM-0100) — the page hands over only what
 * that session may write: the risk matrix, its six bounds and its sixteen zones (FBS-3.3,
 * WF-REF-0160), under `risk_settings.write`; the thresholds of the indices and the delay between two
 * reviews (FBS-3.4, WF-REF-0170, WF-REF-0180), under `indicator_settings.write`. Each form sends the
 * part of its screen alone with the version read (`updateReferenceSettings`), never a field of the
 * other screen; neither the currency, which is not modified (WF-REF-0140), nor the default language
 * of the installation, which is EP-03's, is offered.
 *
 * The form checks before asking that the bounds of each axis rise strictly and that the alert
 * threshold of each index stays below its watch threshold, each broken rule said at the field the
 * server would point at — the bound of the rank that breaks the order, the alert —; the server judges
 * the rest, a refusal by field said at its field, any other under the form, the version stale (412)
 * with the offer to read the page anew. The answer takes the place of the settings read while it is
 * newer than them (`lock_version`) — against the fake back, which keeps nothing, for as long as the
 * screen stays; the page says so under its header (`MockupNotice`) —, and the page is read anew. A
 * form writes from the version it opened on: a reading that comes while it is open does not lend its
 * version to a draft entered on another.
 */
"use client";

import { Pencil } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type ComponentType, type ReactNode, useRef, useState } from "react";

import { updateReferenceSettings } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import { Button } from "@/components/ui/button";
import { compareDecimals, editableDecimal, editablePercent, percentRatio } from "@/i18n/format";

import { Reactivations } from "./reactivation";
import { type Draft, type FormField, ReferenceForm } from "./reference-form";
import {
  IndexThresholdTable,
  LEVELS,
  ReviewDelay,
  RiskBoundsTable,
  RiskZonesTable,
  zoneRank,
} from "./setting-tables";

type ReferenceSettings = components["schemas"]["ReferenceSettings"];
type AlertZone = components["schemas"]["AlertZone"];
type FieldProblem = components["schemas"]["FieldProblem"];

/**
 * Every zone of the contract, which a cell of the matrix may take, from the lowest: one added there
 * fails the type check until it is here.
 */
const EVERY_ZONE: Readonly<Record<AlertZone, true>> = { nominal: true, watch: true, alert: true };

/** The zones a choice offers, in the order of their table. */
const ZONES = Object.keys(EVERY_ZONE) as readonly AlertZone[];

/** The ranks of the three bounds of an axis, from the lowest, and the word that names each. */
const BOUNDS = [
  [0, "first"],
  [1, "second"],
  [2, "third"],
] as const;

/** The two axes of the matrix, by the name of their bounds in the contract. */
type Axis = "probability_bounds" | "severity_bounds";

/** The field of a bound of an axis, by the pointer of the contract it writes. */
function boundField(axis: Axis, rank: number): string {
  return `risk_matrix/${axis}/${String(rank)}`;
}

/** The field of the zone of a cell, by its rank in the order of the contract. */
function zoneField(rank: number): string {
  return `risk_matrix/zones/${String(rank)}`;
}

/** The two indices, by the names of their thresholds in the contract. */
const INDICES = [
  ["cost", "cost_watch", "cost_alert"],
  ["schedule", "schedule_watch", "schedule_alert"],
] as const;

/** The field of the delay between two reviews. */
const WEEKS = "max_weeks_between_reviews";

/** A refusal at a field, as the server would point at it. */
function refusal(name: string, code: FieldProblem["code"]): readonly [string, FieldProblem] {
  return [name, { pointer: `/${name}`, code }];
}

/**
 * The bounds of the matrix that break their order, as the server would refuse them (WF-REF-0160):
 * on each axis, every bound not strictly above the one before it, at its own rank.
 */
function unorderedBounds(values: Draft): ReadonlyMap<string, FieldProblem> {
  const axes: readonly Axis[] = ["probability_bounds", "severity_bounds"];
  return new Map(
    axes.flatMap((axis) =>
      BOUNDS.slice(1)
        .filter(
          ([rank]) =>
            compareDecimals(
              values[boundField(axis, rank)] ?? "0",
              values[boundField(axis, rank - 1)] ?? "0",
            ) <= 0,
        )
        .map(([rank]) => refusal(boundField(axis, rank), "BOUNDS_NOT_ORDERED")),
    ),
  );
}

/**
 * The thresholds as the server would refuse them: each alert threshold not strictly below the watch
 * threshold of its index (WF-REF-0170).
 */
function brokenThresholds(values: Draft): ReadonlyMap<string, FieldProblem> {
  const field = (name: string) => `index_thresholds/${name}`;
  const alerts = INDICES.filter(
    ([, watch, alert]) =>
      compareDecimals(values[field(alert)] ?? "0", values[field(watch)] ?? "0") >= 0,
  ).map(([, , alert]) => refusal(field(alert), "THRESHOLD_NOT_BELOW_WATCH"));
  return new Map(alerts);
}

/** What a form of the settings is opened with, and what it hands back. */
interface SettingsFormProps {
  /** The settings the form opened on, whose version it writes from. */
  readonly settings: ReferenceSettings;
  readonly onDone: (answer: ReferenceSettings) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}

/** The form of the risk matrix: its six bounds, entered as percentages, and its sixteen zones. */
function RiskForm({ settings, ...handlers }: SettingsFormProps) {
  const t = useTranslations("reference");
  const zone = useTranslations("enums.AlertZone");
  const locale = useLocale();
  const matrix = settings.risk_matrix;
  const bounds = (axis: Axis, group: string): FormField[] =>
    BOUNDS.map(([rank, word]) => ({
      name: boundField(axis, rank),
      label: t(`riskMatrix.${word}`),
      control: "number",
      required: true,
      group,
    }));
  // The highest probability first, as the table of the zones reads.
  const zones = [...LEVELS].reverse().flatMap((probability) =>
    LEVELS.map((severity): FormField => ({
      name: zoneField(zoneRank(probability, severity)),
      label: t("riskZones.severity", { level: severity }),
      control: "choice",
      required: true,
      choices: ZONES.map((value) => [value, zone(value)]),
      group: t("riskZones.probability", { level: probability }),
    })),
  );
  const initial: Draft = Object.fromEntries([
    ...matrix.probability_bounds.map(
      (bound, rank) =>
        [boundField("probability_bounds", rank), editablePercent(bound, locale)] as const,
    ),
    ...matrix.severity_bounds.map(
      (bound, rank) =>
        [boundField("severity_bounds", rank), editablePercent(bound, locale)] as const,
    ),
    ...matrix.zones.map((value, rank) => [zoneField(rank), value] as const),
  ]);
  const ask = (values: Draft) => {
    const ratios = (axis: Axis) =>
      BOUNDS.map(([rank]) => percentRatio(values[boundField(axis, rank)] ?? "0"));
    return updateReferenceSettings({
      risk_matrix: {
        probability_bounds: ratios("probability_bounds"),
        severity_bounds: ratios("severity_bounds"),
        // A choice is one of the zones offered; a zone that is none keeps the one read.
        zones: matrix.zones.map(
          (read, rank) => ZONES.find((value) => value === values[zoneField(rank)]) ?? read,
        ),
      },
      lock_version: settings.lock_version,
    });
  };
  return (
    <ReferenceForm<ReferenceSettings>
      kind="settings"
      title={t("riskForm.modify")}
      hint={t("riskForm.hint")}
      creating={false}
      fields={[
        ...bounds("probability_bounds", t("riskForm.probability")),
        ...bounds("severity_bounds", t("riskForm.severity")),
        ...zones,
      ]}
      initial={initial}
      rules={unorderedBounds}
      ask={ask}
      target="update risk_matrix"
      answering={(answer) => answer}
      {...handlers}
    />
  );
}

/** The form of the thresholds of the two indices and of the delay between two reviews. */
function IndicatorForm({ settings, ...handlers }: SettingsFormProps) {
  const t = useTranslations("reference");
  const locale = useLocale();
  const thresholds = settings.index_thresholds;
  const fields: FormField[] = [
    ...INDICES.flatMap(([index, watch, alert]) =>
      (
        [
          [watch, "watch"],
          [alert, "alert"],
        ] as const
      ).map(([name, word]): FormField => ({
        name: `index_thresholds/${name}`,
        label: t(`indices.${word}`),
        control: "number",
        required: true,
        group: t(`indices.${index}`),
      })),
    ),
    // A whole number of weeks, which the contract counts (WF-REF-0180).
    {
      name: WEEKS,
      label: t("indicatorForm.weeks"),
      control: "whole",
      required: true,
      invalid: t("indicatorForm.weeksInvalid"),
    },
  ];
  const initial: Draft = {
    ...Object.fromEntries(
      INDICES.flatMap(([, ...names]) =>
        names.map((name) => [
          `index_thresholds/${name}`,
          editableDecimal(thresholds[name], locale),
        ]),
      ),
    ),
    [WEEKS]: String(settings.max_weeks_between_reviews),
  };
  const ask = (values: Draft) => {
    const threshold = (name: keyof typeof thresholds) => values[`index_thresholds/${name}`] ?? "";
    return updateReferenceSettings({
      index_thresholds: {
        cost_watch: threshold("cost_watch"),
        cost_alert: threshold("cost_alert"),
        schedule_watch: threshold("schedule_watch"),
        schedule_alert: threshold("schedule_alert"),
      },
      // A whole number of weeks, as the form checked it: a count, not a decimal of the contract.
      max_weeks_between_reviews: Number(values[WEEKS]),
      lock_version: settings.lock_version,
    });
  };
  return (
    <ReferenceForm<ReferenceSettings>
      kind="settings"
      title={t("indicatorForm.modify")}
      hint={t("indicatorForm.hint")}
      creating={false}
      fields={fields}
      initial={initial}
      rules={brokenThresholds}
      ask={ask}
      target="update index_thresholds"
      answering={(answer) => answer}
      {...handlers}
    />
  );
}

/** What the last write did, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/**
 * The settings of a screen with the command that modifies them and its form: the answer of the
 * server shown while it is newer than the settings read, what the last write did said beside the
 * command, a refusal answered once the dialog is gone told above the settings (`Reactivations`).
 */
function SettingsWriter({
  settings,
  command,
  saved,
  form: Form,
  children,
}: {
  readonly settings: ReferenceSettings;
  readonly command: string;
  readonly saved: string;
  readonly form: ComponentType<SettingsFormProps>;
  readonly children: (shown: ReferenceSettings) => ReactNode;
}) {
  const [answered, setAnswered] = useState<ReferenceSettings>();
  // The version the form opened on, which it writes from, and the how-many-th opening it is: none
  // while it is closed. An answer closes only the opening it was sent from, never one opened since.
  const [editing, setEditing] = useState<{ settings: ReferenceSettings; opening: number }>();
  const openings = useRef(0);
  const [said, setSaid] = useState<Said>();
  const trigger = useRef<HTMLButtonElement>(null);
  const shown =
    answered !== undefined && answered.lock_version > settings.lock_version ? answered : settings;
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <Button
          ref={trigger}
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            openings.current += 1;
            setEditing({ settings: shown, opening: openings.current });
          }}
        >
          <Pencil aria-hidden="true" />
          {command}
        </Button>
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
      </div>
      {children(shown)}
      {editing === undefined ? null : (
        <Form
          key={editing.opening}
          settings={editing.settings}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            setSaid((before) => ({ text: saved, count: (before?.count ?? 0) + 1 }));
            setEditing((current) => (current?.opening === editing.opening ? undefined : current));
          }}
          onClose={() => {
            setEditing(undefined);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}

/** The risk matrix, and its form, for a session that may modify the risk settings. */
export function RiskSettings({ settings }: { readonly settings: ReferenceSettings }) {
  const t = useTranslations("reference.riskForm");
  return (
    <SettingsWriter settings={settings} command={t("modify")} saved={t("saved")} form={RiskForm}>
      {(shown) => (
        <>
          <RiskBoundsTable matrix={shown.risk_matrix} />
          <RiskZonesTable matrix={shown.risk_matrix} />
        </>
      )}
    </SettingsWriter>
  );
}

/**
 * The thresholds of the indices and the delay between two reviews, and their form, for a session that
 * may modify the indicator settings.
 */
export function IndicatorSettings({ settings }: { readonly settings: ReferenceSettings }) {
  const t = useTranslations("reference.indicatorForm");
  return (
    <SettingsWriter
      settings={settings}
      command={t("modify")}
      saved={t("saved")}
      form={IndicatorForm}
    >
      {(shown) => (
        <>
          <IndexThresholdTable thresholds={shown.index_thresholds} />
          <ReviewDelay weeks={shown.max_weeks_between_reviews} />
        </>
      )}
    </SettingsWriter>
  );
}
