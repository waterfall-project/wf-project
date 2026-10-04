// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the list of the projects of the portfolio that show more than a value formatted:
 * the label of a project, a link that opens it (WF-PTF-0030), out of the order of tabulation, the
 * grid being one stop, which follows it on Enter (`grid-keyboard.ts`); its state, by the catalogue;
 * an index, its value as the server gives it — or that it cannot be computed, and why — and its
 * zone by the one signal of the application (WF-IHM-0070); and the date of the last marked
 * revision, in the local time of the workstation.
 */
"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { Signal } from "@/components/signal/signal";
import { formatDecimal } from "@/i18n/format";

import type { ProjectState } from "./address";

/** An index and its zone, as the contract gives it. */
type IndexValue = components["schemas"]["IndexValue"];

/** Render the label of a project, as a link that opens it. */
export function ProjectLabelCell({ id, label }: { readonly id: string; readonly label: string }) {
  return (
    <Link
      href={`/projects/${id}`}
      tabIndex={-1}
      className="block truncate underline-offset-2 hover:underline"
    >
      {label}
    </Link>
  );
}

/** Render the state of a project, in the language of the interface. */
export function ProjectStateCell({ state }: { readonly state: ProjectState }) {
  const t = useTranslations("enums.ProjectState");
  return <span className="truncate">{t(state)}</span>;
}

/** Render an index: its value and its zone, or why it has none; nothing for a project without. */
export function IndexCell({ index }: { readonly index: IndexValue | null | undefined }) {
  const t = useTranslations();
  const locale = useLocale();
  if (index === null || index === undefined) {
    return null;
  }
  const { value, zone } = index;
  const computed = value.is_computable ? (value.value ?? null) : null;
  const reason = computed === null ? (value.reason ?? null) : null;
  return (
    <span className="inline-flex items-center gap-1.5 tabular-nums">
      {zone === null ? null : <Signal zone={zone} variant="icon" />}
      {computed === null ? (
        <span
          className="truncate text-muted-foreground"
          title={reason === null ? undefined : t(`enums.NotComputableReason.${reason}`)}
        >
          {t("indicator.notComputable")}
          {/* Its reason, read with the cell; the pointer finds it in the title too. */}
          {reason === null ? null : (
            <span className="sr-only">
              {t("portfolio.projects.reason", {
                reason: t(`enums.NotComputableReason.${reason}`),
              })}
            </span>
          )}
        </span>
      ) : (
        formatDecimal(computed, locale)
      )}
    </span>
  );
}

/** Render the moment of the last marked revision, or nothing when none is marked. */
export function MarkedCell({ at }: { readonly at: string | null }) {
  return at === null ? null : <LocalTime value={at} />;
}
