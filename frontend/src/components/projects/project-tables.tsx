// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of a project that are no tables of data, in dense tables, in the order the server gave
 * them (US-0210): the history of its states, each transition dated when it occurred, its states by
 * their badge (#523), by whom, and with the motive given to confirm an exit, if any (WF-CYC-0130) —
 * a list read, which stays a list (decision of the author on #301, 2026-10-08) —; and the pieces
 * the lists of the screens share: a section under its title, a table under its column headers. The
 * lists of the settings of a project are dense grids (`settings-lists.tsx`). Each list is a section
 * under its title — named by `aria-label`, never by an identifier of `useId`, which a server
 * component may share with a client one of the shell (#251) —; an empty list says it is. Nothing
 * is offered to create or modify: those forms belong to the epic of their domain.
 */
import { ArrowRight, Bot, History, type LucideIcon, User } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
