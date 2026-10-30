// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The comparison of two marked revisions of a project (FBS-4.1, US-0210, US-0500): the choice of
 * the two, among the marked revisions of the history, which the address carries —
 * `from_revision_id` and `to_revision_id`, named as the contract names them —, and what
 * `compareRevisions` gives for them, as it gives it (WF-REV-0080): the tree of the revision
 * compared in the dense grid of the structures, each node with the mark of its difference, and the
 * deviations of amounts by nature of cost and by sub-project.
 *
 * The server pairs the two revisions by the lineage of their objects (WF-DAT-0030) and marks each
 * node of the compared tree with its `difference` (C-361): the front pairs nothing, sums nothing
 * and orders nothing (WF-ARC-0020). It reads the nodes the server gives — its `items`, read as
 * `listNodes` reads a structure (#1193), reduced to the fields the grid shows (`fields`, #1201) —
 * and hands them to the grid, which marks them as it marks a differential (`ComparisonGrid`). Each
 * deviation is named by the label the API resolves (#204); one it leaves out is said missing,
 * never replaced by an identifier.
 */
import { GitCompareArrows } from "lucide-react";
import Form from "next/form";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { DifferencesOnly } from "@/components/grid/differences-only";
import { DIFFERENCE_PARAMETER, type DifferenceValue } from "@/components/grid/difference-filter";
import { CELL, ListSection, ListTable } from "@/components/projects/project-tables";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { TableCell, TableRow } from "@/components/ui/table";
import type { GridPreferences } from "@/components/grid/settings";
import { formatMoney } from "@/i18n/format";
import {
  type ProjectContext,
  REVISION_PARAMETER,
  type SearchParameters,
  UNASSIGNED,
} from "@/navigation/context";

import { ComparisonGrid } from "./comparison-grid";
import { comparisonRows } from "./comparison-rows";
import { type NamedRevision, useRevisionName } from "./revision-history";

/** A comparison of two revisions, as the API renders it. */
export type RevisionComparison = components["schemas"]["RevisionComparison"];

type AmountDelta = RevisionComparison["amount_deltas"][number];

/** The two revisions the address asks to compare, as the contract names them. */
export interface ComparedRevisions {
  readonly from_revision_id: string;
  readonly to_revision_id: string;
}

/** The two revisions an address asks to compare, or `undefined` unless it names both. */
export function comparedRevisions(search: SearchParameters): ComparedRevisions | undefined {
  const from = search.get("from_revision_id");
  const to = search.get("to_revision_id");
  return from === null || from === "" || to === null || to === ""
    ? undefined
    : { from_revision_id: from, to_revision_id: to };
}

/** What the comparison of a screen of the revisions shows. */
export interface RevisionComparisonProps {
  /** The revisions of the history, in the order of the server; the marked ones are offered. */
  readonly revisions: readonly NamedRevision[];
  /** The path of the screen, which the choice leads back to. */
  readonly action: string;
  /** The context of the screen, which the choice carries on. */
  readonly context: ProjectContext;
  /** The two revisions the address asks to compare, if it asks. */
  readonly compared: ComparedRevisions | undefined;
  /** What the API gives for them, if they were asked. */
  readonly comparison: RevisionComparison | undefined;
  /** The differences the address retains (`difference`, US-0700); none, every node. */
  readonly difference: readonly DifferenceValue[] | undefined;
  /** The settings of the grid of the comparison the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** The context the choice carries on: the revision of the screen, and its filters. */
function ContextFields({
  context,
  difference,
}: {
  readonly context: ProjectContext;
  readonly difference: readonly DifferenceValue[] | undefined;
}) {
  const carried = [...context.parameters];
  if (difference !== undefined) {
    carried.push([DIFFERENCE_PARAMETER, difference.join(",")]);
  }
  if (context.revisionId !== undefined) {
    carried.unshift([REVISION_PARAMETER, context.revisionId]);
  }
  return carried.map(([name, value]) => (
    <input key={name} type="hidden" name={name} value={value} />
  ));
}

/** A select of one of the two revisions, among the marked ones. */
function RevisionSelect({
  name,
  label,
  marked,
  selected,
}: {
  readonly name: keyof ComparedRevisions;
  readonly label: string;
  readonly marked: readonly NamedRevision[];
  readonly selected: string | undefined;
}) {
  // An identifier of its own, from the name of the field: never one of `useId` (#251).
  const id = `comparison-${name}`;
  const revisionName = useRevisionName();
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect id={id} name={name} defaultValue={selected}>
        {marked.map((revision) => (
          <option key={revision.revision_id} value={revision.revision_id}>
            {revisionName(revision)}
          </option>
        ))}
      </NativeSelect>
    </div>
  );
}

/**
 * The choice of the two revisions: by default, as the server lists the most recent first, the
 * second marked revision compared to the first — the one before it.
 */
function ComparisonForm({
  marked,
  action,
  context,
  compared,
  difference,
}: Pick<RevisionComparisonProps, "action" | "context" | "compared" | "difference"> & {
  readonly marked: readonly NamedRevision[];
}) {
  const t = useTranslations("revisionScreen.comparison");
  return (
    <Form action={action} scroll={false} className="flex flex-wrap items-end gap-3">
      <ContextFields context={context} difference={difference} />
      <RevisionSelect
        name="from_revision_id"
        label={t("from")}
        marked={marked}
        selected={compared?.from_revision_id ?? marked[1]?.revision_id}
      />
      <RevisionSelect
        name="to_revision_id"
        label={t("to")}
        marked={marked}
        selected={compared?.to_revision_id ?? marked[0]?.revision_id}
      />
      <Button type="submit" variant="outline" size="sm">
        <GitCompareArrows aria-hidden="true" />
        {t("compare")}
      </Button>
    </Form>
  );
}

/** A part of the result under its title; the sentence that says it is empty. */
function Part({
  title,
  empty,
  children,
}: {
  readonly title: string;
  /** What the part says when it is empty; `undefined` when it is not. */
  readonly empty: string | undefined;
  readonly children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-1">
      <h3 className="text-sm font-semibold">{title}</h3>
      {empty === undefined ? children : <p className="text-sm text-muted-foreground">{empty}</p>}
    </section>
  );
}

/** The deviations of amounts, by nature of cost and by sub-project, in the order of the server. */
function Deltas({ deltas }: { readonly deltas: readonly AmountDelta[] }) {
  const t = useTranslations("revisionScreen.comparison");
  const dimension = useTranslations("enums.RevisionComparison.amount_deltas.dimension");
  const unassigned = useTranslations("enums.Scope")("unassigned");
  const locale = useLocale();
  return (
    <Part title={t("deltas")} empty={deltas.length === 0 ? t("noDeltas") : undefined}>
      <ListTable label={t("deltas")} columns={[t("dimension"), t("key"), t("delta")]}>
        {deltas.map((delta) => (
          <TableRow key={`${delta.dimension}:${delta.key}`}>
            <TableCell className={CELL}>{dimension(delta.dimension)}</TableCell>
            <TableCell className={CELL}>
              {delta.key === UNASSIGNED ? unassigned : (delta.label ?? t("unnamed"))}
            </TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {formatMoney(delta.reestimated_delta, locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </Part>
  );
}

/** What the API gives for the two revisions compared. */
function ComparisonResult({
  comparison,
  difference,
  preferences,
}: {
  readonly comparison: RevisionComparison;
  readonly difference: readonly DifferenceValue[] | undefined;
  readonly preferences: GridPreferences | undefined;
}) {
  return (
    <div className="space-y-3">
      <DifferencesOnly filter={difference} />
      <ComparisonGrid
        rows={comparisonRows(comparison.items)}
        totals={comparison.totals}
        preferences={preferences}
      />
      <Deltas deltas={comparison.amount_deltas} />
    </div>
  );
}

/**
 * Render the comparison of two revisions: the choice of the two among the marked ones — or that
 * a comparison takes two —, and what the API gives for those the address asks.
 */
export function RevisionComparisonSection({
  revisions,
  action,
  context,
  compared,
  comparison,
  difference,
  preferences,
}: RevisionComparisonProps) {
  const t = useTranslations("revisionScreen.comparison");
  const marked = revisions.filter((revision) => revision.status === "marked");
  return (
    <ListSection
      title={t("title")}
      icon={GitCompareArrows}
      empty={marked.length < 2 ? t("needsTwo") : undefined}
    >
      <ComparisonForm
        marked={marked}
        action={action}
        context={context}
        compared={compared}
        difference={difference}
      />
      {comparison === undefined ? null : (
        <ComparisonResult
          comparison={comparison}
          difference={difference}
          preferences={preferences}
        />
      )}
    </ListSection>
  );
}
