// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The imports and exports of a project (FBS-4.3.4, US-0260), a leaf of the planning with a screen
 * of its own, which the head of the planning leads to, under the banner of its reading context
 * (WF-IHM-0020): the import in two steps (WF-ARC-0100) — a file deposited and analysed, the report
 * of the analysis the address names (`import`), applied once confirmed or abandoned —, the imports
 * of the project, a page of them (`offset`), and the request of an export of the revision read. An
 * import applies to the current revision whatever revision the screen reads in (WF-INTF-0090):
 * every import is offered as the server offers its command (`importOffers`), every report rendered
 * from what `getImport` gives; a read the API refuses, or cannot answer, is thrown for the pages
 * of the shell to say.
 */
import { FileDown, FileUp } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { readPage } from "@/components/costs/address";
import { ListPages } from "@/components/costs/cost-pages";
import { ExportForm } from "@/components/exchanges/export-form";
import { ImportCommands } from "@/components/exchanges/import-commands";
import { ImportList } from "@/components/exchanges/import-list";
import { ImportReport } from "@/components/exchanges/import-report";
import {
  EXCHANGE_KINDS,
  EXCHANGES_PAGE,
  IMPORT_PARAMETER,
  importOffers,
  type ImportOffers,
} from "@/components/exchanges/offers";
import { PendingAddress } from "@/components/grid/pending-address";
import { ICON } from "@/components/projects/project-tables";
import { LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { contextQuery, isIdentifier, type PageSearchParams } from "@/navigation/context";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/**
 * The imports a page of the list holds. The contract does not say in which order it gives them
 * (#320): the list is shown in the order received, a page after the other.
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

/**
 * The current revision of the project, which an import of a planning, an estimate or a remaining
 * writes into — the revision the screen reads in when it is the one —; none when the project has
 * none.
 */
async function readCurrentRevision(read: ProjectReading): Promise<Revision | undefined> {
  const { project_id, current_revision_id } = read.project;
  if (current_revision_id == null) {
    return undefined;
  }
  if (read.revision?.revision_id === current_revision_id) {
    return read.revision;
  }
  return readOrFail("getRevision", () =>
    serverClient().GET("/projects/{project_id}/revisions/{revision_id}", {
      params: { path: { project_id, revision_id: current_revision_id } },
    }),
  );
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

/** The import the address names, when it names one an identifier can stand for. */
async function readShownImport({ revision, address }: GridAddress) {
  const importId = address.get(IMPORT_PARAMETER) ?? "";
  if (!isIdentifier(importId)) {
    return undefined;
  }
  return readOrFail("getImport", () =>
    serverClient().GET("/projects/{project_id}/imports/{import_id}", {
      params: { path: { project_id: revision.projectId, import_id: importId } },
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

/** A part of the screen under its title, named by it. */
function Part({
  title,
  icon,
  children,
}: {
  readonly title: string;
  readonly icon: ReactNode;
  readonly children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

/** The imports offered, or that none is. */
function ImportPart({
  projectId,
  offers,
  start,
}: {
  readonly projectId: string;
  readonly offers: ImportOffers;
  readonly start: string;
}) {
  const t = useTranslations("exchanges.import");
  const offered = EXCHANGE_KINDS.some((kind) => offers[kind] !== undefined);
  return (
    <Part title={t("title")} icon={<FileUp aria-hidden="true" className={ICON} />}>
      {offered ? (
        <ImportCommands projectId={projectId} offers={offers} start={start} />
      ) : (
        <p className="text-sm text-muted-foreground">{t("none")}</p>
      )}
    </Part>
  );
}

/** The request of an export of the revision read. */
function ExportPart({ revision }: { readonly revision: RevisionParams }) {
  const t = useTranslations("exchanges.export");
  return (
    <Part title={t("title")} icon={<FileDown aria-hidden="true" className={ICON} />}>
      <ExportForm projectId={revision.projectId} revisionId={revision.revisionId} />
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
  const [reading, imports, shown] = await Promise.all([
    readProjectContext(at.pathname, at.context),
    readImports(at, offset),
    readShownImport(at),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  const offers = importOffers(reading.project, await readCurrentRevision(reading));
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
        <ExportPart revision={revision} />
      </Screen>
    </>
  );
}
