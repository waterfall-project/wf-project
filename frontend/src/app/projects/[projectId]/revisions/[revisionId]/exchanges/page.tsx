// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The imports and exports of a project (FBS-4.3.4, US-0260), a leaf of the planning with a screen
 * of its own, which the head of the planning leads to, under the banner of its reading context
 * (WF-IHM-0020): the import in two steps (WF-ARC-0100) — a file deposited and analysed, the report
 * of the analysis the address names (`import`), applied once confirmed or abandoned —, the imports
 * of the project, a page of them (`offset`), and the request of an export of the revision read. An
 * import applies to the current revision whatever revision the screen reads in, and creates it if
 * the project has none (WF-INTF-0090): every import is offered as the project offers its command
 * (`importOffers`), every export as the revision read offers its own (`exportOffers`), every report
 * rendered from what `getImport` gives; a read the API refuses, or cannot answer, is thrown for the
 * pages of the shell to say.
 *
 * The screen is guarded by the commands it exercises, not by the read of the planning alone (#521):
 * it shows to a session that reads the planning, whose leaf it is, or to which the project lists an
 * import — a costing engineer, whom the estimate and the remaining to commit lead here when their
 * import is listed. To anyone else it is not found, as a read refused is (WF-ADM-0110).
 */
import { FileDown } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { readPage } from "@/components/costs/address";
import { ListPages } from "@/components/costs/cost-pages";
import { ExportForm } from "@/components/exchanges/export-form";
import { ImportList } from "@/components/exchanges/import-list";
import { ImportPart, Part } from "@/components/exchanges/import-part";
import { ImportReport } from "@/components/exchanges/import-report";
import {
  EXCHANGES_PAGE,
  exportOffers,
  type ExportOffers,
  importOffers,
  listsAnImport,
} from "@/components/exchanges/offers";
import { readShownImport } from "@/components/exchanges/shown-import";
import { PendingAddress } from "@/components/grid/pending-address";
import { ICON } from "@/components/projects/project-tables";
import { LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { contextQuery, type PageSearchParams } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/**
 * The imports a page of the list holds, the most recent first as the server orders them, a page
 * after the other.
 */
const IMPORTS_LIMIT = 20;

/** Title the tab with the imports and exports, and the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.exchanges", projectId);
}

/** A page of the imports of the project, from the place the address asks. */
async function readImports({ revision }: GridAddress, offset: number) {
  return readOrFail("listImports", () =>
    serverClient().GET("/projects/{project_id}/imports", {
      params: {
        path: { project_id: revision.projectId },
        query: { limit: IMPORTS_LIMIT, ...(offset === 0 ? {} : { offset }) },
      },
    }),
  );
}

/** The address of the screen without a report: its context and its page of the list kept. */
function startOf({ pathname, context }: GridAddress, offset: number): string {
  const query = new URLSearchParams(contextQuery(context, false));
  if (offset > 0) {
    query.set(EXCHANGES_PAGE, String(offset));
  }
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** The request of an export of the revision read, or that none is offered. */
function ExportPart({
  revision,
  offers,
}: {
  readonly revision: RevisionParams;
  readonly offers: ExportOffers;
}) {
  const t = useTranslations("exchanges.export");
  return (
    <Part title={t("title")} icon={<FileDown aria-hidden="true" className={ICON} />}>
      <ExportForm projectId={revision.projectId} revisionId={revision.revisionId} offers={offers} />
    </Part>
  );
}

/** The title of the screen. */
function ExchangesHeader() {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.exchanges")}
      icon={LEAF_ICONS["FBS-4.3.4"]}
      subtitle={t("exchanges.subtitle")}
    />
  );
}

/** Render the imports and exports of a project: the report shown, the imports, the export. */
export default async function ExchangesPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "exchanges");
  const offset = readPage(at.address, EXCHANGES_PAGE);
  const [reading, imports, shown, session] = await Promise.all([
    // The imports take neither a sub-project nor a date: the banner shows no filter (#302).
    readProjectContext(at.pathname, at.context, []),
    readImports(at, offset),
    readShownImport(revision.projectId, at.address),
    requestSession(),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  const readsPlanning = session?.permissions.includes("planning.read") === true;
  if (!readsPlanning && !listsAnImport(reading.project)) {
    notFound();
  }
  const offers = importOffers(reading.project);
  const start = startOf(at, offset);
  const { projectId } = revision;
  return (
    <>
      <ContextBanner reading={reading} />
      <Screen>
        <ExchangesHeader />
        {shown === undefined ? null : (
          <ImportReport
            key={shown.import_id}
            projectId={projectId}
            entry={shown}
            offer={offers[shown.kind]}
            start={start}
          />
        )}
        <ImportPart projectId={projectId} offers={offers} start={start} />
        {/* The pages of the list keep the import shown, and turn from the address last asked. */}
        <PendingAddress>
          <ImportList
            imports={imports.items}
            total={imports.meta.total}
            current={shown?.import_id}
            start={start}
          >
            <ListPages list="exchanges" page={imports.meta} shown={imports.items.length} />
          </ImportList>
        </PendingAddress>
        <ExportPart revision={revision} offers={exportOffers(reading.revision)} />
      </Screen>
    </>
  );
}
