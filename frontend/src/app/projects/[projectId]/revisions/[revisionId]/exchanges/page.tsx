// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exchanges of a project by file (US-0260), under the banner of its reading context
 * (WF-IHM-0020): the import in two steps (WF-ARC-0100) — a file deposited and analysed, the
 * report of the analysis the address names (`import`), applied once confirmed or abandoned —, the
 * imports of the project, and the request of an export. An import applies to the current revision
 * (WF-INTF-0090): the screen is one of the project itself. Every import is offered as the server
 * offers its command (`importOffers`), every report rendered from what `getImport` gives; a read
 * the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import { ArrowLeftRight, FileDown, FileUp } from "lucide-react";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import type { ProjectReading } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { ExportForm } from "@/components/exchanges/export-form";
import { ImportCommands } from "@/components/exchanges/import-commands";
import { ImportList } from "@/components/exchanges/import-list";
import { ImportReport } from "@/components/exchanges/import-report";
import {
  EXCHANGE_KINDS,
  IMPORT_PARAMETER,
  importOffers,
  type ImportOffers,
} from "@/components/exchanges/offers";
import { ICON } from "@/components/projects/project-tables";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { contextQuery, pageSearch } from "@/navigation/context";
import { EXCHANGES_SCREEN } from "@/navigation/exchanges";

import { screenMetadata } from "../../../title";
import { type ProjectPageProps, projectAddress, readProjectScreen } from "../screen";

/** The imports the list holds: the most recent ones, as many as a screen shows. */
const IMPORTS_LIMIT = 20;

/** Title the tab with the exchanges, and the project. */
export async function generateMetadata({ params }: ProjectPageProps): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("exchanges.title", projectId);
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

/** The request of an export. */
function ExportPart({
  projectId,
  revisionId,
}: {
  readonly projectId: string;
  readonly revisionId: string | undefined;
}) {
  const t = useTranslations("exchanges.export");
  return (
    <Part title={t("title")} icon={<FileDown aria-hidden="true" className={ICON} />}>
      <ExportForm projectId={projectId} revisionId={revisionId} />
    </Part>
  );
}

/** The title of the screen. */
function ExchangesHeader() {
  const t = useTranslations("exchanges");
  return <PageHeader title={t("title")} icon={ArrowLeftRight} subtitle={t("subtitle")} />;
}

/** Render the exchanges of a project: the report shown, the imports, the export. */
export default async function ExchangesPage(props: ProjectPageProps) {
  const address = await projectAddress(props, EXCHANGES_SCREEN);
  const importId = pageSearch(await props.searchParams).get(IMPORT_PARAMETER) ?? "";
  const { projectId } = address;
  const [read, imports, shown] = await Promise.all([
    readProjectScreen(address),
    readOrFail("listImports", () =>
      serverClient().GET("/projects/{project_id}/imports", {
        params: { path: { project_id: projectId }, query: { limit: IMPORTS_LIMIT } },
      }),
    ),
    importId === ""
      ? undefined
      : readOrFail("getImport", () =>
          serverClient().GET("/projects/{project_id}/imports/{import_id}", {
            params: { path: { project_id: projectId, import_id: importId } },
          }),
        ),
  ]);
  const offers = importOffers(read.project, await readCurrentRevision(read));
  const start = `${address.pathname}${contextQuery(address.context, true)}`;
  return (
    <>
      <ContextBanner reading={read} />
      <Screen>
        <ExchangesHeader />
        {shown === undefined ? null : (
          <ImportReport
            projectId={projectId}
            entry={shown}
            offer={offers[shown.kind]}
            start={start}
          />
        )}
        <ImportPart projectId={projectId} offers={offers} start={start} />
        <ImportList
          imports={imports.items}
          total={imports.meta.total}
          current={shown?.import_id}
          start={start}
        />
        <ExportPart projectId={projectId} revisionId={address.context.revisionId} />
      </Screen>
    </>
  );
}
