// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The installation (FBS-1.6, WF-ADM-0100-A, EP-25 US-2120), outside any project: a card
 * « Installation » with the name of the company, which the exported files bear (WF-EXP-0020) and
 * which a session that holds `installation.write` modifies, and, read only, the currency, the
 * default language and the time zone the bootstrap fixed (WF-REF-0140; `getReferenceSettings`,
 * `getInstallation`). A session without `installation.read` finds the screen not found, as an
 * address that leads nowhere; one that holds it without `installation.write` reads the card without
 * a command. Every value as the API gives it; a read the API refuses, or cannot answer, is thrown
 * for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { InstallationCard, InstallationSettings } from "@/components/reference/settings-forms";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import { readReferenceSettings } from "../../reference/settings";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.installation");
}

/** The title of the screen. */
function InstallationHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("installation")}
      icon={FUNCTION_ICONS.installation}
      density={FUNCTION_DENSITY.installation}
    />
  );
}

/** Render the installation. */
export default async function InstallationPage() {
  const session = await requestSession();
  const permissions = session?.permissions ?? [];
  if (!permissions.includes("installation.read")) {
    notFound();
  }
  const [settings, installation] = await Promise.all([
    readReferenceSettings(),
    readOrFail("getInstallation", () => serverClient().GET("/installation")),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.installation}>
      <InstallationHeader />
      {permissions.includes("installation.write") ? (
        <InstallationSettings settings={settings} installation={installation} />
      ) : (
        <InstallationCard settings={settings} installation={installation} />
      )}
    </Screen>
  );
}
