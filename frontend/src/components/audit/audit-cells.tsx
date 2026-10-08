// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the journal of audit that show more than a value formatted (WF-SEC-0030): the
 * author, an account by the name the inscription keeps — that of the moment of the action, kept
 * after the account is deactivated (WF-ADM-0060) — or the platform; the action and the nature of
 * the object, in words; the object and the project, by the names the inscription keeps, each a link
 * to it when the session may consult it (WF-ADM-0110), its name alone otherwise; and the link to
 * the history of the object, the journal filtered on it. A link is out of the order of tabulation,
 * the grid being one stop, which follows it on Enter (`grid-keyboard.ts`).
 */
"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { usePendingLink } from "@/components/grid/pending-address";

import { type AuditAction, type AuditObjectKind, historyHref } from "./audit-address";

type AuditEvent = components["schemas"]["AuditEvent"];

/** How a link of a cell shows: the whole cell, its text cut short. */
const LINK = "block truncate underline-offset-2 hover:underline";

/** Render the author of an inscription: the name of the account, or the platform. */
export function ActorCell({ actor }: { readonly actor: AuditEvent["actor"] }) {
  const t = useTranslations("enums.AuditActorKind");
  return actor.kind === "user" && actor.display_name !== undefined ? (
    actor.display_name
  ) : (
    <span className="text-muted-foreground">{t(actor.kind)}</span>
  );
}

/** Render the action of an inscription, in words. */
export function ActionCell({ action }: { readonly action: AuditAction }) {
  const t = useTranslations("enums.AuditAction");
  return t(action);
}

/** Render the nature of the object of an inscription, in words. */
export function ObjectKindCell({ kind }: { readonly kind: AuditObjectKind }) {
  const t = useTranslations("enums.AuditObjectKind");
  return t(kind);
}

/**
 * Render the object of an inscription by the label it bore at the moment of the action — or, for
 * one that has none, a backup, by its nature, never by its identifier —, a link to it when the
 * session may consult it.
 */
export function ObjectCell({
  object,
  href,
}: {
  readonly object: AuditEvent["object"];
  readonly href: string | undefined;
}) {
  const t = useTranslations("enums.AuditObjectKind");
  const label = object.label;
  if (label === null) {
    return <span className="text-muted-foreground">{t(object.kind)}</span>;
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
  const name = object.label ?? t(`enums.AuditObjectKind.${object.kind}`);
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
