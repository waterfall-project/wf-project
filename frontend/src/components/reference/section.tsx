// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces the screens of the reference data share (US-0250): a section under its title, named
 * by it — by `aria-label`, never by an identifier of `useId`, which a server component may share
 * with a client one of the shell (#251) —, in its card on a screen recomposed by EP-25
 * (`ReferenceCard`), bare on the others until their lot recomposes them (`ReferenceSection`); the
 * state of an object, active or deactivated — a deactivated one stays readable (WF-REF-0150) —;
 * what stands for a list whose bounds the API refused (#545); the body of a list, its grid within
 * the region that tells the refusals of its commands (`ListBody`).
 */
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ICON } from "@/components/projects/project-tables";
import { type Principal, SectionCard } from "@/components/shell/section-card";
import { ActivityBadge } from "@/components/ui/activity-badge";

import { Reactivations } from "./reactivation";

/**
 * A list or a set of values of the reference data in its card (US-2080, #3071): its title, the
 * command that creates in it at the right of the title — filled, the one filled command of the
 * card (`SectionCard`) —, offered on an empty list too, and its body (`ListBody` says an empty list). The screen gives the creation as a function of the variant the card draws it at, never
 * the variant itself.
 */
export function ReferenceCard({
  title,
  icon,
  creation,
  children,
}: {
  readonly title: string;
  readonly icon: LucideIcon;
  /** The command that creates an object of the list; none for a session that does not write. */
  readonly creation?: Principal["command"] | undefined;
  readonly children: ReactNode;
}) {
  return (
    <SectionCard
      title={title}
      icon={icon}
      principal={creation === undefined ? undefined : { does: "create", command: creation }}
    >
      <div className="flex min-w-0 flex-col gap-2">{children}</div>
    </SectionCard>
  );
}

/**
 * A list or a set of values of the reference data, under its title, bare: the screens EP-25 has not
 * recomposed in cards yet (`ReferenceCard`).
 */
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

/**
 * Whether an object is active, or deactivated — « Actif » by a dot and its word, « Désactivé » by
 * its outlined mark and its word: by their shape and their word, never by colour alone
 * (`ActivityBadge`, WF-IHM-0070, #3079).
 */
export function ActiveState({ active }: { readonly active: boolean }) {
  const t = useTranslations("reference.state");
  return <ActivityBadge active={active}>{active ? t("active") : t("inactive")}</ActivityBadge>;
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
 * list as well. A list whose filters are folded into the bar of its grid (`folded`) shows them
 * above only when the bounds were refused.
 */
export function ListBody({
  empty,
  refused = false,
  folded = false,
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
  /**
   * Whether the filters are folded into the bar of the grid (#2916): they stand above the list only
   * where there is no grid — a list unread because its bounds were refused.
   */
  readonly folded?: boolean;
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
      {empty === undefined && (!folded || refused) ? filters : null}
      <Reactivations reads={reads}>
        {refused ? <BoundsRefused /> : body}
        {dialog}
      </Reactivations>
      {empty === undefined && !refused ? pages : null}
    </>
  );
}
