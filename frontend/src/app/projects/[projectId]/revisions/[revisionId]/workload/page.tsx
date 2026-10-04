// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workload of a project (FBS-4.4.4, WF-DEV-0070, US-0240), at the route of its leaf of the
 * estimate (`functions.json`), which the screen of the estimate leads to: the banner of the reading
 * context (WF-IHM-0020); the workload by role and by month as the API computes it
 * (`getProjectWorkload`) on the basis, the marked revision and the node of organisation the
 * address asks — the server filters, the front computes nothing —, the capacity of each role
 * against it, and its export as a PNG image (WF-IHM-0130). The choice offers the bases the project
 * admits, the marked revisions of the project (`listRevisions`, `status=marked`) and the nodes of
 * organisation (`listOrgNodes`).
 *
 * A basis the API refuses — a project without a reference revision (409), a marked revision
 * missing or not marked (422) — is said unavailable, and why, the rest of the screen shown. Any
 * other answer follows the rule of the reads (`readOrFail`).
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import { LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import {
  BASIS_REFUSED,
  type WorkloadAddress,
  type WorkloadAsked,
  type WorkloadBasis,
  type WorkloadRead,
  WorkloadSection,
} from "@/components/workload/workload-section";
import type { PageSearchParams, SearchParameters } from "@/navigation/context";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the function, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.workload", projectId);
}

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/** The bases of a workload, as the contract names them. */
const BASES: readonly WorkloadBasis[] = [
  "reference_budget",
  "marked_remaining",
  "current_remaining",
];

/** A parameter of the address, `undefined` when it is absent or empty. */
function given(address: SearchParameters, name: string): string | undefined {
  const value = address.get(name);
  return value === null || value === "" ? undefined : value;
}

/**
 * What the address asks of the workload: its basis — the remaining of the revision under way
 * unless it names another —, the marked revision of that basis, the node of organisation.
 */
function workloadAsked(address: SearchParameters): WorkloadAsked {
  const named = address.get("basis");
  return {
    basis: BASES.find((basis) => basis === named) ?? "current_remaining",
    revision: given(address, "workload_revision"),
    orgNode: given(address, "org_node_id"),
  };
}

/**
 * The workload on what the address asks — the marked revision sent only with the basis that takes
 * it, the node of organisation the server filters on —; the nodes of organisation and the marked
 * revisions of the project, which the choice offers.
 */
async function readWorkload({ revision }: GridAddress, asked: WorkloadAsked) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const query = {
    basis: asked.basis,
    ...(asked.basis === "marked_remaining" && asked.revision !== undefined
      ? { revision_id: asked.revision }
      : {}),
    ...(asked.orgNode === undefined ? {} : { org_node_id: asked.orgNode }),
  };
  const [workload, orgNodes, marked] = await Promise.all([
    readOrRefused("getProjectWorkload", BASIS_REFUSED, () =>
      client.GET("/projects/{project_id}/workload", { params: { path, query } }),
    ),
    readOrFail("listOrgNodes", () => client.GET("/reference/org-nodes")),
    readOrFail("listRevisions", () =>
      client.GET("/projects/{project_id}/revisions", {
        params: { path, query: { status: ["marked"] } },
      }),
    ),
  ]);
  return { workload: workload satisfies WorkloadRead, orgNodes, marked: marked.items };
}

/**
 * The bases the project admits (WF-DEV-0070): on a project without a reference revision, the
 * revision under way alone; the remaining of a marked revision, only when the project has one.
 */
function offeredBases(reading: ProjectReading, marked: readonly Revision[]): WorkloadBasis[] {
  if (reading.project.reference_revision_id === null) {
    return ["current_remaining"];
  }
  return marked.length === 0
    ? ["reference_budget", "current_remaining"]
    : ["reference_budget", "marked_remaining", "current_remaining"];
}

/** The parameters of the address as Next hands them, the first value of each. */
function parametersOf(search: PageSearchParams): WorkloadAddress["parameters"] {
  return Object.entries(search).flatMap(([name, value]) => {
    const first = typeof value === "string" ? value : value?.[0];
    return first === undefined ? [] : [[name, first] as const];
  });
}

/** The head of the screen and its workload. */
function WorkloadScreen({
  reading,
  read,
  asked,
  address,
}: {
  readonly reading: ProjectReading;
  readonly read: Awaited<ReturnType<typeof readWorkload>>;
  readonly asked: WorkloadAsked;
  readonly address: WorkloadAddress;
}) {
  const t = useTranslations();
  const { project } = reading;
  return (
    <Screen density="airy">
      <PageHeader title={t("functions.workload")} icon={LEAF_ICONS["FBS-4.4.4"]} density="airy" />
      <WorkloadSection
        workload={read.workload}
        asked={asked}
        bases={offeredBases(reading, read.marked)}
        marked={read.marked}
        orgNodes={read.orgNodes}
        address={address}
        project={{ label: project.label, code: project.code ?? project.project_id }}
        shown={reading.revision}
      />
    </Screen>
  );
}

/** Render the workload of a project. */
export default async function WorkloadPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "workload");
  const asked = workloadAsked(at.address);
  const [reading, read] = await Promise.all([
    readProjectContext(at.pathname, at.context),
    readWorkload(at, asked),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={reading} />
      <WorkloadScreen
        reading={reading}
        read={read}
        asked={asked}
        address={{ pathname: at.pathname, parameters: parametersOf(search) }}
      />
    </>
  );
}
