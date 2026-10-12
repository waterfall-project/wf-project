// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the journal of audit that show more than a value formatted (WF-SEC-0030): the
 * author, an account by the name the inscription keeps — that of the moment of the action, kept
 * after the account is deactivated, and the neutral label once it is anonymised (WF-ADM-0060) — or
 * the platform; the action and the nature of the object, in words; the object and the project, by
 * the names the inscription keeps — an account anonymised by the neutral label —, each a link to it
 * when the session may consult it (WF-ADM-0110), its name alone otherwise; the link to the
 * history of the object, the journal filtered on it; what the action did to its object, composed in
 * the language of the reader from the codes and the identifiers the inscription keeps, never a
 * sentence of the API (WF-ARC-0110); and the correlation, a link to the inscriptions
 * of its request alone (WF-OBS-0020). A link is out of the order of tabulation,
 * the grid being one stop, which follows it on Enter (`grid-keyboard.ts`).
 */
"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { useAccountNaming } from "@/components/account/account-name";
import { AnonymizedName, KeptName } from "@/components/account/anonymized-name";
import { usePendingLink } from "@/components/grid/pending-address";
import { formatLocale } from "@/i18n/format";

import {
  type AuditAction,
  type AuditObjectKind,
  correlationHref,
  historyHref,
} from "./audit-address";

type AuditEvent = components["schemas"]["AuditEvent"];

/** How a link of a cell shows: the whole cell, its text cut short. */
const LINK = "block truncate underline-offset-2 hover:underline";

/**
 * The name of the object of an inscription: the label it bore at the moment of the action; for an
 * account anonymised since, the neutral label; for a backup, which has none, its nature.
 */
export function useObjectName(): (object: Pick<AuditEvent["object"], "label" | "kind">) => string {
  const t = useTranslations("enums.AuditObjectKind");
  const naming = useAccountNaming();
  return ({ label, kind }) => label ?? (kind === "user" ? naming.kept(null) : t(kind));
}

/**
 * Render the author of an inscription: the name of the account — the neutral label for an account
 * anonymised —, or the platform.
 */
export function ActorCell({ actor }: { readonly actor: AuditEvent["actor"] }) {
  const t = useTranslations("enums.AuditActorKind");
  return actor.kind === "user" && actor.display_name !== undefined ? (
    <KeptName name={actor.display_name} />
  ) : (
    <span className="text-muted-foreground">{t(actor.kind)}</span>
  );
}

/** Render the action of an inscription, in words. */
export function ActionCell({ action }: { readonly action: AuditAction }) {
  const t = useTranslations("enums.AuditAction");
  return t(action);
}

/** The parameters of an inscription, as the contract gives them: codes, identifiers, labels kept. */
type AuditParams = AuditEvent["params"];
type PermissionCode = components["schemas"]["PermissionCode"];
type AuditAccessRole = components["schemas"]["AuditAccessRole"];

/**
 * What an action did to its object, in sentences of the language of the reader, composed from the
 * parameters the inscription keeps (WF-ARC-0110, #706) — the origin of an account created; the
 * fields of the identity a modification changed, and its attachment to the directory; the
 * permissions of a role created, those a modification granted and withdrew, and the label it bore
 * before; the roles an attribution granted and withdrew, by the labels they bore then
 * (WF-ADM-0090). The labels of the roles are shown as they were entered, never translated. None for
 * an action whose object says it all.
 */
export function useAuditDetails(): (
  action: AuditAction,
  params: AuditParams,
) => string | undefined {
  const t = useTranslations();
  const said = useTranslations("admin.auditLog.details");
  const list = new Intl.ListFormat(formatLocale(useLocale()), { type: "conjunction" });
  const listed = (items: readonly string[]) => list.format(items);
  const permissions = (codes: readonly PermissionCode[]) =>
    listed(codes.map((code) => t(`permissions.${code}`)));
  const roles = (held: readonly AuditAccessRole[]) => listed(held.map((role) => role.label));
  // An account: its origin, the fields of its identity changed, its attachment to the directory.
  const account = ({ origin, fields = [], attached }: AuditParams): (string | false)[] => [
    origin !== undefined && t(`enums.UserOrigin.${origin}`),
    fields.length > 0 &&
      said("fields", {
        count: fields.length,
        fields: listed(fields.map((field) => t(`enums.AuditUserField.${field}`))),
      }),
    attached === true && said("attached"),
  ];
  // A role: the label it bore before, its permissions, those granted and withdrawn.
  const role = (params: AuditParams): (string | false)[] => [
    params.previous_label !== undefined && said("renamed", { label: params.previous_label }),
    params.permissions !== undefined &&
      said("permissions", {
        count: params.permissions.length,
        permissions: permissions(params.permissions),
      }),
    ...(
      [
        ["permissionsGranted", params.permissions_granted ?? []],
        ["permissionsWithdrawn", params.permissions_withdrawn ?? []],
      ] as const
    ).map(
      ([key, codes]) =>
        codes.length > 0 && said(key, { count: codes.length, permissions: permissions(codes) }),
    ),
  ];
  // An attribution: the roles granted and withdrawn, or that it changed none.
  const attribution = (action: AuditAction, params: AuditParams): (string | false)[] => {
    const granted = params.access_roles_granted ?? [];
    const withdrawn = params.access_roles_withdrawn ?? [];
    return [
      granted.length > 0 && said("rolesGranted", { count: granted.length, roles: roles(granted) }),
      withdrawn.length > 0 &&
        said("rolesWithdrawn", { count: withdrawn.length, roles: roles(withdrawn) }),
      action === "user_access_roles_set" &&
        granted.length === 0 &&
        withdrawn.length === 0 &&
        said("noRoleChanged"),
    ];
  };
  return (action, params) => {
    const parts = [...account(params), ...role(params), ...attribution(action, params)].filter(
      (part) => part !== false,
    );
    return parts.length === 0
      ? undefined
      : parts.reduce((first, second) => said("then", { first, second }));
  };
}

/**
 * Render what the action of an inscription did to its object, in the language of the reader; its
 * whole sentence on hover, the cell cutting it short. Nothing for an action whose object says it
 * all.
 */
export function DetailsCell({ event }: { readonly event: AuditEvent }) {
  const details = useAuditDetails()(event.action, event.params);
  return details === undefined ? null : (
    <span title={details} className="block truncate">
      {details}
    </span>
  );
}

/** Render the nature of the object of an inscription, in words. */
export function ObjectKindCell({ kind }: { readonly kind: AuditObjectKind }) {
  const t = useTranslations("enums.AuditObjectKind");
  return t(kind);
}

/**
 * Render the object of an inscription by the label it bore at the moment of the action — an account
 * anonymised since by the neutral label; a backup, which has none, by its nature, never by its
 * identifier —, a link to it when the session may consult it.
 */
export function ObjectCell({
  object,
  href,
}: {
  readonly object: AuditEvent["object"];
  readonly href: string | undefined;
}) {
  const name = useObjectName()(object);
  const label = object.label;
  if (label === null) {
    return object.kind === "user" ? (
      <AnonymizedName />
    ) : (
      <span className="text-muted-foreground">{name}</span>
    );
  }
  return href === undefined ? (
    label
  ) : (
    <Link href={href} tabIndex={-1} className={LINK}>
      {label}
    </Link>
  );
}

/**
 * Render the project of an inscription by its code and its label at the moment of the action, a
 * link to it when the session may open it; or that the object belongs to no project.
 */
export function ProjectCell({
  project,
  href,
}: {
  readonly project: AuditEvent["project"];
  readonly href: string | undefined;
}) {
  const t = useTranslations("admin.auditLog");
  if (project === null) {
    return <span className="text-muted-foreground">{t("noProject")}</span>;
  }
  const name = t("project", { code: project.code, label: project.label });
  return href === undefined ? (
    name
  ) : (
    <Link href={href} tabIndex={-1} className={LINK}>
      {name}
    </Link>
  );
}

/**
 * Render the link to the history of the object of an inscription: the journal filtered on its
 * nature and its identifier, its whole history — every other filter lifted —, back to the first
 * page, the sort kept — from the address last asked (`usePendingLink`).
 */
export function HistoryCell({ object }: { readonly object: AuditEvent["object"] }) {
  const t = useTranslations();
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) => historyHref(pathname, query, object));
  const name = useObjectName()(object);
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      tabIndex={-1}
      aria-label={t("admin.auditLog.history", { object: name })}
      className="flex items-center justify-center text-muted-foreground hover:text-foreground"
    >
      <History aria-hidden="true" className="size-4" />
    </Link>
  );
}

/**
 * Render the correlation of an inscription, a link to the inscriptions of its request alone — those
 * of the background task it set off too —, the sort kept, from the address last asked.
 */
export function CorrelationCell({ correlation }: { readonly correlation: string }) {
  const t = useTranslations("admin.auditLog");
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    correlationHref(pathname, query, correlation),
  );
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      tabIndex={-1}
      aria-label={t("correlated", { correlation })}
      className={LINK}
    >
      {correlation}
    </Link>
  );
}
