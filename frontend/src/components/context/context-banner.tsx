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
 * chip shows after those of the context, lifted by the address of the screen without it. An icon
 * before each
 * fact, whose name the list of definitions gives to a screen reader; the states in badges, in
 * words.
 *
 * A server component: what it shows is the reading of the page, and a filter is lifted by
 * following a link, not by a state of the browser. It hands the project on to the shell, which
 * names it in its side bar and its breadcrumb (`ShowProject`).
 */
import { Calculator, Filter, Folder, GitBranch, Lock, X } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import type { BreakdownChip, BreakdownParameter } from "@/components/grid/breakdown-filter";
import { ShowProject } from "@/components/shell/shown-project";
import { Badge } from "@/components/ui/badge";
import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";
import { UNASSIGNED, withoutFilter } from "@/navigation/context";

import type { Revision } from "./read-only";
import type { ContextFilter, ProjectReading, Subproject } from "./reading";

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
}

/** The part of a screen a filter restricts alone, by the key of its text in the catalogue. */
export type Restriction = "grid" | "exceptMilestones";

/** The filters that restrict a part of a screen alone, and the part each restricts. */
export type Restrictions = Readonly<
  Partial<Record<ContextFilter["name"] | BreakdownParameter, Restriction>>
>;

/** A chip of an active filter: its parameter, its text, and the address that lifts it. */
interface Chip {
  readonly name: ContextFilter["name"] | BreakdownParameter;
  readonly text: string;
  readonly lift: string;
}

const FACT = "flex items-center gap-1.5";
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
): Chip[] {
  const t = useTranslations();
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
      lift: withoutFilter(reading.pathname, reading.context, filter.name),
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
            lift: breakdown.lift,
          },
        ]),
  ];
}

/** The revision read: its name, its status, whether it is the reference. */
function RevisionFacts({ revision }: { readonly revision: Revision }) {
  const t = useTranslations();
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
      {revision.is_reference ? (
        <dd>
          <Badge variant="outline">{t("contextBanner.reference")}</Badge>
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
}: ContextBannerProps) {
  const t = useTranslations();
  const chips = useChips(reading, restricts, breakdown);
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
          {chips.map(({ name, text, lift }) => (
            <li
              key={name}
              className="flex h-6 items-center gap-1.5 rounded-full border bg-background pr-1 pl-2"
            >
              <Filter aria-hidden="true" className={ICON} />
              {text}
              <Link
                href={lift}
                aria-label={t("contextBanner.removeFilter", { filter: text })}
                className="rounded-full p-0.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring"
              >
                <X aria-hidden="true" className="size-3" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
