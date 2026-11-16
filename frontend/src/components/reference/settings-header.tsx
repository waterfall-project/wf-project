// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The header of the screens of the settings of the risks and of the indicators: the title of the
 * function, its icon and its density, with the command that modifies them at its right when the
 * session may. One place for the pages, which read, and for the forms, which write.
 */
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader } from "@/components/shell/page-header";

/** The functions whose settings are a screen of their own. */
export type SettingsScreen = "risk_settings" | "indicator_settings";

const TITLES = { risk_settings: "riskSettings", indicator_settings: "indicatorSettings" } as const;

/** The title of a settings screen, and its command (`actions`) when the session modifies. */
export function SettingsHeader({
  screen,
  actions,
}: {
  readonly screen: SettingsScreen;
  readonly actions?: ReactNode;
}) {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t(TITLES[screen])}
      icon={FUNCTION_ICONS[screen]}
      density={FUNCTION_DENSITY[screen]}
      actions={actions}
    />
  );
}
