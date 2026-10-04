// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of a project (FBS-4.8, US-0240), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the indicators FBS-4.8.1 to
 * FBS-4.8.5 as the API computes them for the sub-project and at the date the address filters
 * (`getProjectIndicators`, `scope`, `as_of`), with the evolution of the indices
 * (`getIndexHistory`, WF-IND-0130); the tracking of the milestones (`getMilestoneTracking`,
 * WF-IND-0090); the cumulative costs at the same date, shifted by the payment delays when the
 * address asks it (`getCostCurve`, `payment_delays`, WF-IND-0100), and the curves of earned value
 * for the same sub-project (`getEarnedValueCurves`, WF-IND-0110); and the workload of the project
 * (FBS-4.4.4, `getProjectWorkload`, WF-DEV-0070) on the basis, the marked revision and the node
 * of organisation the address asks, exported as a PNG image (WF-IHM-0130).
 *
 * The indicators of a project are computed from the state In progress only (WF-IND-0010): before,
 * the API refuses them (409, `STATE_FORBIDS_OPERATION`), and the screen says so rather than coming
 * down, the evolution of the indices and the cumulative curves left unasked. A basis of the
 * workload the API refuses — a project without a reference revision (409), a marked revision
 * missing or not marked (422) — is said unavailable, the rest of the screen shown. Any other
 * answer follows the rule of the reads (`readOrFail`): the screen never shows a figure it did not
 * read, and computes none.
 */
import { Info, TriangleAlert } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import {
  CostCurveSection,
  EarnedValueSection,
  MilestoneSection,
  PAYMENT_DELAYS,
  type ScreenAddress,
  type WorkloadAsked,
  type WorkloadBasis,
  WorkloadSection,
} from "@/components/indicators/indicator-sections";
import { ProjectIndicatorCards } from "@/components/indicators/project-indicators";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  return screenMetadata("functions.projectIndicators", projectId);
}

/** The refusal of the indicators of a project not yet in progress (WF-IND-0010). */
const NOT_IN_PROGRESS = [{ status: 409, code: "STATE_FORBIDS_OPERATION" }] as const;

/**
 * The indicators of the project for the sub-project and at the date the address filters, then
 * the evolution of its indices and its cumulative curves — the costs at the same date, shifted
 * by the payment delays when the address asks it, the earned value for the same sub-project too
 * —; none of them when the project is not yet in progress, the others left unasked.
 */
async function readIndicators({ revision, context, address }: GridAddress) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const scope = context.parameters.get("subproject_id");
  const asOf = context.parameters.get("as_of");
  const dated = asOf === null ? {} : { as_of: asOf };
  const query = { ...(scope === null ? {} : { scope }), ...dated };
  const indicators = await readUnlessRefused("getProjectIndicators", NOT_IN_PROGRESS, () =>
    client.GET("/projects/{project_id}/indicators", { params: { path, query } }),
  );
  if (indicators === undefined) {
    return undefined;
  }
  const delays = address.get(PAYMENT_DELAYS) === "true" ? { payment_delays: true } : {};
  const [history, costs, earnedValue] = await Promise.all([
    readOrFail("getIndexHistory", () =>
      client.GET("/projects/{project_id}/indicators/index-history", { params: { path } }),
    ),
    readOrFail("getCostCurve", () =>
      client.GET("/projects/{project_id}/indicators/cost-curve", {
        params: { path, query: { ...dated, ...delays } },
      }),
    ),
    readOrFail("getEarnedValueCurves", () =>
      client.GET("/projects/{project_id}/indicators/earned-value-curves", {
        params: { path, query },
      }),
    ),
  ]);
  return { indicators, history, costs, earnedValue };
}

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

/** The refusals of a basis of the workload, which the screen says unavailable (WF-DEV-0070). */
const BASIS_REFUSED = [
  { status: 409, code: "STATE_FORBIDS_OPERATION" },
  { status: 422, code: "VALIDATION_FAILED" },
] as const;

/**
 * The tracking of the milestones; the workload on what the address asks, the marked revision
 * sent only with the basis that takes it, the node of organisation the server filters on; the
 * nodes of organisation and the marked revisions of the project, which the choice offers.
 */
async function readTracking({ revision }: GridAddress, asked: WorkloadAsked) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const query = {
    basis: asked.basis,
    ...(asked.basis === "marked_remaining" && asked.revision !== undefined
      ? { revision_id: asked.revision }
      : {}),
    ...(asked.orgNode === undefined ? {} : { org_node_id: asked.orgNode }),
  };
  const [milestones, workload, orgNodes, marked] = await Promise.all([
    readOrFail("getMilestoneTracking", () =>
      client.GET("/projects/{project_id}/indicators/milestone-tracking", { params: { path } }),
    ),
    readUnlessRefused("getProjectWorkload", BASIS_REFUSED, () =>
      client.GET("/projects/{project_id}/workload", { params: { path, query } }),
    ),
    readOrFail("listOrgNodes", () => client.GET("/reference/org-nodes")),
    readOrFail("listRevisions", () =>
      client.GET("/projects/{project_id}/revisions", {
        params: { path, query: { status: ["marked"] } },
      }),
    ),
  ]);
  return { milestones, workload, orgNodes, marked: marked.items };
}

/** The figures of the screen: the indicators, the evolution of the indices, the curves. */
type Figures = NonNullable<Awaited<ReturnType<typeof readIndicators>>>;

/** What the screen says when the API does not compute the indicators of the project yet. */
function NotInProgress() {
  const t = useTranslations("projectIndicators.notInProgress");
  return (
    <Alert>
      <TriangleAlert aria-hidden="true" />
      <AlertTitle>{t("title")}</AlertTitle>
      <AlertDescription>{t("explanation")}</AlertDescription>
    </Alert>
  );
}

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/**
 * The revisions the figures and the workload are computed on, when it is not the revision of the
 * address: the contract does not let the screen ask the indicators of a given revision (#247) — it
 * gives those of the revision under way, or of the last marked revision before the date `as_of`
 * asks —, and the workload reads the revision of its basis. Each is read once by its identifier
 * (`getRevision`), only then, for its version name; one the API does not find is said unnamed,
 * never left out, and the screen stays. Any other answer follows the rule of the reads.
 */
async function readRevisionsOf(
  projectId: string,
  shown: string | undefined,
  ids: readonly string[],
): Promise<ReadonlyMap<string, Revision | undefined>> {
  const elsewhere = [...new Set(ids)].filter((id) => id !== shown);
  const client = serverClient();
  const read = await Promise.all(
    elsewhere.map((id) =>
      readUnlessRefused("getRevision", [{ status: 404 }], () =>
        client.GET("/projects/{project_id}/revisions/{revision_id}", {
          params: { path: { project_id: projectId, revision_id: id } },
        }),
      ),
    ),
  );
  return new Map(elsewhere.map((id, index) => [id, read[index]]));
}

/**
 * What the screen says, at its head, when its figures are computed on another revision than the
 * one its banner names: never in silence (WF-IHM-0020).
 */
function ComputedElsewhere({
  revisions,
}: {
  readonly revisions: readonly (Revision | undefined)[];
}) {
  const t = useTranslations();
  if (revisions.length === 0) {
    return null;
  }
  const name = (revision: Revision | undefined) =>
    revision === undefined
      ? t("projectIndicators.elsewhere.unknown")
      : (revision.version_name ?? t("contextBanner.currentRevision"));
  return (
    <Alert>
      <Info aria-hidden="true" />
      <AlertTitle>{t("projectIndicators.elsewhere.title")}</AlertTitle>
      <AlertDescription>
        {revisions.map((revision, index) => (
          <p key={revision?.revision_id ?? index}>
            {t("projectIndicators.elsewhere.explanation", { revision: name(revision) })}
          </p>
        ))}
      </AlertDescription>
    </Alert>
  );
}

/** The name of a revision: its version name, the revision under way, or unnamed. */
function useRevisionLabel() {
  const t = useTranslations();
  return (name: string | null | undefined) =>
    name === undefined
      ? t("projectIndicators.elsewhere.unknown")
      : (name ?? t("contextBanner.currentRevision"));
}

/** The parameters of the address as Next hands them, the first value of each. */
function parametersOf(search: PageSearchParams): ScreenAddress["parameters"] {
  return Object.entries(search).flatMap(([name, value]) => {
    const first = typeof value === "string" ? value : value?.[0];
    return first === undefined ? [] : [[name, first] as const];
  });
}

/** The bases the project offers (WF-DEV-0070): see `WorkloadSectionProps.bases`. */
function offeredBases(reading: ProjectReading, marked: readonly unknown[]): WorkloadBasis[] {
  if (reading.project.reference_revision_id === null) {
    return ["current_remaining"];
  }
  return marked.length === 0
    ? ["reference_budget", "current_remaining"]
    : ["reference_budget", "marked_remaining", "current_remaining"];
}

/** What the screen shows below the cards of the indicators. */
function Sections({
  reading,
  figures,
  tracking,
  asked,
  address,
  workloadRevision,
}: {
  readonly reading: ProjectReading;
  readonly figures: Figures | undefined;
  readonly tracking: Awaited<ReturnType<typeof readTracking>>;
  readonly asked: WorkloadAsked;
  readonly address: ScreenAddress;
  readonly workloadRevision: string | null | undefined;
}) {
  const label = useRevisionLabel();
  const { project } = reading;
  return (
    <>
      <MilestoneSection tracking={tracking.milestones} />
      {figures === undefined ? null : (
        <>
          <CostCurveSection curves={figures.costs} address={address} />
          <EarnedValueSection curves={figures.earnedValue} />
        </>
      )}
      <WorkloadSection
        workload={tracking.workload}
        asked={asked}
        bases={offeredBases(reading, tracking.marked)}
        marked={tracking.marked}
        orgNodes={tracking.orgNodes}
        address={address}
        project={{ label: project.label, code: project.code ?? project.project_id }}
        revision={label(workloadRevision)}
      />
    </>
  );
}

/** The header of the screen: the name and the icon of the function. */
function IndicatorsHeader() {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.projectIndicators")}
      icon={FUNCTION_ICONS.project_indicators}
      density={FUNCTION_DENSITY.project_indicators}
    />
  );
}

/** Render the indicators of a project, its curves, its milestones and its workload. */
export default async function IndicatorsPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "indicators");
  const asked = workloadAsked(at.address);
  const [reading, figures, tracking] = await Promise.all([
    readProjectContext(at.pathname, at.context),
    readIndicators(at),
    readTracking(at, asked),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  const shown = reading.revision;
  const computedOn =
    figures === undefined
      ? []
      : [...new Set([figures.indicators.context.revision_id, figures.history.context.revision_id])];
  const workloadOn = tracking.workload?.context.revision_id;
  const named = await readRevisionsOf(revision.projectId, shown?.revision_id, [
    ...computedOn,
    ...(workloadOn === undefined ? [] : [workloadOn]),
  ]);
  const elsewhere = computedOn.filter((id) => id !== shown?.revision_id).map((id) => named.get(id));
  // The version name of the revision of the workload: `null` under way, `undefined` unnamed.
  const workloadRevision =
    workloadOn === shown?.revision_id
      ? shown?.version_name
      : named.get(workloadOn ?? "")?.version_name;
  return (
    <>
      <ContextBanner reading={reading} />
      <Screen density={FUNCTION_DENSITY.project_indicators}>
        <IndicatorsHeader />
        <ComputedElsewhere revisions={elsewhere} />
        {figures === undefined ? (
          <NotInProgress />
        ) : (
          <ProjectIndicatorCards indicators={figures.indicators} history={figures.history} />
        )}
        <Sections
          reading={reading}
          figures={figures}
          tracking={tracking}
          asked={asked}
          address={{ pathname: at.pathname, parameters: parametersOf(search) }}
          workloadRevision={workloadRevision}
        />
      </Screen>
    </>
  );
}
