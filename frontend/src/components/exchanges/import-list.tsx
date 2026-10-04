// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The imports of the project, in progress and past, as `listImports` gives them (WF-INTF-0080,
 * WF-ARC-0100): of each, its file — a link to its report —, its kind, the status where it stopped
 * and when it was opened, in the local time of the workstation; in the order received. The list
 * says when it shows only the first of its imports, and that it is empty when no import was ever
 * opened. A section named by its label, as a server component has no identifier to give.
 */
import { History } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";

import { importHref } from "./offers";

type Import = components["schemas"]["Import"];

/** The imports of a page of the list, how many the project holds, and the one shown. */
export interface ImportListProps {
  readonly imports: readonly Import[];
  readonly total: number;
  /** The import whose report the screen shows, if any. */
  readonly current: string | undefined;
  /** The address of the screen, its context kept. */
  readonly start: string;
}

/** Render the imports of the project, each leading to its report. */
export function ImportList({ imports, total, current, start }: ImportListProps) {
  const t = useTranslations();
  const title = t("exchanges.list.title");
  return (
    <section aria-label={title} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <History aria-hidden="true" className={ICON} />
        {title}
      </h2>
      {total === 0 ? (
        <p className="text-sm text-muted-foreground">{t("exchanges.list.none")}</p>
      ) : (
        <ListTable
          label={title}
          columns={[
            t("exchanges.list.file"),
            t("exchanges.list.kind"),
            t("exchanges.list.status"),
            t("exchanges.list.openedAt"),
          ]}
        >
          {imports.map((entry) => (
            <TableRow key={entry.import_id}>
              <TableCell className={CELL}>
                <Link
                  href={importHref(start, entry.import_id)}
                  aria-current={entry.import_id === current ? "page" : undefined}
                  className="font-medium underline-offset-4 hover:underline aria-[current=page]:underline"
                >
                  {entry.filename}
                </Link>
              </TableCell>
              <TableCell className={CELL}>{t(`enums.ExchangeKind.${entry.kind}`)}</TableCell>
              <TableCell className={CELL}>{t(`enums.Import.status.${entry.status}`)}</TableCell>
              <TableCell className={CELL}>
                <LocalTime value={entry.created_at} />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
      {imports.length < total ? (
        <p className="text-sm text-muted-foreground">
          {t("exchanges.list.partial", { shown: imports.length, total })}
        </p>
      ) : null}
    </section>
  );
}
