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
 * component may share with a client one of the shell (#251) —; an empty list says it is. The pieces
 * offer no command themselves: those of the sub-projects and of the contributors are their
 * components' (`subproject-commands.tsx`, `contributor-commands.tsx`, EP-02/L44b); the history of
 * the states is read only.
 */
import { ArrowRight, Bot, History, type LucideIcon, User } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { KeptName } from "@/components/account/anonymized-name";
import { LocalTime } from "@/components/local-time";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import { SectionCard, type SectionCardProps } from "@/components/shell/section-card";
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

/**
 * A list of a project in the card of its section (`SectionCard`, US-2130): under its title with its
 * icon, its commands at the right of the title, and the sentence that says it is empty. A server
 * screen gives the principal command; a client component never hands it on (typescript.md, defect
 * 12).
 */
export function ListCard({
  title,
  icon,
  empty,
  principal,
  footer,
  children,
}: {
  readonly title: string;
  readonly icon: LucideIcon;
  /** What the card says when the list is empty; `undefined` when it is not. */
  readonly empty: string | undefined;
  readonly principal?: SectionCardProps["principal"];
  /** What stays under the list, whether it is empty or not. */
  readonly footer?: ReactNode;
  readonly children: ReactNode;
}) {
  return (
    <SectionCard title={title} icon={icon} principal={principal}>
      <div className="flex min-w-0 flex-col gap-3">
        {empty === undefined ? children : <p className="text-sm text-muted-foreground">{empty}</p>}
        {footer}
      </div>
    </SectionCard>
  );
}

/**
 * A table of a list, named by its title, with its column headers, in a group of the same name that
 * the keyboard reaches, and scrolls when the list overflows its box.
 */
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
    <Table aria-label={label} list={label} className="w-full">
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

/**
 * Who made a transition: the name of their account — the neutral label for an account anonymised
 * since (WF-ADM-0060) —, or an automatic process of the platform.
 */
export function Actor({ actor }: { readonly actor: StateTransition["actor"] }) {
  const t = useTranslations("enums.ActorRef.kind");
  const Icon = actor.kind === "platform" ? Bot : User;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon aria-hidden="true" className={ICON} />
      {actor.kind === "user" && actor.display_name !== undefined ? (
        <KeptName name={actor.display_name} />
      ) : (
        t(actor.kind)
      )}
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
    <ListCard
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
    </ListCard>
  );
}
