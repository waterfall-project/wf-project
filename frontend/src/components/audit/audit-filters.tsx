// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the journal of audit (FBS-1.5, WF-SEC-0030, #2916), folded into the bar of its grid
 * (`filtering`): by period, by author — an account, or whether an account or the platform acted —,
 * by action, by project, by object kind, and by the correlation of a request (WF-OBS-0020); the one
 * object whose history the address asks is told by a chip. The authors and the projects to choose
 * are those the whole journal names (`listAuditFacets`), which the consultation of the journal
 * alone reads (WF-ADM-0100) — an account anonymised by the neutral label, never by a name it no
 * longer has (WF-ADM-0060). A filter chosen only changes the address, under the names of the
 * contract (`audit-address.ts`), back to the first page; the page reads anew the inscriptions the
 * server retains. The front filters nothing. A change goes on from the address last asked
 * (`usePendingAddress`): a filter chosen right after a sort or another filter keeps it.
 *
 * The period is two instants, entered in the local time of the workstation and sent as the
 * contract takes them, in universal time, the start included and the end excluded (`PeriodFilter`,
 * `instant`): only the browser knows its time zone, so the fields show the instants of the address
 * once the page is hydrated, and the period is applied from then on. An end the API refuses for
 * preceding the start is said at its field, the start named in the local time.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import { useAccountNaming } from "@/components/account/account-name";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { FilterFields } from "@/components/grid/filter-fields";
import type { PeriodRefusals } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { TextFilter } from "@/components/grid/text-filter";
import { type FilterValue, ValuesFilter } from "@/components/grid/values-filter";

import {
  ACTIONS,
  ACTOR_KIND,
  ACTOR_KINDS,
  AUDIT_ACTIONS,
  AUDIT_PAGE,
  type AuditFilters,
  CORRELATION,
  CORRELATION_PATTERN,
  FROM,
  OBJECT_KIND,
  OBJECT_KINDS,
  PROJECT,
  TO,
  USER,
} from "./audit-address";
import type { AuditNames, ProjectChoice } from "./audit-chips";

/** The longest correlation the contract takes. */
const CORRELATION_LENGTH = 64;

/** What the filters show: those the address asks, and what each offers to choose. */
export interface AuditFilterPanelProps extends AuditNames {
  readonly filters: AuditFilters;
  /** The sides of the period the API refused (422); none when it read the journal. */
  readonly refused?: PeriodRefusals | undefined;
}

/** Render the filters of the journal, as the address asks them. */
export function AuditFilterPanel({
  filters,
  users,
  projects,
  named,
  refused,
}: AuditFilterPanelProps) {
  const t = useTranslations();
  const naming = useAccountNaming();
  const ids = { user: useId(), project: useId(), kind: useId() };
  const actors: FilterValue<(typeof ACTOR_KINDS)[number]>[] = ACTOR_KINDS.map((kind) => ({
    value: kind,
    text: t(`enums.AuditActorKind.${kind}`),
  }));
  const chosenAuthor =
    named.account !== undefined
      ? naming.person(named.account)
      : named.user === undefined
        ? undefined
        : naming.kept(named.user);
  const authors = users.map((user) => ({ value: user.id, text: naming.kept(user.name) }));
  const projectName = ({ code, label }: Omit<ProjectChoice, "id">) =>
    code === null ? label : t("admin.auditLog.project", { code, label });
  const offered = projects.map((project) => ({ value: project.id, text: projectName(project) }));
  const kinds = OBJECT_KINDS.map((kind) => ({
    value: kind,
    text: t(`enums.AuditObjectKind.${kind}`),
  }));
  return (
    <FilterFields>
      <PeriodFilter
        label={t("admin.auditLog.filters.period")}
        kind="instant"
        period={{ from: filters.from, to: filters.to }}
        refused={refused}
        texts={{
          from: t("admin.auditLog.filters.from"),
          to: t("admin.auditLog.filters.to"),
        }}
        names={{ from: FROM, to: TO }}
        page={AUDIT_PAGE}
      />
      <ValuesFilter
        name={ACTOR_KIND}
        label={t("admin.auditLog.filters.actorKind")}
        every={t("admin.auditLog.filters.everyActor")}
        values={actors}
        chosen={filters.actorKinds}
        page={AUDIT_PAGE}
      />
      {/* Offered when there is an author to choose, or one to clear: none in a journal only the
      platform wrote. */}
      {authors.length === 0 && filters.user === undefined ? null : (
        <ChoiceFilter
          id={ids.user}
          name={USER}
          label={t("admin.auditLog.filters.user")}
          every={t("admin.auditLog.filters.everyUser")}
          choices={authors}
          chosen={filters.user}
          unknown={chosenAuthor}
          page={AUDIT_PAGE}
        />
      )}
      <ValuesFilter
        name={ACTIONS}
        label={t("admin.auditLog.filters.actions")}
        every={t("admin.auditLog.filters.everyAction")}
        values={AUDIT_ACTIONS.map((action) => ({
          value: action,
          text: t(`enums.AuditAction.${action}`),
        }))}
        chosen={filters.actions}
        page={AUDIT_PAGE}
        exhaustive={false}
      />
      <ChoiceFilter
        id={ids.project}
        name={PROJECT}
        label={t("admin.auditLog.filters.project")}
        every={t("admin.auditLog.filters.everyProject")}
        choices={offered}
        chosen={filters.project}
        unknown={named.project === undefined ? undefined : projectName(named.project)}
        page={AUDIT_PAGE}
      />
      <ChoiceFilter
        id={ids.kind}
        name={OBJECT_KIND}
        label={t("admin.auditLog.filters.objectKind")}
        every={t("admin.auditLog.filters.everyObjectKind")}
        choices={kinds}
        chosen={filters.objectKind}
        page={AUDIT_PAGE}
      />
      <TextFilter
        name={CORRELATION}
        label={t("admin.auditLog.filters.correlation")}
        value={filters.correlation}
        length={CORRELATION_LENGTH}
        page={AUDIT_PAGE}
        pattern={CORRELATION_PATTERN}
        form={t("admin.auditLog.filters.correlationForm")}
      />
    </FilterFields>
  );
}
