// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces the screens of the reference data share (US-0250): a section under its title, named
 * by it — by `aria-label`, never by an identifier of `useId`, which a server component may share
 * with a client one of the shell (#251) —; the state of an object, active or deactivated — a
 * deactivated one stays readable (WF-REF-0150) —; and the name of an object another one is
 * attached to, by the list the page read, or said unknown — never its identifier.
 */
import { CircleOff, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ICON } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";

/** A list or a set of values of the reference data, under its title. */
export function ReferenceSection({
  title,
  icon: Icon,
  empty,
  children,
}: {
  readonly title: string;
  readonly icon: LucideIcon;
  /** What the section says when its list is empty; `undefined` when it is not. */
  readonly empty?: string | undefined;
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

/**
 * The names of the objects of a list by their identifier, and the name of one: the label the list
 * gives it, or « unknown » for one it does not hold — never the identifier.
 */
export function namesOf<T>(
  items: readonly T[],
  id: (item: T) => string,
  label: (item: T) => string,
  unknown: string,
): (id: string) => string {
  const names = new Map(items.map((item) => [id(item), label(item)]));
  return (key) => names.get(key) ?? unknown;
}
