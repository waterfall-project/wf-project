// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of a project, at the top of the side bar: the project the address reads in — its
 * label, its code and its state by its badge (#523), as its screen handed them on —, else that no
 * project is open. It opens on the list of all projects — the home, its contributor filter lifted
 * —, offered only to a session that may read every project: for any other, the list lifted is the
 * list filtered, and it opens on the home (#522, WF-IHM-0090); in a project, on its page, which
 * keeps the context
 * of the address. Choosing among the projects themselves waits for a read the shell does not
 * make: the list is a screen of its own.
 */
"use client";

import { ChevronsUpDown, FolderKanban, FolderOpen, Waves } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import type { components } from "@/api/generated/schema";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import { contextQuery, readContext } from "@/navigation/context";
import { ALL_PROJECTS, HOME, mayLiftContributorFilter } from "@/navigation/home";

import { type ShownProject, useShownProject } from "./shown-project";

/** What the trigger says of the project open: its label; none, and that no project is shown. */
function useProjectTitle(open: boolean, project: ShownProject | undefined): string {
  const t = useTranslations();
  if (project === undefined) {
    return t(open ? "projectSwitcher.unnamed" : "projectSwitcher.none");
  }
  return project.label;
}

/** Render the project open, and the way to the projects the session may read. */
export function ProjectSwitcher({
  permissions,
}: {
  readonly permissions: readonly components["schemas"]["PermissionCode"][];
}) {
  const t = useTranslations("projectSwitcher");
  const { isMobile } = useSidebar();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const project = useShownProject(context?.projectId);
  const title = useProjectTitle(context !== undefined, project);
  const everyProject = mayLiftContributorFilter(permissions);
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              tooltip={title}
              className="data-[state=open]:bg-sidebar-accent"
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Waves aria-hidden="true" className="size-4" />
              </span>
              <span className="grid min-w-0 flex-1 text-left leading-tight">
                <span className="truncate font-semibold">{title}</span>
                {project === undefined ? null : (
                  <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                    {project.code == null ? null : <span className="truncate">{project.code}</span>}
                    <ProjectStateBadge state={project.state} />
                  </span>
                )}
              </span>
              <ChevronsUpDown aria-hidden="true" className="ml-auto text-muted-foreground" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="start"
            side={isMobile ? "bottom" : "right"}
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56"
          >
            <DropdownMenuItem asChild>
              <Link href={everyProject ? ALL_PROJECTS : HOME}>
                <FolderKanban aria-hidden="true" />
                {t(everyProject ? "allProjects" : "myProjects")}
              </Link>
            </DropdownMenuItem>
            {context === undefined ? null : (
              <DropdownMenuItem asChild>
                <Link href={`/projects/${context.projectId}${contextQuery(context, true)}`}>
                  <FolderOpen aria-hidden="true" />
                  {t("projectPage")}
                </Link>
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
