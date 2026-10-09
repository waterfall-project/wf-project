// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the risks (FBS-3.3, US-0250), outside any project: the bounds of the risk
 * matrix, common to every project (WF-REF-0160), and the zone of each of its cells, as the server
 * gives them. A read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { RiskBoundsTable, RiskZonesTable } from "@/components/reference/setting-tables";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

import { screenMetadata } from "../../title";
import { readReferenceSettings } from "../settings";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.riskSettings");
}

/** The title of the screen. */
function RisksHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("riskSettings")}
      icon={FUNCTION_ICONS.risk_settings}
      density={FUNCTION_DENSITY.risk_settings}
    />
  );
}

/** Render the settings of the risks. */
export default async function RiskSettingsPage() {
  const settings = await readReferenceSettings();
  return (
    <Screen density={FUNCTION_DENSITY.risk_settings}>
      <RisksHeader />
      <RiskBoundsTable matrix={settings.risk_matrix} />
      <RiskZonesTable matrix={settings.risk_matrix} />
    </Screen>
  );
}
