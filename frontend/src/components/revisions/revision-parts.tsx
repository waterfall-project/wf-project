// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the revisions shows of the revision it reads in (FBS-4.1, US-0210): its
 * cost structures, in the order of the server — the main one, the amendments, each said merged
 * when the API says so, and the estimate of each risk —, each by its nature and its label
 * (WF-REV-0100); and, for the current revision, the rate update the API proposes, category by
 * category, each with its previous rate, the proposed one and where the latter comes from — the
 * rate of the reference, or the previous rate projected by inflation (WF-REV-0060).
 *
 * Every figure is the API's, formatted from its exact string. Nothing is offered to create,
 * merge or apply: those commands belong to the forms of their domain. A name the API leaves out
 * is said missing, never replaced by an identifier.
 */
import { BadgeCheck, Coins, FileDiff, Layers, type LucideIcon, ShieldAlert } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { CELL, ICON, ListSection, ListTable } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/i18n/format";

/** A cost structure of a revision. */
export type CostStructure = components["schemas"]["CostStructure"];

/** The rate update the API proposes for a revision. */
export type RateUpdateProposal = components["schemas"]["RateUpdateProposal"];

/** The icon of each nature of structure. */
const STRUCTURE_ICONS: Readonly<Record<CostStructure["kind"], LucideIcon>> = {
  main: Layers,
  amendment: FileDiff,
  risk: ShieldAlert,
};

const AMOUNT = `${CELL} tabular-nums`;

/** Render the cost structures of a revision, each by its nature and its label. */
export function CostStructureList({
  structures,
}: {
  readonly structures: readonly CostStructure[];
}) {
  const t = useTranslations("revisionScreen.structures");
  const kind = useTranslations("enums.StructureKind");
  return (
    <ListSection
      title={t("title")}
      icon={Layers}
      empty={structures.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[t("kind"), t("label"), t("state")]}>
        {structures.map((structure) => {
          const Icon = STRUCTURE_ICONS[structure.kind];
          return (
            <TableRow key={structure.structure_id}>
              <TableCell className={CELL}>
                <span className="inline-flex items-center gap-1.5">
                  <Icon aria-hidden="true" className={ICON} />
                  {kind(structure.kind)}
                </span>
              </TableCell>
              <TableCell className={CELL}>{structure.label}</TableCell>
              <TableCell className={CELL}>
                {structure.is_merged ? (
                  <Badge variant="outline">
                    <BadgeCheck aria-hidden="true" />
                    {t("merged")}
                  </Badge>
                ) : null}
              </TableCell>
            </TableRow>
          );
        })}
      </ListTable>
    </ListSection>
  );
}

/**
 * Render the rate update the API proposes for the current revision, category by category, or
 * that the reference has not changed and none is proposed.
 */
export function RateUpdate({ proposal }: { readonly proposal: RateUpdateProposal }) {
  const t = useTranslations("revisionScreen.rateUpdate");
  const source = useTranslations("enums.RateUpdateProposal.categories.source");
  const locale = useLocale();
  const { categories } = proposal;
  return (
    <ListSection
      title={t("title")}
      icon={Coins}
      empty={categories.length === 0 ? t("none") : undefined}
    >
      <div className="space-y-1 text-sm text-muted-foreground">
        {proposal.target_year === undefined ? null : (
          <p>{t("year", { year: proposal.target_year.toString() })}</p>
        )}
        <p>{t("notImposed")}</p>
      </div>
      <ListTable
        label={t("title")}
        columns={[t("category"), t("previous"), t("proposed"), t("source")]}
      >
        {categories.map((category) => (
          <TableRow key={category.cost_category_id}>
            <TableCell className={CELL}>{t("unnamed")}</TableCell>
            <TableCell className={AMOUNT}>
              {formatMoney(category.previous_amount, locale)}
            </TableCell>
            <TableCell className={AMOUNT}>
              {formatMoney(category.proposed_amount, locale)}
            </TableCell>
            <TableCell className={CELL}>{source(category.source)}</TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ListSection>
  );
}
