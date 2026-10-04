// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of a project, in dense tables, in the order the server gave them (US-0210): its
 * sub-projects, each by the code the ERP knows it by, and whether actual costs are charged to it
 * (WF-PRJ-0050); its contributors, and whether their account is still active (WF-PRJ-0060); the
 * history of its states, each transition dated when it occurred and by whom (WF-CYC-0130). Each
 * table is a section under its title; an empty list says it is. Nothing is offered to create or
 * modify: those forms belong to the epic of their domain.
 */
import {
  ArrowRight,
  Bot,
  FolderTree,
  History,
  type LucideIcon,
  User,
  Users,
  UserX,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useId } from "react";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { Badge } from "@/components/ui/badge";
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
type StateTransition = components["schemas"]["StateTransition"];

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
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-2">
      <h2 id={id} className="flex items-center gap-2 text-base font-semibold">
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

/** The contributors of a project, each by the name of their account, and whether it is active. */
export function ContributorList({
  contributors,
}: {
  readonly contributors: readonly Contributor[];
}) {
  const t = useTranslations("projectLists.contributors");
  return (
    <ListSection
      title={t("title")}
      icon={Users}
      empty={contributors.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("name"), t("account")]}>
        {contributors.map((contributor) => (
          <TableRow key={contributor.user_id}>
            <TableCell className={CELL}>
              <span className="inline-flex items-center gap-1.5">
                <User aria-hidden="true" className={ICON} />
                {contributor.display_name}
              </span>
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

/** Who made a transition: the name of their account, or an automatic process of the platform. */
function Actor({ actor }: { readonly actor: StateTransition["actor"] }) {
  const t = useTranslations("enums.ActorRef.kind");
  const Icon = actor.kind === "platform" ? Bot : User;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon aria-hidden="true" className={ICON} />
      {actor.display_name ?? t(actor.kind)}
    </span>
  );
}

/** The history of the states of a project, from its creation to its current state. */
export function TransitionList({
  transitions,
}: {
  readonly transitions: readonly StateTransition[];
}) {
  const t = useTranslations("projectLists.transitions");
  const state = useTranslations("enums.ProjectState");
  return (
    <ListSection
      title={t("title")}
      icon={History}
      empty={transitions.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("occurredAt"), t("change"), t("actor")]}>
        {transitions.map((transition) => (
          <TableRow key={`${transition.occurred_at}:${transition.to_state}`}>
            <TableCell className={CELL}>
              <LocalTime value={transition.occurred_at} />
            </TableCell>
            <TableCell className={CELL}>
              <span className="inline-flex items-center gap-1.5">
                {transition.from_state == null ? t("creation") : state(transition.from_state)}
                <ArrowRight aria-label={t("to")} role="img" className={ICON} />
                <Badge>{state(transition.to_state)}</Badge>
              </span>
            </TableCell>
            <TableCell className={CELL}>
              <Actor actor={transition.actor} />
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}
