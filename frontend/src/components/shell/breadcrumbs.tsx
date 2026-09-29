// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The breadcrumb of the shell, in its bar: where the page shown sits (`crumbsOf`), each step
 * before it a link, the project named as its screen handed it on — or, while its screen loads,
 * said open without a name. A client component: the shell persists from one page to the next,
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
import { type Crumb, crumbsOf } from "@/navigation/breadcrumbs";
import { readContext } from "@/navigation/context";

import { useShownProject } from "./shown-project";

/** Render where the page shown sits. */
export function Breadcrumbs() {
  const t = useTranslations();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const project = useShownProject(context?.projectId);
  const crumbs = crumbsOf(pathname, context);
  const text = (crumb: Crumb) =>
    crumb.kind === "label" ? t(crumb.label) : (project?.label ?? t("projectSwitcher.unnamed"));
  return (
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
  );
}
