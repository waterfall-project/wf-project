// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The navigation of the shell (WF-IHM-0010): the functions of the FBS the session may read,
 * drawn from `functions.json`. The functions outside any project are reached without opening
 * one; in a project, the links carry its context — the revision read, the filtered
 * sub-project, the calculation date —, and a project without a revision offers the functions
 * of the project itself; outside, a link leads back to the last project
 * context, which a cookie of the front keeps across visits. When the session cannot be read,
 * the status screen is still offered, alone: it is what is consulted when nothing else works
 * (WF-ADM-0130).
 *
 * A client component: the shell persists from one page to the next, and only the browser
 * knows the address it now shows.
 */
"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import type { components } from "@/api/generated/schema";
import {
  contextAddress,
  contextCookie,
  type ProjectContext,
  readContext,
} from "@/navigation/context";
import {
  diagnosticGroups,
  type FunctionGroup,
  functionHref,
  readableGroups,
} from "@/navigation/functions";

/** What the navigation offers, and where it leads back to. */
export interface NavigationProps {
  /**
   * The effective permissions of the session, or `unreadable` when the session could not be
   * read: the status screen alone is offered then (`diagnosticGroups`).
   */
  readonly permissions: readonly components["schemas"]["PermissionCode"][] | "unreadable";
  /** The address of the last project context, from the cookie of the request. */
  readonly remembered: string | undefined;
}

const LINK = "block rounded-md px-2 py-1 hover:bg-accent hover:text-accent-foreground";
const CURRENT = "aria-[current=page]:bg-accent aria-[current=page]:font-medium";

/** The links of a group, in the context of the page shown. */
function GroupLinks({
  group,
  context,
  pathname,
}: {
  readonly group: FunctionGroup;
  readonly context: ProjectContext | undefined;
  readonly pathname: string;
}) {
  const t = useTranslations();
  const links = group.functions
    .map((fn) => ({ fn, href: functionHref(fn, context) }))
    .filter((link): link is { fn: typeof link.fn; href: string } => link.href !== undefined);
  return links.length === 0 ? null : (
    <ul className="space-y-1">
      {links.map(({ fn, href }) => (
        <li key={fn.code}>
          <Link
            href={href}
            aria-current={href.split("?")[0] === pathname ? "page" : undefined}
            className={`${LINK} ${CURRENT}`}
          >
            {t(fn.label)}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Render the functions the session may read, in the context of the page shown. */
export function Navigation({ permissions, remembered }: NavigationProps) {
  const t = useTranslations();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const here = context === undefined ? undefined : contextAddress(pathname, context);
  // The last project context: the one shown, or the last one left. Adjusted while
  // rendering, so that leaving a project leads back to it at once.
  const [last, remember] = useState(remembered);
  if (here !== undefined && here !== last) {
    remember(here);
  }
  const groups = permissions === "unreadable" ? diagnosticGroups() : readableGroups(permissions);
  useEffect(() => {
    if (here !== undefined) {
      document.cookie = contextCookie(here);
    }
  }, [here]);

  return (
    <nav aria-label={t("navigation.label")} className="space-y-4 p-4 text-sm">
      {context === undefined && last !== undefined ? (
        <Link href={last} className={`${LINK} flex items-center gap-2 font-medium`}>
          <ArrowLeft aria-hidden="true" className="size-4" />
          {t("navigation.returnToProject")}
        </Link>
      ) : null}
      {groups.map((group) => (
        <section key={group.code} className="space-y-1">
          <h2 className="px-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {group.route === undefined ? (
              t(group.label)
            ) : (
              <Link
                href={group.route}
                aria-current={group.route === pathname ? "page" : undefined}
                className={CURRENT}
              >
                {t(group.label)}
              </Link>
            )}
          </h2>
          <GroupLinks group={group} context={context} pathname={pathname} />
        </section>
      ))}
    </nav>
  );
}
