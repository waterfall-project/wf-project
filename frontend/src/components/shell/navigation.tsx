// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The navigation of the shell (WF-IHM-0010), in its side bar: the functions of the FBS the
 * session may read, drawn from `functions.json`, in three groups — the platform, outside any
 * project, by block of the FBS, each opening on its functions; the project, with the list of
 * projects; the revision read. The
 * functions outside any project are reached without opening one; in a project, the links carry
 * its context — the revision read, the filtered sub-project, the calculation date —, and a
 * project without a revision offers the functions of the project itself; outside, a link leads
 * back to the last project context, which a cookie of the front keeps across visits. When the
 * session cannot be read, the status screen is still offered, alone: it is what is consulted
 * when nothing else works (WF-ADM-0130).
 *
 * Each entry has its icon; folded into a rail, the bar shows the icons alone, each entry keeping
 * its name, which a tooltip shows. At the top, the logo and the choice of a project; at the foot,
 * the button that folds the bar. A client component: the shell persists from one page to the
 * next, and only the browser knows the address it now shows.
 */
"use client";

import { ChevronRight, type LucideIcon, PanelLeft, Undo2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useState } from "react";

import type { components } from "@/api/generated/schema";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
  useSidebarToggleLabel,
} from "@/components/ui/sidebar";
import {
  contextAddress,
  contextCookie,
  type ProjectContext,
  readContext,
} from "@/navigation/context";
import {
  diagnosticGroups,
  findScreen,
  type FunctionGroup,
  functionHref,
  type NavigationFunction,
  readableGroups,
  type Scope,
} from "@/navigation/functions";
import { HOME } from "@/navigation/home";
import type { ThemePreference } from "@/theme/theme";

import { FUNCTION_ICONS, GROUP_ICONS } from "./function-display";
import { Logo } from "./logo";
import { ProjectSwitcher } from "./project-switcher";

/** What the navigation offers, and where it leads back to. */
export interface NavigationProps {
  /**
   * The effective permissions of the session, or `unreadable` when the session could not be
   * read: the status screen alone is offered then (`diagnosticGroups`).
   */
  readonly permissions: readonly components["schemas"]["PermissionCode"][] | "unreadable";
  /** The address of the last project context, from the cookie of the request. */
  readonly remembered: string | undefined;
  /** The display mode of the account, for the variant of the logo. */
  readonly theme: ThemePreference | undefined;
}

/** An entry of the bar: where it leads, what it is called, its icon. */
interface Entry {
  readonly key: string;
  readonly href: string;
  readonly label: string;
  readonly icon: LucideIcon;
  /**
   * Whether it leads to the page shown, whatever the query (`page`); to the function whose leaf
   * the page shown is, which the bar does not offer (`true`); or to neither.
   */
  readonly current: false | "page" | "true";
}

/** The entries of a list, in the order given. */
function Entries({ entries }: { readonly entries: readonly Entry[] }) {
  return (
    <SidebarMenu>
      {entries.map(({ key, href, label, icon: Icon, current }) => (
        <SidebarMenuItem key={key}>
          <SidebarMenuButton asChild tooltip={label}>
            <Link href={href} aria-current={current || undefined}>
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      ))}
    </SidebarMenu>
  );
}

/** A group of the bar, under its heading; nothing when it has no entry. */
function Section({
  label,
  children,
  empty,
}: {
  readonly label: string;
  readonly children: ReactNode;
  readonly empty: boolean;
}) {
  return empty ? null : (
    <SidebarGroup className="group-data-[collapsible=icon]:not-first:border-t group-data-[collapsible=icon]:not-first:border-sidebar-border">
      <SidebarGroupLabel asChild>
        <h2>{label}</h2>
      </SidebarGroupLabel>
      {children}
    </SidebarGroup>
  );
}

/** The name of a function, in the language of the page. */
type Naming = (fn: NavigationFunction) => string;

/** The functions of a scope among those given, as entries in the context of the page shown. */
function functionEntries(
  functions: readonly NavigationFunction[],
  scope: Scope,
  context: ProjectContext | undefined,
  pathname: string,
  name: Naming,
): Entry[] {
  // The function whose leaf the page shown is, if it is one: its entry stands for the leaf.
  const parent = findScreen(pathname.split("/").slice(1))?.parent;
  const current = (href: string, fn: NavigationFunction): Entry["current"] => {
    if (href.split("?")[0] === pathname) {
      return "page";
    }
    return fn.code === parent?.code ? "true" : false;
  };
  return functions
    .filter((fn) => fn.scope === scope)
    .flatMap((fn) => {
      const href = functionHref(fn, context);
      return href === undefined
        ? []
        : [
            {
              key: fn.code,
              href,
              label: name(fn),
              icon: FUNCTION_ICONS[fn.permission],
              current: current(href, fn),
            },
          ];
    });
}

/**
 * A block of the FBS outside any project, which opens on its functions: open at first when it
 * holds the page shown — or always, when the session cannot be read and the status screen is
 * all there is —, and as the user leaves it after. Once the bar is a rail, its functions are
 * hidden and the block says it is closed; the block of the page shown is marked current, and
 * pressing a block unfolds the bar on its functions.
 */
function PlatformBlock({
  group,
  entries,
  diagnostic,
}: {
  readonly group: FunctionGroup;
  readonly entries: readonly Entry[];
  readonly diagnostic: boolean;
}) {
  const t = useTranslations();
  const { state, isMobile, setOpen: unfold } = useSidebar();
  const current = entries.some((entry) => entry.current);
  const holdsPage = diagnostic || current;
  const [toggled, toggle] = useState<boolean>();
  // A page of the block shown anew opens it again, whatever the user did before.
  const [held, hold] = useState(holdsPage);
  if (held !== holdsPage) {
    hold(holdsPage);
    toggle(undefined);
  }
  const rail = state === "collapsed" && !isMobile;
  const label = t(group.label);
  const Icon = GROUP_ICONS[group.label];
  return (
    <Collapsible
      asChild
      open={rail ? false : (toggled ?? holdsPage)}
      onOpenChange={(open) => {
        if (rail) {
          unfold(true);
        }
        toggle(open);
      }}
      className="group/collapsible"
    >
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton
            type="button"
            tooltip={label}
            aria-current={rail && current ? "true" : undefined}
          >
            <Icon aria-hidden="true" />
            <span>{label}</span>
            <ChevronRight
              aria-hidden="true"
              className="ml-auto text-muted-foreground group-data-[state=open]/collapsible:rotate-90"
            />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarMenuSub>
            {entries.map(({ key, href, label: name, icon: EntryIcon, current }) => (
              <SidebarMenuSubItem key={key}>
                <SidebarMenuSubButton>
                  <Link href={href} aria-current={current || undefined}>
                    <EntryIcon aria-hidden="true" />
                    <span>{name}</span>
                  </Link>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  );
}

/** The functions outside any project, by block of the FBS. */
function PlatformSection({
  groups,
  pathname,
  diagnostic,
}: {
  readonly groups: readonly FunctionGroup[];
  readonly pathname: string;
  readonly diagnostic: boolean;
}) {
  const t = useTranslations();
  const blocks = groups
    .map((group) => ({
      group,
      entries: functionEntries(group.functions, "platform", undefined, pathname, (fn) =>
        t(fn.label),
      ),
    }))
    .filter((block) => block.entries.length > 0);
  return (
    <Section label={t("navigation.scopes.platform")} empty={blocks.length === 0}>
      <SidebarMenu>
        {blocks.map(({ group, entries }) => (
          <PlatformBlock key={group.code} group={group} entries={entries} diagnostic={diagnostic} />
        ))}
      </SidebarMenu>
    </Section>
  );
}

/** The last project context: the one shown, or the last one left, kept in a cookie. */
function useLastContext(here: string | undefined, remembered: string | undefined) {
  // Adjusted while rendering, so that leaving a project leads back to it at once.
  const [last, remember] = useState(remembered);
  if (here !== undefined && here !== last) {
    remember(here);
  }
  useEffect(() => {
    if (here !== undefined) {
      document.cookie = contextCookie(here);
    }
  }, [here]);
  return last;
}

/** The groups of the bar: the platform, the project, the revision read. */
function NavigationGroups({ permissions, remembered }: Omit<NavigationProps, "theme">) {
  const t = useTranslations();
  const pathname = usePathname();
  const context = readContext(pathname, useSearchParams());
  const last = useLastContext(
    context === undefined ? undefined : contextAddress(pathname, context),
    remembered,
  );
  const groups = permissions === "unreadable" ? diagnosticGroups() : readableGroups(permissions);
  const functions = groups.flatMap((group) => group.functions);
  const name: Naming = (fn) => t(fn.label);
  const projectEntries: Entry[] = [
    ...groups.flatMap((group): Entry[] =>
      group.route === undefined
        ? []
        : [
            {
              key: group.code,
              href: group.route,
              label: t(group.label),
              icon: GROUP_ICONS[group.label],
              current: group.route === pathname ? "page" : false,
            },
          ],
    ),
    ...(context === undefined && last !== undefined
      ? ([
          {
            key: "return",
            href: last,
            label: t("navigation.returnToProject"),
            icon: Undo2,
            current: false,
          },
        ] satisfies Entry[])
      : []),
    ...functionEntries(functions, "project", context, pathname, name),
  ];
  const revisionEntries = functionEntries(functions, "revision", context, pathname, name);
  return (
    <nav aria-label={t("navigation.label")}>
      <PlatformSection
        groups={groups}
        pathname={pathname}
        diagnostic={permissions === "unreadable"}
      />
      <Section label={t("navigation.scopes.project")} empty={projectEntries.length === 0}>
        <Entries entries={projectEntries} />
      </Section>
      <Section label={t("navigation.scopes.revision")} empty={revisionEntries.length === 0}>
        <Entries entries={revisionEntries} />
      </Section>
    </nav>
  );
}

/** The button at the foot of the bar that folds it into a rail, or unfolds it. */
function FoldButton() {
  const { toggleSidebar } = useSidebar();
  const label = useSidebarToggleLabel();
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton type="button" tooltip={label} onClick={toggleSidebar}>
          <PanelLeft aria-hidden="true" />
          <span>{label}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

/** Render the side bar: the logo, the project open, the functions the session may read. */
export function Navigation({ permissions, remembered, theme }: NavigationProps) {
  return (
    <Sidebar>
      <SidebarHeader>
        <Link
          href={HOME}
          data-rail-hidden=""
          className="rounded-md px-2 py-1 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring group-data-[collapsible=icon]:hidden"
        >
          <Logo theme={theme} />
        </Link>
        {permissions === "unreadable" ? null : <ProjectSwitcher />}
      </SidebarHeader>
      <SidebarContent>
        <NavigationGroups permissions={permissions} remembered={remembered} />
      </SidebarContent>
      <SidebarFooter>
        <FoldButton />
      </SidebarFooter>
    </Sidebar>
  );
}
