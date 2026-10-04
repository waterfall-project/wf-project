// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of the platform (FBS-1.3, US-0250), outside any project (WF-ADM-0130): the version
 * installed; each component, available or not, and when it was last checked; the storage used and
 * available; the last reading of the accounts of the identity provider, the last backup and the
 * last restoration test, each dated with its outcome; the alerts under way. Every value as the API
 * gives it. A read the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  AlertList,
  ComponentList,
  OperationList,
  StorageFacts,
} from "@/components/admin/platform-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

import { screenMetadata } from "../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.systemStatus");
}

/** The title of the screen, and the version installed. */
function StatusHeader({ version }: { readonly version: string }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.systemStatus")}
      icon={FUNCTION_ICONS.system_status}
      density={FUNCTION_DENSITY.system_status}
      subtitle={t("admin.status.version", { version })}
    />
  );
}

/** Render the state of the platform. */
export default async function SystemStatusPage() {
  const status = await readOrFail("getSystemStatus", () => serverClient().GET("/system/status"));
  return (
    <Screen density={FUNCTION_DENSITY.system_status}>
      <StatusHeader version={status.version} />
      <AlertList alerts={status.alerts} />
      <ComponentList components={status.components} />
      <StorageFacts storage={status.storage} />
      <OperationList status={status} />
    </Screen>
  );
}
