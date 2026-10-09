// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How each function of the navigation shows (charter, guide « Charte graphique »): its icon, a
 * form of Lucide, which the side bar shows before the name of the function, and alone once
 * folded into a rail, where the tooltip and the name the entry keeps say what it is, and which
 * the header of its screen repeats; and the density of its screen — dense for the grids and the
 * lists, the most under the eyes, airy for the indicators. Tables typed on the permissions of
 * the functions: a function added to `functions.json` has neither until it is given them here,
 * and the typing says so. The blocks of the FBS have their icons too, which the side bar shows
 * before their names, and so have the pages of the account, in the menu of the account and in
 * the headers of their screens. A leaf with a screen of its own has its icon by its code, which
 * the link of its function's screen and the header of its own screen show.
 */
import {
  Activity,
  ArrowLeftRight,
  BookOpen,
  Briefcase,
  BriefcaseBusiness,
  Calculator,
  CalendarClock,
  CalendarRange,
  ChartColumnStacked,
  ChartGantt,
  ChartPie,
  ChartSpline,
  Coins,
  DatabaseBackup,
  FolderKanban,
  Gauge,
  GitBranch,
  HeartPulse,
  Hourglass,
  ImageIcon,
  Kanban,
  Network,
  type LucideIcon,
  Receipt,
  RefreshCcw,
  ScrollText,
  Settings,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  TrendingUp,
  TriangleAlert,
  User,
  UserCog,
  Users,
  Wrench,
} from "lucide-react";

import type { AccountPage } from "@/navigation/account";
import type { FunctionGroup, FunctionPermission } from "@/navigation/functions";

import type { Density } from "./page-header";

/** The icon of each function, by the name of its permissions. */
export const FUNCTION_ICONS: Readonly<Record<FunctionPermission, LucideIcon>> = {
  users: Users,
  access_roles: ShieldCheck,
  system_status: Activity,
  backups: DatabaseBackup,
  audit_log: ScrollText,
  portfolio_projects: BriefcaseBusiness,
  portfolio_workload: ChartGantt,
  portfolio_performance: TrendingUp,
  portfolio_cost_structure: ChartPie,
  portfolio_risks: TriangleAlert,
  portfolio_cost_curve: ChartSpline,
  portfolio_pilot_health: HeartPulse,
  cost_settings: Coins,
  resource_settings: UserCog,
  risk_settings: SlidersHorizontal,
  indicator_settings: Settings2,
  revisions: GitBranch,
  project_settings: Settings,
  planning: CalendarRange,
  estimate: Calculator,
  remaining: Hourglass,
  risks: ShieldAlert,
  actual_costs: Receipt,
  project_indicators: Gauge,
  lifecycle: RefreshCcw,
};

/**
 * The icon of each leaf with a screen of its own, by its code: the timelines, the imports and
 * exports and the task tree of the planning, the workload of the project, the Kanban of the start
 * of the tasks.
 */
export const LEAF_ICONS = {
  "FBS-4.3.1": CalendarClock,
  "FBS-4.3.4": ArrowLeftRight,
  "FBS-4.3.5": Network,
  "FBS-4.4.4": ChartColumnStacked,
  "FBS-4.5.3": Kanban,
} as const satisfies Readonly<Record<string, LucideIcon>>;

/** The icon of each block of the FBS, by the key of its name. */
export const GROUP_ICONS: Readonly<Record<FunctionGroup["label"], LucideIcon>> = {
  "functionGroups.administration": Wrench,
  "functionGroups.portfolio": Briefcase,
  "functionGroups.applicationSettings": BookOpen,
  "functionGroups.projects": FolderKanban,
};

/** The density of the screen of each function, by the name of its permissions. */
export const FUNCTION_DENSITY: Readonly<Record<FunctionPermission, Density>> = {
  users: "dense",
  access_roles: "dense",
  system_status: "airy",
  backups: "dense",
  audit_log: "dense",
  portfolio_projects: "dense",
  portfolio_workload: "dense",
  portfolio_performance: "airy",
  portfolio_cost_structure: "airy",
  portfolio_risks: "dense",
  portfolio_cost_curve: "airy",
  portfolio_pilot_health: "airy",
  cost_settings: "dense",
  resource_settings: "dense",
  risk_settings: "dense",
  indicator_settings: "dense",
  revisions: "dense",
  project_settings: "dense",
  planning: "dense",
  estimate: "dense",
  remaining: "dense",
  risks: "dense",
  actual_costs: "dense",
  project_indicators: "airy",
  lifecycle: "dense",
};

/** The icon of each page of the account. */
export const ACCOUNT_ICONS: Readonly<Record<AccountPage, LucideIcon>> = {
  account: User,
  avatar: ImageIcon,
};
