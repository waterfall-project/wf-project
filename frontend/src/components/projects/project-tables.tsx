// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of a project, in dense tables, in the order the server gave them (US-0210): its
 * sub-projects, each by the code the ERP knows it by, and whether actual costs are charged to it
 * (WF-PRJ-0050); its contributors, the project manager told from the others, and whether their
 * account is still active (WF-PRJ-0060); its work breakdown, each order item with its work packages
 * and their deliverables (WF-PRJ-0020); the history of its states, each transition dated when it
 * occurred, its states by their badge, by whom, and with the motive given to confirm an exit, if any (WF-CYC-0130). Each
 * table is a section under its title — named by `aria-label`, never by an identifier of `useId`,
 * which a server component may share with a client one of the shell (#251) —; an empty list says
 * it is. Nothing is offered to create or modify: those forms belong to the epic of their domain.
 */
import {
  ArrowRight,
  Bot,
  FolderTree,
  History,
  ListTree,
  type LucideIcon,
  User,
  UserCog,
  Users,
  UserX,
} from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { Badge } from "@/components/ui/badge";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Subproject = components["schemas"]["Subproject"];
type Contributor = components["schemas"]["Contributor"];
type WorkBreakdown = components["schemas"]["WorkBreakdown"];
type OrderItem = components["schemas"]["OrderItem"];
type WorkPackage = components["schemas"]["WorkPackage"];
type StateTransition = components["schemas"]["StateTransition"];

/** A row of the work breakdown: a work package of an order item, or the order item without one. */
interface BreakdownRow {
  readonly key: string;
  readonly item: OrderItem;
  readonly workPackage: WorkPackage | undefined;
}

/** The padding of a cell of a dense list. */
export const CELL = "py-1.5";
/** An icon before a text of a list, hidden from a screen reader by whoever draws it. */
export const ICON = "size-4 shrink-0 text-muted-foreground";

/** A list of a project under its title, with its icon; the sentence that says it is empty. */
export function ListSection({
  title,
  icon: Icon,
  empty,
  children,
}: {
  readonly title: string;
  readonly icon: LucideIcon;
  /** What the section says when the list is empty; `undefined` when it is not. */
  readonly empty: string | undefined;
  readonly children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <Icon aria-hidden="true" className={ICON} />
        {title}
      </h2>
      {empty === undefined ? children : <p className="text-sm text-muted-foreground">{empty}</p>}
    </section>
  );
}

/** A table of a list, named by its title, with its column headers. */
export function ListTable({
  label,
  columns,
  children,
}: {
  readonly label: string;
  readonly columns: readonly string[];
  readonly children: ReactNode;
}) {
  return (
    <Table aria-label={label} className="w-full">
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column} className={CELL}>
              {column}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>{children}</TableBody>
    </Table>
  );
}

/** The sub-projects of a project, each by its code, its label, and its actual costs. */
export function SubprojectList({ subprojects }: { readonly subprojects: readonly Subproject[] }) {
  const t = useTranslations("projectLists.subprojects");
  return (
    <ListSection
      title={t("title")}
      icon={FolderTree}
      empty={subprojects.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("code"), t("label"), t("actualCosts")]}>
        {subprojects.map((subproject) => (
          <TableRow key={subproject.subproject_id}>
            <TableCell className={CELL}>{subproject.code}</TableCell>
            <TableCell className={CELL}>{subproject.label}</TableCell>
            <TableCell className={CELL}>
              {t(subproject.has_actual_costs ? "charged" : "notCharged")}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}

/**
 * The contributors of a project, each by the name of their account, their capacity — the project
 * manager marked by an icon besides its name, readable without colour —, and whether their
 * account is active.
 */
export function ContributorList({
  contributors,
}: {
  readonly contributors: readonly Contributor[];
}) {
  const t = useTranslations("projectLists.contributors");
  const kind = useTranslations("enums.ContributorKind");
  return (
    <ListSection
      title={t("title")}
      icon={Users}
      empty={contributors.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("name"), t("kind"), t("account")]}>
        {contributors.map((contributor) => (
          <TableRow key={contributor.user_id}>
            <TableCell className={CELL}>
              <span className="inline-flex items-center gap-1.5">
                <User aria-hidden="true" className={ICON} />
                {contributor.display_name}
              </span>
            </TableCell>
            <TableCell className={CELL}>
              {contributor.kind === "project_manager" ? (
                <span className="inline-flex items-center gap-1.5">
                  <UserCog aria-hidden="true" className={ICON} />
                  {kind(contributor.kind)}
                </span>
              ) : (
                kind(contributor.kind)
              )}
            </TableCell>
            <TableCell className={CELL}>
              {contributor.is_active ? (
                t("active")
              ) : (
                <Badge variant="outline">
                  <UserX aria-hidden="true" />
                  {t("inactive")}
                </Badge>
              )}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}

/**
 * The work breakdown of a project, as its order was entered (WF-PRJ-0020): a row for each work
 * package, under the label of its order item, with its deliverables; an order item without a work
 * package says so on a row of its own.
 */
export function WorkBreakdownList({ breakdown }: { readonly breakdown: WorkBreakdown }) {
  const t = useTranslations("projectLists.workBreakdown");
  const rows = breakdown.order_items.flatMap((item): BreakdownRow[] =>
    item.work_packages.length === 0
      ? [{ key: item.order_item_id, item, workPackage: undefined }]
      : item.work_packages.map((workPackage) => ({
          key: workPackage.work_package_id,
          item,
          workPackage,
        })),
  );
  return (
    <ListSection
      title={t("title")}
      icon={ListTree}
      empty={rows.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("orderItem"), t("workPackage"), t("deliverables")]}>
        {rows.map(({ key, item, workPackage }) => (
          <TableRow key={key}>
            <TableCell className={CELL}>{item.label}</TableCell>
            <TableCell className={CELL}>{workPackage?.label ?? t("noWorkPackage")}</TableCell>
            <TableCell className={CELL}>
              {workPackage === undefined || workPackage.deliverables.length === 0 ? (
                t("noDeliverable")
              ) : (
                <ul>
                  {workPackage.deliverables.map((deliverable) => (
                    <li key={deliverable.deliverable_id}>{deliverable.label}</li>
                  ))}
                </ul>
              )}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}

/** Who made a transition: the name of their account, or an automatic process of the platform. */
export function Actor({ actor }: { readonly actor: StateTransition["actor"] }) {
  const t = useTranslations("enums.ActorRef.kind");
  const Icon = actor.kind === "platform" ? Bot : User;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon aria-hidden="true" className={ICON} />
      {actor.display_name ?? t(actor.kind)}
    </span>
  );
}

/**
 * The history of the states of a project, from its creation to its current state; the motive of
 * an exit as the user gave it, a transition without one left blank rather than said lacking.
 */
export function TransitionList({
  transitions,
}: {
  readonly transitions: readonly StateTransition[];
}) {
  const t = useTranslations("projectLists.transitions");
  return (
    <ListSection
      title={t("title")}
      icon={History}
      empty={transitions.length === 0 ? t("none") : undefined}
    >
      <ListTable
        label={t("title")}
        columns={[t("occurredAt"), t("change"), t("actor"), t("reason")]}
      >
        {transitions.map((transition) => (
          <TableRow key={`${transition.occurred_at}:${transition.to_state}`}>
            <TableCell className={CELL}>
              <LocalTime value={transition.occurred_at} />
            </TableCell>
            <TableCell className={CELL}>
              <span className="inline-flex items-center gap-1.5">
                {transition.from_state == null ? (
                  t("creation")
                ) : (
                  <ProjectStateBadge state={transition.from_state} />
                )}
                <ArrowRight aria-label={t("to")} role="img" className={ICON} />
                <ProjectStateBadge state={transition.to_state} />
              </span>
            </TableCell>
            <TableCell className={CELL}>
              <Actor actor={transition.actor} />
            </TableCell>
            <TableCell className={CELL}>{transition.reason}</TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}
