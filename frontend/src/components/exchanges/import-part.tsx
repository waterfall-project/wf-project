// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The first step of an import as a part of a screen, under its title: a command for each kind of
 * file the project offers to import (`ImportCommands`), or that none is offered. The screen of the
 * imports and exports shows it, and so does the screen of a project that has no revision yet, which
 * no address of a revision reaches: an import creates the revision it applies to (WF-INTF-0090,
 * #332). Whichever shows it, the import shown afterwards is the one the address names
 * (`readShownImport`).
 */
import { FileUp } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ICON } from "@/components/projects/project-tables";

import { ImportCommands } from "./import-commands";
import { EXCHANGE_KINDS, type ImportOffers } from "./offers";

/** A part of a screen under its title, named by it. */
export function Part({
  title,
  icon,
  children,
}: {
  readonly title: string;
  readonly icon: ReactNode;
  readonly children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

/** Render the imports offered, or that none is. */
export function ImportPart({
  projectId,
  offers,
  start,
}: {
  readonly projectId: string;
  readonly offers: ImportOffers;
  /** The address of the screen, its context kept, from which the report of an import is shown. */
  readonly start: string;
}) {
  const t = useTranslations("exchanges.import");
  const offered = EXCHANGE_KINDS.some((kind) => offers[kind] !== undefined);
  return (
    <Part title={t("title")} icon={<FileUp aria-hidden="true" className={ICON} />}>
      {offered ? (
        <ImportCommands projectId={projectId} offers={offers} start={start} />
      ) : (
        <p className="text-sm text-muted-foreground">{t("none")}</p>
      )}
    </Part>
  );
}
