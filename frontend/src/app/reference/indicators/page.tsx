// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the indicators (FBS-3.4, US-0250), outside any project: the watch and alert
 * thresholds of the cost and schedule indices (WF-REF-0170), and the longest delay expected
 * between two marked revisions (WF-REF-0180), as the server gives them. A read the API refuses,
 * or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { IndexThresholdTable, ReviewDelay } from "@/components/reference/setting-tables";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

import { screenMetadata } from "../../title";
import { readReferenceSettings } from "../settings";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.indicatorSettings");
}

/** The title of the screen. */
function IndicatorsHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("indicatorSettings")}
      icon={FUNCTION_ICONS.indicator_settings}
      density={FUNCTION_DENSITY.indicator_settings}
    />
  );
}

/** Render the settings of the indicators. */
export default async function IndicatorSettingsPage() {
  const settings = await readReferenceSettings();
  return (
    <Screen density={FUNCTION_DENSITY.indicator_settings}>
      <IndicatorsHeader />
      <IndexThresholdTable thresholds={settings.index_thresholds} />
      <ReviewDelay weeks={settings.max_weeks_between_reviews} />
    </Screen>
  );
}
