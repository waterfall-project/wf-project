// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the indicators (FBS-3.4, US-0250), outside any project: the watch and alert
 * thresholds of the cost and schedule indices (WF-REF-0170), and the longest delay expected
 * between two marked revisions (WF-REF-0180), as the server gives them. A session that may modify the
 * indicator settings modifies the four thresholds and the delay in one form (EP-14/L43e); the screen
 * then says that the fake back keeps none of what is written (`MockupNotice`). A read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { platformOffer } from "@/components/commands/offer";
import { IndexThresholdTable, ReviewDelay } from "@/components/reference/setting-tables";
import { IndicatorSettings } from "@/components/reference/settings-forms";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { requestSession } from "@/session/request";

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
  const [settings, session] = await Promise.all([readReferenceSettings(), requestSession()]);
  const writes = platformOffer(session?.permissions, "indicator_settings") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.indicator_settings}>
      <IndicatorsHeader />
      {writes ? (
        <>
          <MockupNotice />
          <IndicatorSettings settings={settings} />
        </>
      ) : (
        <>
          <IndexThresholdTable thresholds={settings.index_thresholds} />
          <ReviewDelay weeks={settings.max_weeks_between_reviews} />
        </>
      )}
    </Screen>
  );
}
