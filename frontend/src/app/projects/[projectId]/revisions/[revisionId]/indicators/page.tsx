// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of a project (FBS-4.8, US-0240), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the indicators FBS-4.8.1 to
 * FBS-4.8.5 as the API computes them for the sub-project the address filters, on the revision of
 * the address — a marked one as its marking kept them (WF-DAT-0040) —, or at the date the address
 * asks, which chooses the revision itself (`getProjectIndicators`, `scope`, `revision_id`,
 * `as_of`), with the evolution of the indices for the same sub-project (`getIndexHistory`, `scope`,
 * WF-IND-0130); the tracking of the milestones (`getMilestoneTracking`, WF-IND-0090); the
 * cumulative costs for the same sub-project, on the same revision or at the same date, shifted by
 * the payment delays when the address asks it (`getCostCurve`, `scope`, `payment_delays`,
 * WF-IND-0100), and the curves of earned value for the same sub-project too
 * (`getEarnedValueCurves`, WF-IND-0110) — each of the three exported as
 * a PNG image that names the project, the revision of its calculation and its date (WF-IHM-0130).
 *
 * When a date `as_of` computes the indicators on another revision than the one the address names,
 * the banner names the revision of the calculation (#363); the evolution of the indices, always
 * computed on the revision under way, is said at the head of the screen. The sub-project the
 * address filters — the one the banner shows (WF-IHM-0020) — restricts what the API reads for it
 * (`scope`, WF-IND-0020): the indicators, the evolution of the indices, the cumulative costs and
 * the curves of earned value. The tracking of the milestones is computed for the project alone: it
 * follows milestones, which a sub-project does not have (WF-IND-0020); the banner says so on its
 * chip, and the tracking that it covers the whole project.
 *
 * The indicators of a project are computed from the state In progress only (WF-IND-0010): before,
 * the API refuses them (409, `STATE_FORBIDS_OPERATION`), and the screen says so rather than coming
 * down, the evolution of the indices and the cumulative curves left unasked; so too of a
 * sub-project the project does not have (422, `UNKNOWN_SUBPROJECT` on `/query/scope`), never read
 * as figures of nothing. A curve with nothing to draw says so rather than drawing a zero. Any other
 * answer follows the rule of the reads (`readOrFail`): the screen never shows a figure it did not
 * read, and computes none.
 */
import { Info, TriangleAlert } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import {
  type Problem,
  readOrFail,
  readOrRefused,
  readUnlessRefused,
  refusalOf,
} from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  type ComputedRevision,
  ContextBanner,
  type Restrictions,
  useSubprojectName,
} from "@/components/context/context-banner";
import {
  type ContextFilter,
  type ProjectReading,
  readProjectContext,
} from "@/components/context/reading";
import {
  CostCurveSection,
  EarnedValueSection,
  MilestoneSection,
  PAYMENT_DELAYS,
  type ScreenAddress,
} from "@/components/indicators/indicator-sections";
import type { MilestoneTracking } from "@/components/indicators/milestone-chart";
import { ProjectIndicatorCards } from "@/components/indicators/project-indicators";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { PageSearchParams } from "@/navigation/context";

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

/**
 * The sub-project the screen filters restricts every figure of it but the tracking of the
 * milestones, computed for the project alone (WF-IND-0020).
 */
const RESTRICTS: Restrictions = { subproject_id: "exceptMilestones" };

/** The filter of a sub-project. */
type SubprojectFilter = Extract<ContextFilter, { name: "subproject_id" }>;

/** The sub-project the reading filters, if any. */
function subprojectFilter(reading: ProjectReading): SubprojectFilter | undefined {
  return reading.filters.find(
    (filter): filter is SubprojectFilter => filter.name === "subproject_id",
  );
}

/**
 * The refusals of the indicators the screen says rather than coming down: a project not yet in
 * progress (409, WF-IND-0010), and a sub-project the project does not have (422, `/query/scope`).
 */
const REFUSED = [
  { status: 409, code: "STATE_FORBIDS_OPERATION" },
  { status: 422, code: "VALIDATION_FAILED" },
] as const;

/** Why the screen reads no indicator: the key of what it says in the catalogue. */
type IndicatorsRefusal = "notInProgress" | "unknownScope";

/**
 * Why the API refused the indicators: a project not yet in progress, or a sub-project it does not
 * have; any other refusal of a parameter is the screen's fault, thrown as an unexpected answer.
 */
function indicatorsRefusal(status: number, problem: Problem): IndicatorsRefusal {
  if (status === 409) {
    return "notInProgress";
  }
  const scope = (problem.fields ?? []).some(
    (field) => field.pointer === "/query/scope" && field.code === "UNKNOWN_SUBPROJECT",
  );
  if (!scope) {
    throw refusalOf("getProjectIndicators", status, problem);
  }
  return "unknownScope";
}

/**
 * The indicators of the project for the sub-project the address filters, on its revision or at the
 * date it asks — the API refuses both together —, then the evolution of its indices for the same
 * sub-project and its cumulative curves — the costs and the earned value for the same sub-project,
 * on the same revision or at the same date, the costs shifted by the payment delays when the
 * address asks it —; or why the API refused the indicators — a project not yet in progress, a
 * sub-project it does not have —, the others left unasked.
 */
async function readIndicators({ revision, context, address }: GridAddress) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const scope = context.parameters.get("subproject_id");
  const asOf = context.parameters.get("as_of");
  const dated = asOf === null ? { revision_id: revision.revisionId } : { as_of: asOf };
  const scoped = scope === null ? {} : { scope };
  const query = { ...scoped, ...dated };
  const read = await readOrRefused("getProjectIndicators", REFUSED, () =>
    client.GET("/projects/{project_id}/indicators", { params: { path, query } }),
  );
  if (read.kind === "refused") {
    return { refused: indicatorsRefusal(read.refusal.status, read.problem) } as const;
  }
  const indicators = read.data;
  const delays = address.get(PAYMENT_DELAYS) === "true" ? { payment_delays: true } : {};
  const [history, costs, earnedValue] = await Promise.all([
    readOrFail("getIndexHistory", () =>
      client.GET("/projects/{project_id}/indicators/index-history", {
        params: { path, query: scoped },
      }),
    ),
    readOrFail("getCostCurve", () =>
      client.GET("/projects/{project_id}/indicators/cost-curve", {
        params: { path, query: { ...query, ...delays } },
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

/**
 * The tracking of the milestones, which the API gives whatever the state of the project, for the
 * project alone: a sub-project has no milestones (WF-IND-0020).
 */
async function readMilestones({ revision }: GridAddress) {
  return readOrFail("getMilestoneTracking", () =>
    serverClient().GET("/projects/{project_id}/indicators/milestone-tracking", {
      params: { path: { project_id: revision.projectId } },
    }),
  );
}

/** The figures of the screen: the indicators, the evolution of the indices, the curves. */
type Figures = Exclude<Awaited<ReturnType<typeof readIndicators>>, { readonly refused: unknown }>;

/**
 * What the screen says when the API does not compute the indicators: not yet, the project not in
 * progress; or not for the sub-project the address names, which the project does not have.
 */
function IndicatorsRefused({ reason }: { readonly reason: IndicatorsRefusal }) {
  const t = useTranslations(`projectIndicators.${reason}`);
  return (
    <Alert>
      <TriangleAlert aria-hidden="true" />
      <AlertTitle>{t("title")}</AlertTitle>
      <AlertDescription>{t("explanation")}</AlertDescription>
    </Alert>
  );
}

/** The cards of the indicators and the evolution of their indices, or why the API computes none. */
function IndicatorsOrWhy({ read }: { readonly read: Awaited<ReturnType<typeof readIndicators>> }) {
  return "refused" in read ? (
    <IndicatorsRefused reason={read.refused} />
  ) : (
    <ProjectIndicatorCards indicators={read.indicators} history={read.history} />
  );
}

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/**
 * The revisions the figures and the charts are computed on, when it is not the revision of the
 * address: the evolution of the indices, always computed today on the revision under way, and the
 * figures of the last marked revision before the date `as_of` asks; an exported chart names its
 * revision. Each is read once by its identifier
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
 * What the screen says, at its head, when the evolution of the indices is computed on another
 * revision than the indicators — always today, on the revision under way —: never in silence
 * (WF-IHM-0020). The revision of the indicators is the one the banner names: the revision of the
 * address, or the revision of the calculation a date `as_of` chose (`computedOn`, #363).
 */
function ComputedElsewhere({ history }: { readonly history: Revision | undefined }) {
  const t = useTranslations();
  const revision =
    history === undefined
      ? t("contextBanner.unnamedRevision")
      : (history.version_name ?? t("contextBanner.currentRevision"));
  return (
    <Alert>
      <Info aria-hidden="true" />
      <AlertTitle>{t("projectIndicators.elsewhere.title")}</AlertTitle>
      <AlertDescription>
        <p>{t("projectIndicators.elsewhere.history", { revision })}</p>
      </AlertDescription>
    </Alert>
  );
}

/** The name of a revision: its version name, the revision under way, or unnamed. */
function useRevisionLabel() {
  const t = useTranslations();
  return (name: string | null | undefined) =>
    name === undefined
      ? t("contextBanner.unnamedRevision")
      : (name ?? t("contextBanner.currentRevision"));
}

/** The parameters of the address as Next hands them, the first value of each. */
function parametersOf(search: PageSearchParams): ScreenAddress["parameters"] {
  return Object.entries(search).flatMap(([name, value]) => {
    const first = typeof value === "string" ? value : value?.[0];
    return first === undefined ? [] : [[name, first] as const];
  });
}

/** The version name of a revision: `null` for the one under way, `undefined` when unnamed. */
type RevisionName = (revisionId: string) => string | null | undefined;

/** What the screen shows below the cards of the indicators, each chart with its provenance. */
function Sections({
  reading,
  figures,
  milestones,
  address,
  nameOf,
}: {
  readonly reading: ProjectReading;
  readonly figures: Figures | undefined;
  readonly milestones: MilestoneTracking;
  readonly address: ScreenAddress;
  readonly nameOf: RevisionName;
}) {
  const t = useTranslations("projectIndicators.provenance");
  const label = useRevisionLabel();
  const subprojectName = useSubprojectName();
  const { project } = reading;
  // A sub-project filtered, which the tracking of the milestones does not have: the image of each
  // chart says what it is computed on, the sub-project or the project whole.
  const filtered = subprojectFilter(reading);
  const provenance = (revisionId: string, restricted: boolean) => ({
    project: project.label,
    code: project.code ?? project.project_id,
    revision: label(nameOf(revisionId)),
    ...(filtered === undefined
      ? {}
      : {
          detail: restricted
            ? t("subproject", { subproject: subprojectName(filtered.value, filtered.subproject) })
            : t("wholeProject"),
        }),
  });
  return (
    <>
      <MilestoneSection
        tracking={milestones}
        provenance={provenance(milestones.context.revision_id, false)}
        wholeProject={filtered !== undefined}
      />
      {figures === undefined ? null : (
        <>
          <CostCurveSection
            curves={figures.costs}
            address={address}
            provenance={provenance(figures.costs.context.revision_id, true)}
          />
          <EarnedValueSection
            curves={figures.earnedValue}
            provenance={provenance(figures.earnedValue.context.revision_id, true)}
          />
        </>
      )}
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

/** Render the indicators of a project, its curves and its milestones. */
export default async function IndicatorsPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "indicators");
  const [reading, read, milestones] = await Promise.all([
    readProjectContext(at.pathname, at.context, ["subproject_id", "as_of"]),
    readIndicators(at),
    readMilestones(at),
  ]);
  const figures = "refused" in read ? undefined : read;
  if (reading === "not_found") {
    notFound();
  }
  const shown = reading.revision;
  const computedOn = figures?.indicators.context.revision_id;
  const history = figures?.history.context.revision_id;
  const charted = [
    milestones.context.revision_id,
    ...(figures === undefined
      ? []
      : [figures.costs.context.revision_id, figures.earnedValue.context.revision_id]),
  ];
  const named = await readRevisionsOf(revision.projectId, shown?.revision_id, [
    ...(computedOn === undefined ? [] : [computedOn]),
    ...(history === undefined ? [] : [history]),
    ...charted,
  ]);
  const nameOf: RevisionName = (id) =>
    id === shown?.revision_id ? shown.version_name : named.get(id)?.version_name;
  // The banner names the revision the indicators are computed on when it is not the one shown;
  // the evolution of the indices, computed on its own, is said at the head of the screen.
  const indicatorsOn: ComputedRevision | undefined =
    computedOn === undefined
      ? undefined
      : { revisionId: computedOn, versionName: nameOf(computedOn) };
  return (
    <>
      <ContextBanner reading={reading} computedOn={indicatorsOn} restricts={RESTRICTS} />
      <Screen density={FUNCTION_DENSITY.project_indicators}>
        <IndicatorsHeader />
        {history === undefined || history === (computedOn ?? shown?.revision_id) ? null : (
          <ComputedElsewhere history={named.get(history)} />
        )}
        <IndicatorsOrWhy read={read} />
        <Sections
          reading={reading}
          figures={figures}
          milestones={milestones}
          address={{ pathname: at.pathname, parameters: parametersOf(search) }}
          nameOf={nameOf}
        />
      </Screen>
    </>
  );
}
