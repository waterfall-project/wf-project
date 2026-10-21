// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The comparison of two marked revisions of a project (FBS-4.1, US-0210): the choice of the two,
 * among the marked revisions of the history, which the address carries — `from_revision_id` and
 * `to_revision_id`, named as the contract names them —, and what `compareRevisions` gives for
 * them, as it gives it (WF-REV-0080): the tasks and lines added, removed and changed, each change
 * named, and the deviations of amounts by nature of cost and by sub-project.
 *
 * The server pairs the two revisions by the lineage of their objects (WF-DAT-0030) and marks each
 * node of the compared tree with its `difference` (C-361): the front pairs nothing, sums nothing
 * and orders nothing (WF-ARC-0020). It only splits the nodes the server gives — its `items`, read
 * as `listNodes` reads a structure (#1193) — into three parts by the mark the server gave them —
 * added, removed, changed —, keeping the order of the plan within each, and leaves the unchanged
 * ones out — the dense grid of the whole tree comes with US-0500/L4. Each deviation is named by the label the API resolves (#204); one it leaves out is
 * said missing, never replaced by an identifier.
 */
import { Calculator, ClipboardList, GitCompareArrows, type LucideIcon } from "lucide-react";
import Form from "next/form";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { CELL, ICON, ListSection, ListTable } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/i18n/format";
import {
  type ProjectContext,
  REVISION_PARAMETER,
  type SearchParameters,
  UNASSIGNED,
} from "@/navigation/context";

import { type NamedRevision, useRevisionName } from "./revision-history";

/** A comparison of two revisions, as the API renders it. */
export type RevisionComparison = components["schemas"]["RevisionComparison"];

/**
 * A node of the comparison, as `fields` reduces it (#1208): only its address and its mark are always
 * rendered, the rest when `fields` names it.
 */
type ComparisonNode = components["schemas"]["ComparedNodeRead"];
type NodeDifference = components["schemas"]["NodeDifference"];
type NodeKind = components["schemas"]["NodeKind"];
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

/** The icon of each kind of node: a task, a line of the estimate. */
const KIND_ICONS: Readonly<Record<NodeKind, LucideIcon>> = {
  task: ClipboardList,
  estimate_line: Calculator,
};

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
}

/** The context the choice carries on: the revision of the screen, and its filters. */
function ContextFields({ context }: { readonly context: ProjectContext }) {
  const carried = [...context.parameters];
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
}: Pick<RevisionComparisonProps, "action" | "context" | "compared"> & {
  readonly marked: readonly NamedRevision[];
}) {
  const t = useTranslations("revisionScreen.comparison");
  return (
    <Form action={action} scroll={false} className="flex flex-wrap items-end gap-3">
      <ContextFields context={context} />
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

/** The kind of a node, its icon and its name; nothing when `fields` leaves it out. */
function KindOf({ kind }: { readonly kind: NodeKind | undefined }) {
  const name = useTranslations("enums.NodeKind");
  if (kind === undefined) {
    return null;
  }
  const Icon = KIND_ICONS[kind];
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon aria-hidden="true" className={ICON} />
      {name(kind)}
    </span>
  );
}

/** The tasks and lines of one part — added, removed, changed —, and what changed of each. */
function Nodes({
  title,
  none,
  nodes,
  withChanges,
}: {
  readonly title: string;
  readonly none: string;
  readonly nodes: readonly ComparisonNode[];
  readonly withChanges: boolean;
}) {
  const t = useTranslations("revisionScreen.comparison");
  const change = useTranslations("enums.NodeChange");
  const columns = [t("label"), t("kind"), ...(withChanges ? [t("changes")] : [])];
  return (
    <Part title={title} empty={nodes.length === 0 ? none : undefined}>
      <ListTable label={title} columns={columns}>
        {nodes.map((node) => (
          // Keyed by `node_id`, always rendered, and not by `lineage_id`, which `fields` leaves
          // out when the screen does not name it (#1208): no two nodes of a reading share it.
          <TableRow key={node.node_id}>
            <TableCell className={`${CELL} whitespace-normal`}>{labelOf(node)}</TableCell>
            <TableCell className={CELL}>
              <KindOf kind={node.kind} />
            </TableCell>
            {withChanges ? (
              <TableCell className={CELL}>
                <span className="flex flex-wrap gap-1">
                  {node.changes.map((name) => (
                    <Badge key={name} variant="outline">
                      {change(name)}
                    </Badge>
                  ))}
                </span>
              </TableCell>
            ) : null}
          </TableRow>
        ))}
      </ListTable>
    </Part>
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
              {formatMoney(delta.delta, locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </Part>
  );
}

/** The label of a node, that of its task or of its line. */
function labelOf(node: ComparisonNode): string | undefined {
  return (node.task ?? node.estimate_line)?.label;
}

/**
 * The nodes of the compared tree the server marked so, in the order of the plan. A changed node is
 * one of which something changes itself (`changes`): a task marked modified for its content only
 * — a line or a sub-task added, removed or changed — is not one, its content saying it.
 */
function marked(nodes: readonly ComparisonNode[], difference: NodeDifference): ComparisonNode[] {
  return nodes.filter(
    (node) =>
      node.difference === difference && (difference !== "modified" || node.changes.length > 0),
  );
}

/** What the API gives for the two revisions compared. */
function ComparisonResult({ comparison }: { readonly comparison: RevisionComparison }) {
  const t = useTranslations("revisionScreen.comparison");
  return (
    <div className="space-y-3">
      <Nodes
        title={t("added")}
        none={t("noneAdded")}
        nodes={marked(comparison.items, "added")}
        withChanges={false}
      />
      <Nodes
        title={t("removed")}
        none={t("noneRemoved")}
        nodes={marked(comparison.items, "removed")}
        withChanges={false}
      />
      <Nodes
        title={t("changed")}
        none={t("noneChanged")}
        nodes={marked(comparison.items, "modified")}
        withChanges
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
}: RevisionComparisonProps) {
  const t = useTranslations("revisionScreen.comparison");
  const marked = revisions.filter((revision) => revision.status === "marked");
  return (
    <ListSection
      title={t("title")}
      icon={GitCompareArrows}
      empty={marked.length < 2 ? t("needsTwo") : undefined}
    >
      <ComparisonForm marked={marked} action={action} context={context} compared={compared} />
      {comparison === undefined ? null : <ComparisonResult comparison={comparison} />}
    </ListSection>
  );
}
