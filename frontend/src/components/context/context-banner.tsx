// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The banner of the reading context, on every screen of the data of a project (WF-IHM-0020):
 * the project, the revision read — its version name, its status, whether it is the reference
 * —, that it is read only when it is, and the active filters as chips, visible without
 * opening any panel, each with a link that lifts it; and, when the figures of the screen are
 * computed on another revision than the one the address names — a date `as_of` reads the last
 * marked revision before it —, the revision of the calculation (`CalculationContext.revision_id`),
 * named as the screen read it (#363). A filter that restricts only a part of the screen says so on
 * its chip: the chip says what it restricts — the grid and not the indicators (#459), every figure
 * of the indicators but the tracking of the milestones, which a sub-project does not have
 * (WF-IND-0020). A grid filtered by a lot or a post of the work breakdown gives its filter, which a
 * chip shows after those of the context, lifted by a link (`ChipLift`) that is the address shown
 * without it, or, by a click, the address last asked; so does « Écarts seulement » of a differential
 * and of the comparison of two revisions (US-0700). A grid that reads the structure its address
 * names — the planning, the estimate (US-0500) — gives it, and the banner names it, its kind
 * besides when it is not the main one — a differential, the own estimate of a risk —, and offers
 * the other structures of the revision to read instead (`StructureChoice`); a filter of the
 * context lifted leaves the grid on it. An icon before each fact, whose name the list of
 * definitions gives to a screen reader; the states in badges, in words.
 *
 * A server component: what it shows is the reading of the page, and a filter is lifted by
 * following a link, not by a state of the browser. It hands the project on to the shell, which
 * names it in its side bar and its breadcrumb (`ShowProject`).
 */
import { Calculator, Filter, Folder, GitBranch, Layers, Lock, X } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import {
  BREAKDOWN_PARAMETERS,
  type BreakdownChip,
  type BreakdownParameter,
} from "@/components/grid/breakdown-filter";
import {
  DIFFERENCE_PARAMETER,
  type DifferenceValue,
  isDifferencesOnly,
} from "@/components/grid/difference-filter";
import { ShowProject } from "@/components/shell/shown-project";
import { Badge } from "@/components/ui/badge";
import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";
import { UNASSIGNED } from "@/navigation/context";

import { ChipLift } from "./chip-lift";
import type { Revision } from "./read-only";
import type { ContextFilter, ProjectReading, Subproject } from "./reading";
import { type ListedStructure, runsOfKind, type StructureChoices } from "./structure";
import { StructureChoice } from "./structure-choice";

/**
 * A revision a calculation was made on (`CalculationContext.revision_id`), as the screen read it:
 * its version name, `null` for the revision under way, `undefined` when the API does not find it.
 */
export interface ComputedRevision {
  readonly revisionId: string;
  readonly versionName: string | null | undefined;
}

/** What the banner shows: the reading of the screen. */
export interface ContextBannerProps {
  readonly reading: ProjectReading;
  /**
   * The revision the figures of the screen are computed on, when the calculation context names
   * another than the address: the banner names it, so that no value is taken for one of the
   * revision shown.
   */
  readonly computedOn?: ComputedRevision | undefined;
  /**
   * The filters the screen reads that restrict a part of it alone, and which part: the grid — the
   * sub-project of the remaining to commit, whose indicators are those of the project whole —, or
   * all but the tracking of the milestones — the sub-project of the screen of the indicators, the
   * time/time diagram being computed for the project alone (WF-IND-0020). A filter not named
   * restricts the whole screen.
   */
  readonly restricts?: Restrictions | undefined;
  /**
   * The lot or the post the grid of the screen is filtered by (`breakdownChip`): a filter of the
   * grid, not of the context, which the links between functions do not carry on.
   */
  readonly breakdown?: BreakdownChip | undefined;
  /**
   * The differences the grid of a differential, or the comparison of two revisions, retains
   * (`readDifferenceFilter`, US-0700): « Écarts seulement » when it retains all three. A filter of
   * the grid, not of the context.
   */
  readonly difference?: readonly DifferenceValue[] | undefined;
  /**
   * The structure the grid of the screen reads, and those of its revision it may read instead; none
   * for a screen that reads the main structure alone, which the banner then does not name.
   */
  readonly structure?: StructureChoices | undefined;
}

/** The part of a screen a filter restricts alone, by the key of its text in the catalogue. */
export type Restriction = "grid" | "exceptMilestones";

/** The filters that restrict a part of a screen alone, and the part each restricts. */
export type Restrictions = Readonly<
  Partial<
    Record<ContextFilter["name"] | BreakdownParameter | typeof DIFFERENCE_PARAMETER, Restriction>
  >
>;

/**
 * A chip of an active filter: its parameter, its text, and the parameters of an address that carry
 * it.
 */
interface Chip {
  readonly name: ContextFilter["name"] | BreakdownParameter | typeof DIFFERENCE_PARAMETER;
  readonly text: string;
  readonly lifts: readonly string[];
}

const FACT = "flex shrink-0 items-center gap-1.5";
const ICON = "size-3.5 shrink-0 text-muted-foreground";

/**
 * A date the address carries, shown as a date of the contract; as it is when it is none — the
 * address is the user's to write, and the API refuses it.
 */
function addressDate(value: string, locale: Locale): string {
  try {
    return formatPlanningDate(value, locale);
  } catch {
    return value;
  }
}

/**
 * The name of the sub-project a filter retains: its code and its label, « outside any sub-project »,
 * or, for a sub-project the project does not have, the identifier the address gives.
 */
export function useSubprojectName(): (value: string, subproject: Subproject | undefined) => string {
  const t = useTranslations();
  return (value, subproject) => {
    if (subproject !== undefined) {
      return t("contextBanner.subprojectName", { code: subproject.code, label: subproject.label });
    }
    return value === UNASSIGNED ? t("enums.SubprojectFilter.unassigned") : value;
  };
}

/**
 * The chips of the active filters — those of the context, then the lot or the post of the grid —,
 * each saying the filter, and the part of the screen it restricts when not the whole.
 */
function useChips(
  reading: ProjectReading,
  restricts: Restrictions,
  breakdown: BreakdownChip | undefined,
  difference: readonly DifferenceValue[] | undefined,
): Chip[] {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const subprojectName = useSubprojectName();
  const named = (filter: ContextFilter) =>
    filter.name === "as_of"
      ? t("contextBanner.asOf", { date: addressDate(filter.value, locale) })
      : t("contextBanner.subproject", {
          subproject: subprojectName(filter.value, filter.subproject),
        });
  const restricted = (name: Chip["name"], text: string) => {
    const part = restricts[name];
    return part === undefined ? text : t(`contextBanner.restricts.${part}`, { filter: text });
  };
  return [
    ...reading.filters.map((filter) => ({
      name: filter.name,
      text: restricted(filter.name, named(filter)),
      lifts: [filter.name],
    })),
    ...(breakdown === undefined
      ? []
      : [
          {
            name: breakdown.filter.name,
            text: restricted(
              breakdown.filter.name,
              t("contextBanner.breakdown", {
                kind: breakdown.filter.kind,
                label: breakdown.item?.label ?? breakdown.filter.value,
              }),
            ),
            lifts: Object.values(BREAKDOWN_PARAMETERS),
          },
        ]),
    ...(difference === undefined
      ? []
      : [
          {
            name: DIFFERENCE_PARAMETER,
            text: restricted(
              DIFFERENCE_PARAMETER,
              isDifferencesOnly(difference)
                ? t("contextBanner.differencesOnly")
                : t("contextBanner.differences", {
                    values: format.list(
                      difference.map((value) => t(`enums.NodeDifferenceFilter.${value}`)),
                    ),
                  }),
            ),
            lifts: [DIFFERENCE_PARAMETER],
          },
        ]),
  ];
}

/**
 * The revision read: its name, its status, the revision it is a copy of when it has one
 * (`source_version_name`, WF-IHM-0020), whether it is the reference. The source is shown at every
 * width: its width is bounded (4.5rem under the medium window, enough for « Copie de » and its
 * start, which the structure and the filters need beside it at 700 px) and it is cut with an
 * ellipsis, its full text in the `title`, so that the banner keeps its one row on a narrow window,
 * the totals of the grid in view under it (WF-IHM-0060); no other fact shrinks, the banner wrapping when the room lacks.
 */
function RevisionFacts({ revision }: { readonly revision: Revision }) {
  const t = useTranslations();
  const source =
    revision.source_version_name === null
      ? undefined
      : t("contextBanner.sourceRevision", { name: revision.source_version_name });
  return (
    <div className={FACT}>
      <dt>
        <GitBranch aria-hidden="true" className={ICON} />
        <span className="sr-only">{t("contextBanner.revision")}</span>
      </dt>
      <dd>{revision.version_name ?? t("contextBanner.currentRevision")}</dd>
      <dd>
        <Badge>{t(`enums.RevisionStatus.${revision.status}`)}</Badge>
      </dd>
      {source === undefined ? null : (
        <dd className="max-w-[4.5rem] truncate md:max-w-64" title={source}>
          {source}
        </dd>
      )}
      {revision.is_reference ? (
        <dd>
          <Badge variant="outline">{t("contextBanner.reference")}</Badge>
        </dd>
      ) : null}
    </div>
  );
}

/**
 * The structure read, and the others of the revision offered when it has some — each named by its
 * label and whether it is merged, under the name of its kind but for the main one. A grid opened on a
 * differential, or on the own estimate of a risk, names it and its kind in a badge (WF-IHM-0020); the
 * main structure, which the head of the grid names too, is named to a screen reader alone, so that
 * the banner keeps its one row on a narrow window, the totals of the grid in view under it — and not
 * at all when the revision has no other, nothing being offered.
 */
function StructureFacts({ structure }: { readonly structure: StructureChoices }) {
  const t = useTranslations();
  const { read, listed } = structure;
  if (read.kind === "main" && listed.length < 2) {
    return null;
  }
  const option = ({ structure_id, label, kind, is_merged }: ListedStructure) => ({
    structure_id,
    kind,
    text: is_merged ? t("contextBanner.mergedStructure", { label }) : label,
  });
  const groups = runsOfKind(listed).map(({ kind, structures }) => ({
    name: kind === "main" ? undefined : t(`enums.StructureKind.${kind}`),
    options: structures.map(option),
  }));
  return (
    <div className={FACT}>
      <dt>
        <Layers aria-hidden="true" className={ICON} />
        <span className="sr-only">{t("contextBanner.structure")}</span>
      </dt>
      <dd className={read.kind === "main" ? "sr-only" : undefined}>{read.label}</dd>
      {read.kind === "main" ? null : (
        <dd>
          <Badge variant="outline">{t(`enums.StructureKind.${read.kind}`)}</Badge>
        </dd>
      )}
      {listed.length > 1 ? (
        <dd>
          <StructureChoice
            label={t("contextBanner.chooseStructure", { structure: read.label })}
            groups={groups}
            chosen={read.structure_id}
          />
        </dd>
      ) : null}
    </div>
  );
}

/** The revision the figures are computed on, when it is not the one shown. */
function ComputedOnFacts({ computedOn }: { readonly computedOn: ComputedRevision }) {
  const t = useTranslations("contextBanner");
  const { versionName } = computedOn;
  return (
    <div className={FACT}>
      <dt>
        <Calculator aria-hidden="true" className={ICON} />
        <span className="sr-only">{t("computedOn")}</span>
      </dt>
      <dd>
        <Badge variant="outline">
          {versionName === undefined ? t("unnamedRevision") : (versionName ?? t("currentRevision"))}
        </Badge>
      </dd>
    </div>
  );
}

/** Render the reading context of a screen of a project. */
export function ContextBanner({
  reading,
  computedOn,
  restricts = {},
  breakdown,
  difference,
  structure,
}: ContextBannerProps) {
  const t = useTranslations();
  const chips = useChips(reading, restricts, breakdown, difference);
  const { project, revision, readOnly } = reading;
  return (
    <section
      aria-label={t("contextBanner.label")}
      className="flex min-h-10 flex-wrap items-center gap-x-4 gap-y-1 border-b bg-muted px-5 py-1.5 text-xs text-foreground"
    >
      <ShowProject
        project={{
          project_id: project.project_id,
          label: project.label,
          code: project.code ?? null,
          state: project.state,
        }}
      />
      <dl className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <div className={FACT}>
          <dt>
            <Folder aria-hidden="true" className={ICON} />
            <span className="sr-only">{t("contextBanner.project")}</span>
          </dt>
          <dd className="font-medium">{project.label}</dd>
        </div>
        {revision === undefined ? null : <RevisionFacts revision={revision} />}
        {structure === undefined ? null : <StructureFacts structure={structure} />}
        {computedOn === undefined || computedOn.revisionId === revision?.revision_id ? null : (
          <ComputedOnFacts computedOn={computedOn} />
        )}
      </dl>
      {readOnly ? (
        <p className={`${FACT} font-medium`}>
          <Lock aria-hidden="true" className={ICON} />
          {t("contextBanner.readOnly")}
        </p>
      ) : null}
      {chips.length === 0 ? null : (
        <ul aria-label={t("contextBanner.filters")} className="ml-auto flex flex-wrap gap-1.5">
          {chips.map(({ name, text, lifts }) => (
            <li
              key={name}
              className="flex h-6 items-center gap-1.5 rounded-full border bg-background pr-1 pl-2"
            >
              <Filter aria-hidden="true" className={ICON} />
              {text}
              <ChipLift lifts={lifts} label={t("contextBanner.removeFilter", { filter: text })}>
                <X aria-hidden="true" className="size-3" />
              </ChipLift>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
