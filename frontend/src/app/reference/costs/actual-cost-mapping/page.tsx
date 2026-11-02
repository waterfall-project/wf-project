// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The correspondence of the extraction of the actual costs (FBS-3.1.3, US-0620), outside any
 * project, a leaf of the cost settings: for each of the five columns the import reads, the labels
 * under which the ERP names it, and the columns it keeps, declared one by one (WF-REF-0190). A bar
 * says the columns required that have no label, as the server computes them. A session that may
 * modify the cost settings edits the lists and saves them whole; another reads them, with no
 * command. The screen then says that the fake back keeps none of what is written (`MockupNotice`).
 * A read the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { platformOffer } from "@/components/commands/offer";
import { ActualCostMapping } from "@/components/reference/actual-cost-mapping";
import { FUNCTION_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.actualCostMapping");
}

/** The title of the screen. */
function MappingHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("actualCostMapping")}
      icon={LEAF_ICONS["FBS-3.1.3"]}
      density={FUNCTION_DENSITY.cost_settings}
    />
  );
}

/** Render the correspondence of the extraction of the actual costs. */
export default async function ActualCostMappingPage() {
  const [mapping, session] = await Promise.all([
    readOrFail("getActualCostMapping", () => serverClient().GET("/reference/actual-cost-mapping")),
    requestSession(),
  ]);
  const writes = platformOffer(session?.permissions, "cost_settings") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.cost_settings}>
      <MappingHeader />
      {writes ? <MockupNotice /> : null}
      <ActualCostMapping mapping={mapping} writes={writes} />
    </Screen>
  );
}
