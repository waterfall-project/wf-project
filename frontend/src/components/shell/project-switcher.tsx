// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of a project, at the top of the side bar: the project the address reads in — its
 * label, its code and its state, as its screen handed them on —, else that no project is open.
 * It opens on the list of all projects and, in a project, on its page, which keeps the context
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
import { contextQuery, readContext } from "@/navigation/context";

import { type ShownProject, useShownProject } from "./shown-project";

/** What the trigger says of the project open: its label, and its code and its state. */
function useProjectTexts(
  open: boolean,
  project: ShownProject | undefined,
): { readonly title: string; readonly summary: string | undefined } {
  const t = useTranslations();
  if (project === undefined) {
    return {
      title: t(open ? "projectSwitcher.unnamed" : "projectSwitcher.none"),
      summary: undefined,
    };
  }
  const state = t(`enums.ProjectState.${project.state}`);
  return {
    title: project.label,
    summary:
      project.code == null ? state : t("projectSwitcher.summary", { code: project.code, state }),
  };
}

/** Render the project open, and the way to the projects. */
export function ProjectSwitcher() {
  const t = useTranslations("projectSwitcher");
  const { isMobile } = useSidebar();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const project = useShownProject(context?.projectId);
  const { title, summary } = useProjectTexts(context !== undefined, project);
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" tooltip={title}>
              <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Waves aria-hidden="true" className="size-4" />
              </span>
              <span className="grid min-w-0 flex-1 text-left leading-tight">
                <span className="truncate font-semibold">{title}</span>
                {summary === undefined ? null : (
                  <span className="truncate text-xs text-muted-foreground">{summary}</span>
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
              <Link href="/projects">
                <FolderKanban aria-hidden="true" />
                {t("allProjects")}
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
