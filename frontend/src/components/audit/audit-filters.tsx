// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the journal of audit (FBS-1.5, WF-SEC-0030): by period, by author — an account,
 * or whether an account or the platform acted —, by action, by project and by object, its nature
 * and the one object whose history the address asks. A filter chosen only changes the address,
 * under the names of the contract (`audit-address.ts`), back to the first page; the page reads anew
 * the inscriptions the server retains. The front filters nothing. A change goes on from the address
 * last asked (`usePendingAddress`): a filter chosen right after a sort or another filter keeps it.
 *
 * The period is two instants, entered in the local time of the workstation and sent as the
 * contract takes them, in universal time: only the browser knows its time zone, so the fields show
 * the instants of the address once the page is hydrated, and the period is applied from then on.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ChevronDown, ListFilter, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState } from "react";

import { readValues, valuesHref } from "@/components/grid/filters";
import { usePendingAddress, usePendingLink } from "@/components/grid/pending-address";
import { type FilterValue, ValuesFilter } from "@/components/grid/values-filter";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useHydrated } from "@/components/use-hydrated";

import {
  ACTIONS,
  ACTOR_KIND,
  ACTOR_KINDS,
  AUDIT_ACTIONS,
  AUDIT_PAGE,
  type AuditAction,
  type AuditFilters,
  auditHref,
  FROM,
  OBJECT,
  OBJECT_KIND,
  OBJECT_KINDS,
  PROJECT,
  TO,
  USER,
} from "./audit-address";

/** An object a filter may choose, by its identifier and the text that names it. */
interface Choice {
  readonly value: string;
  readonly text: string;
}

/** An account that may be an author, by its identifier and its names. */
export interface AuthorChoice {
  readonly id: string;
  readonly firstName: string;
  readonly lastName: string;
}

/** A project, by its identifier, its code — if it has one — and its label. */
export interface ProjectChoice {
  readonly id: string;
  readonly code: string | null | undefined;
  readonly label: string;
}

/** Change filters of the journal, from the address last asked. */
function useAuditFilter() {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  return (changes: Readonly<Record<string, string | undefined>>) => {
    request((query) => auditHref(pathname, query, changes));
  };
}

/** Two digits. */
function twoDigits(value: number): string {
  return String(value).padStart(2, "0");
}

/** An instant of the contract as a field of local date and time writes it: `2026-06-03T10:30`. */
function localField(instant: string): string {
  const at = new Date(instant);
  const date = `${String(at.getFullYear())}-${twoDigits(at.getMonth() + 1)}-${twoDigits(at.getDate())}`;
  return `${date}T${twoDigits(at.getHours())}:${twoDigits(at.getMinutes())}`;
}

/** A local date and time entered, as the contract takes an instant; none for a field emptied. */
function instantOfField(field: string): string | undefined {
  const at = new Date(field);
  return field === "" || Number.isNaN(at.getTime()) ? undefined : at.toISOString();
}

/** What the user entered in the fields of the period, and over which period of the address. */
interface Entered {
  /** The period of the address the entry was made over: another, and the entry is forgotten. */
  readonly over: string;
  readonly from?: string;
  readonly to?: string;
}

/**
 * The filter by period: from an instant, included, to another, excluded, as the contract reads them;
 * sent together. Each field keeps the other side of the period: a start after the end is not offered.
 * A bound left untouched leaves as the address names it, never through its field, which shows it to
 * the minute; an entry is dated by the period of the address it was made over, so that a period the
 * address changes — back in the history — shows anew, and the form, never remounted, keeps the focus.
 */
function PeriodFilter({ from, to }: Pick<AuditFilters, "from" | "to">) {
  const t = useTranslations("admin.auditLog.filters");
  const ids = { from: useId(), to: useId() };
  const hydrated = useHydrated();
  const over = `${from ?? ""}/${to ?? ""}`;
  const [entered, setEntered] = useState<Entered>({ over });
  const filter = useAuditFilter();
  const current: Entered = entered.over === over ? entered : { over };
  const asked = { from, to };
  const shown = (bound: "from" | "to") => {
    const instant = asked[bound];
    return current[bound] ?? (hydrated && instant !== undefined ? localField(instant) : "");
  };
  const period = { from: shown("from"), to: shown("to") };
  /** What a bound sends: its entry, as an instant; untouched, the instant of the address. */
  const sent = (bound: "from" | "to") => {
    const entry = current[bound];
    return entry === undefined ? asked[bound] : instantOfField(entry);
  };
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    filter({ [FROM]: sent("from"), [TO]: sent("to") });
  };
  return (
    <form aria-label={t("period")} onSubmit={submit} className="flex flex-wrap items-center gap-2">
      {(["from", "to"] as const).map((bound) => (
        <div key={bound} className="flex items-center gap-2">
          <Label htmlFor={ids[bound]}>{t(bound)}</Label>
          <Input
            id={ids[bound]}
            type="datetime-local"
            value={period[bound]}
            {...(bound === "from"
              ? { max: period.to === "" ? undefined : period.to }
              : { min: period.from === "" ? undefined : period.from })}
            onChange={(event) => {
              setEntered({ ...current, [bound]: event.target.value });
            }}
            className="h-8 w-52"
          />
        </div>
      ))}
      {/* Sent by React alone: before the hydration, the browser would send the form itself. */}
      <Button type="submit" size="sm" variant="outline" disabled={!hydrated}>
        <ListFilter aria-hidden="true" className="size-4" />
        {t("apply")}
      </Button>
    </form>
  );
}

/**
 * The filter on one object of a column — the author, the project, the nature of the object —,
 * chosen among those offered; one the address names that is not offered stays chosen under the name
 * given, to be cleared.
 */
function ChoiceFilter({
  id,
  name,
  label,
  every,
  choices,
  chosen,
  unknown,
}: {
  /** The identifier of its list, which the focus is given back to. */
  readonly id: string;
  /** The parameter of the address the filter writes, as the contract names it. */
  readonly name: string;
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  readonly choices: readonly Choice[];
  readonly chosen: string | undefined;
  /** The name of the object chosen when it is not offered. */
  readonly unknown: string | undefined;
}) {
  const filter = useAuditFilter();
  const offered = chosen === undefined || choices.some((choice) => choice.value === chosen);
  return (
    <div className="flex items-center gap-2 text-sm">
      <Label htmlFor={id} className="whitespace-nowrap">
        {label}
      </Label>
      <div className="w-56 shrink-0">
        <NativeSelect
          id={id}
          value={chosen ?? ""}
          onChange={(event) => {
            filter({ [name]: event.target.value });
          }}
        >
          <option value="">{every}</option>
          {choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.text}
            </option>
          ))}
          {offered ? null : <option value={chosen}>{unknown ?? chosen}</option>}
        </NativeSelect>
      </div>
    </div>
  );
}

/**
 * The filter by action: a menu of the actions of the contract, in its order, each checked when the
 * address filters on it, and one that lifts the filter; the menu stays open while actions are
 * checked.
 */
function ActionsFilter({ chosen }: { readonly chosen: readonly AuditAction[] }) {
  const t = useTranslations();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const filter = { name: ACTIONS, values: AUDIT_ACTIONS, page: AUDIT_PAGE };
  /** Filter on the actions a change makes of those last asked. */
  const change = (make: (asked: readonly AuditAction[]) => readonly AuditAction[]) => {
    request((query) =>
      valuesHref(pathname, query, filter, make(readValues(query, ACTIONS, AUDIT_ACTIONS))),
    );
  };
  const shown =
    chosen.length === 0
      ? t("admin.auditLog.filters.everyAction")
      : t("admin.auditLog.filters.actionsChosen", { count: chosen.length });
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="sm"
          variant={chosen.length === 0 ? "outline" : "default"}
          aria-label={t("admin.auditLog.filters.actionsNamed", { chosen: shown })}
        >
          <ListFilter aria-hidden="true" className="size-4" />
          {shown}
          <ChevronDown aria-hidden="true" className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-96 overflow-y-auto">
        <DropdownMenuItem
          onSelect={() => {
            change(() => []);
          }}
        >
          {t("admin.auditLog.filters.everyAction")}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {AUDIT_ACTIONS.map((action) => (
          <DropdownMenuCheckboxItem
            key={action}
            checked={chosen.includes(action)}
            onCheckedChange={() => {
              change((asked) =>
                asked.includes(action)
                  ? asked.filter((each) => each !== action)
                  : [...asked, action],
              );
            }}
            onSelect={(event) => {
              event.preventDefault();
            }}
          >
            {t(`enums.AuditAction.${action}`)}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * The object whose history the address asks, by its name, and the link that lifts it: the journal
 * of every object of its nature, or of every nature. The link gone with the object, the focus goes
 * to the filter of the nature, which stays (`returnTo`) — when the page follows it, not when the
 * browser opens it in a tab.
 */
function ObjectShown({ name, returnTo }: { readonly name: string; readonly returnTo: string }) {
  const t = useTranslations("admin.auditLog.filters");
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    auditHref(pathname, query, { [OBJECT]: undefined }),
  );
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      {t("object", { object: name })}
      <Link
        href={href}
        onClick={(event) => {
          onClick(event);
          // Followed in the page only: a tab the browser opens — Ctrl, Cmd, Shift — leaves it.
          if (event.defaultPrevented) {
            document.getElementById(returnTo)?.focus();
          }
        }}
        scroll={false}
        aria-label={t("liftObject", { object: name })}
        className={buttonVariants({ variant: "outline", size: "sm" })}
      >
        <X aria-hidden="true" className="size-4" />
        {t("lift")}
      </Link>
    </span>
  );
}

/** What the filters show: those the address asks, and what each offers to choose. */
export interface AuditFilterBarProps {
  readonly filters: AuditFilters;
  /** The accounts that may be authors, by their names; none when the session may not read them. */
  readonly users: readonly AuthorChoice[];
  /** The projects the session may open, by their codes and labels. */
  readonly projects: readonly ProjectChoice[];
  /**
   * The names the inscriptions shown give what the address names and no choice offers: the author,
   * the project, the object whose history is asked.
   */
  readonly named: {
    readonly user: string | undefined;
    readonly project: Omit<ProjectChoice, "id"> | undefined;
    /** The object, by its label — none for a backup, named by its nature. */
    readonly object:
      { readonly label: string | null; readonly kind: (typeof OBJECT_KINDS)[number] } | undefined;
  };
}

/** Render the filters of the journal, as the address asks them. */
export function AuditFilterBar({ filters, users, projects, named }: AuditFilterBarProps) {
  const t = useTranslations();
  const ids = { user: useId(), project: useId(), kind: useId() };
  const actors: FilterValue<(typeof ACTOR_KINDS)[number]>[] = ACTOR_KINDS.map((kind) => ({
    value: kind,
    text: t(`enums.AuditActorKind.${kind}`),
  }));
  const authors = users.map((user) => ({
    value: user.id,
    text: t("admin.users.named", { firstName: user.firstName, lastName: user.lastName }),
  }));
  const projectName = ({ code, label }: Omit<ProjectChoice, "id">) =>
    code === null || code === undefined ? label : t("admin.auditLog.project", { code, label });
  const offered = projects.map((project) => ({ value: project.id, text: projectName(project) }));
  const kinds = OBJECT_KINDS.map((kind) => ({
    value: kind,
    text: t(`enums.AuditObjectKind.${kind}`),
  }));
  return (
    <section
      aria-label={t("admin.auditLog.filters.label")}
      className="flex flex-wrap items-center gap-x-6 gap-y-2"
    >
      <PeriodFilter from={filters.from} to={filters.to} />
      <ValuesFilter
        name={ACTOR_KIND}
        label={t("admin.auditLog.filters.actorKind")}
        every={t("admin.auditLog.filters.everyActor")}
        values={actors}
        chosen={filters.actorKinds}
        page={AUDIT_PAGE}
      />
      {/* Offered when there is an author to choose, or one to clear: none to a session that may
      not read the accounts. */}
      {authors.length === 0 && filters.user === undefined ? null : (
        <ChoiceFilter
          id={ids.user}
          name={USER}
          label={t("admin.auditLog.filters.user")}
          every={t("admin.auditLog.filters.everyUser")}
          choices={authors}
          chosen={filters.user}
          unknown={named.user}
        />
      )}
      <ActionsFilter chosen={filters.actions} />
      <ChoiceFilter
        id={ids.project}
        name={PROJECT}
        label={t("admin.auditLog.filters.project")}
        every={t("admin.auditLog.filters.everyProject")}
        choices={offered}
        chosen={filters.project}
        unknown={named.project === undefined ? undefined : projectName(named.project)}
      />
      <ChoiceFilter
        id={ids.kind}
        name={OBJECT_KIND}
        label={t("admin.auditLog.filters.objectKind")}
        every={t("admin.auditLog.filters.everyObjectKind")}
        choices={kinds}
        chosen={filters.objectKind}
        unknown={undefined}
      />
      {filters.object === undefined ? null : (
        <ObjectShown
          name={
            named.object === undefined
              ? filters.object
              : (named.object.label ?? t(`enums.AuditObjectKind.${named.object.kind}`))
          }
          returnTo={ids.kind}
        />
      )}
    </section>
  );
}
