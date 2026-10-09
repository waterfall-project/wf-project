// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The breadcrumb of the shell, in its bar, after a separator: where the page shown sits
 * (`crumbsOf`), each step before it a link — a function the session may read —, the project named as its screen handed it on — or,
 * while its screen loads, said open without a name. A client component: the shell persists from one page to the next,
 * and only the browser knows the address it now shows.
 */
"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Fragment } from "react";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import type { components } from "@/api/generated/schema";
import { type Crumb, crumbsOf } from "@/navigation/breadcrumbs";
import { readContext } from "@/navigation/context";

import { useShownProject } from "./shown-project";

/** Render where the page shown sits, for a session of the permissions given. */
export function Breadcrumbs({
  permissions,
}: {
  readonly permissions: readonly components["schemas"]["PermissionCode"][];
}) {
  const t = useTranslations();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const project = useShownProject(context?.projectId);
  const crumbs = crumbsOf(pathname, context, permissions);
  const text = (crumb: Crumb) =>
    crumb.kind === "label" ? t(crumb.label) : (project?.label ?? t("projectSwitcher.unnamed"));
  // An address that leads nowhere sits nowhere: no navigation without a step, nor its
  // separator; the space it would take stays, and keeps the rest of the bar at the right.
  if (crumbs.length === 0) {
    return <div className="flex-1" />;
  }
  return (
    <>
      <Separator orientation="vertical" className="h-4!" />
      <Breadcrumb aria-label={t("breadcrumbs.label")} className="min-w-0 flex-1">
        <BreadcrumbList className="flex-nowrap">
          {crumbs.map((crumb, index) => {
            const last = index === crumbs.length - 1;
            return (
              <Fragment key={crumb.kind === "label" ? crumb.label : crumb.projectId}>
                {index === 0 ? null : <BreadcrumbSeparator />}
                <BreadcrumbItem>
                  {crumb.href === undefined || last ? (
                    <BreadcrumbPage
                      aria-current={last ? "page" : undefined}
                      className={last ? "font-medium" : "text-muted-foreground"}
                    >
                      {text(crumb)}
                    </BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={crumb.href}>{text(crumb)}</BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </Fragment>
            );
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </>
  );
}
