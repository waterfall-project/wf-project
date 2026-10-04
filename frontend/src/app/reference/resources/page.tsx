// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), outside any project: the organisation
 * (FBS-3.2.1), the resource roles (FBS-3.2.2), the calendars (FBS-3.2.3) and the constants the
 * units of duration convert by, under the same permission as the calendars (WF-PLA-0160). Each
 * object names those it is attached to as the server resolves them. Every figure as the API gives it. A read the API refuses, or cannot answer, is thrown for
 * the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  CalendarList,
  DurationUnitFacts,
  OrgNodeList,
  ResourceRoleList,
} from "@/components/reference/resource-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.resourceSettings");
}

/** The title of the screen. */
function ResourcesHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("resourceSettings")}
      icon={FUNCTION_ICONS.resource_settings}
      density={FUNCTION_DENSITY.resource_settings}
    />
  );
}

/** Render the settings of the resources. */
export default async function ResourceSettingsPage() {
  const client = serverClient();
  const [nodes, roles, calendars, units] = await Promise.all([
    readOrFail("listOrgNodes", () => client.GET("/reference/org-nodes")),
    readOrFail("listResourceRoles", () => client.GET("/reference/resource-roles")),
    readOrFail("listCalendars", () => client.GET("/reference/calendars")),
    readOrFail("getDurationUnits", () => client.GET("/reference/duration-units")),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.resource_settings}>
      <ResourcesHeader />
      <OrgNodeList nodes={nodes} />
      <ResourceRoleList roles={roles} />
      <CalendarList calendars={calendars} />
      <DurationUnitFacts units={units} />
    </Screen>
  );
}
