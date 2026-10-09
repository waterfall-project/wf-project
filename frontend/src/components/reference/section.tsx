// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces the screens of the reference data share (US-0250): a section under its title, named
 * by it — by `aria-label`, never by an identifier of `useId`, which a server component may share
 * with a client one of the shell (#251) —; the state of an object, active or deactivated — a
 * deactivated one stays readable (WF-REF-0150) —; what stands for a list whose bounds the API
 * refused (#545); the body of a list, its grid within the region that tells the refusals of its
 * commands (`ListBody`).
 */
import { CircleOff, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ICON } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";

import { Reactivations } from "./reactivation";

/** A list or a set of values of the reference data, under its title. */
export function ReferenceSection({
  title,
  icon: Icon,
  empty,
  fill = false,
  commands,
  children,
}: {
  readonly title: string;
  readonly icon: LucideIcon;
  /** What the section says when its list is empty; `undefined` when it is not. */
  readonly empty?: string | undefined;
  /**
   * Whether the section fills what its screen leaves it — the one grid of a screen that fills the
   * window (`Screen fill`) —, the grid shrinking to it.
   */
  readonly fill?: boolean;
  /** The commands of the section beside its title — a creation —, offered even on an empty list. */
  readonly commands?: ReactNode;
  readonly children: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className={fill ? "flex min-h-0 flex-1 flex-col gap-2" : "space-y-2"}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <Icon aria-hidden="true" className={ICON} />
          {title}
        </h2>
        {commands}
      </div>
      {empty === undefined ? children : <p className="text-sm text-muted-foreground">{empty}</p>}
    </section>
  );
}

/** Whether an object is active, or deactivated — said by a mark and a word, not by colour. */
export function ActiveState({ active }: { readonly active: boolean }) {
  const t = useTranslations("reference.state");
  return active ? (
    t("active")
  ) : (
    <Badge variant="outline">
      <CircleOff aria-hidden="true" />
      {t("inactive")}
    </Badge>
  );
}

/** What stands for the grid of a list whose bounds the API refused (422), the list unread. */
export function BoundsRefused() {
  const t = useTranslations("reference");
  return <p className="text-sm text-destructive">{t("boundsRefused")}</p>;
}

/**
 * The body of a list: its filters, its grid and its pages — or, empty with nothing narrowing it, what
 * says so; its bounds refused, what stands for its grid, its filters kept —, the grid within the
 * region that tells the refusals of its commands, where its form opens too (`dialog`), on an empty
 * list as well.
 */
export function ListBody({
  empty,
  refused = false,
  reads,
  filters,
  grid,
  pages,
  dialog,
}: {
  /** What the list says when it is empty and nothing narrows it; `undefined` when it is not. */
  readonly empty: string | undefined;
  /** Whether the API refused the bounds of the list (422), which is then unread. */
  readonly refused?: boolean;
  /** The parameters of the address the list reads (`listReads`). */
  readonly reads: readonly string[];
  readonly filters: ReactNode;
  readonly grid: ReactNode;
  readonly pages?: ReactNode;
  /** The dialog of the form of the list, rendered while its commands have one open. */
  readonly dialog: ReactNode;
}) {
  const body =
    empty === undefined ? grid : <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <>
      {empty === undefined ? filters : null}
      <Reactivations reads={reads}>
        {refused ? <BoundsRefused /> : body}
        {dialog}
      </Reactivations>
      {empty === undefined && !refused ? pages : null}
    </>
  );
}
