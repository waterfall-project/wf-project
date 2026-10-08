// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The natures and the categories of cost (FBS-3.1.1, US-0250), in dense tables, in the order the
 * server gave them: each nature by its code, its name and its type (WF-REF-0030); each category
 * by its code, its name, its nature and its accounting code (WF-REF-0040). A deactivated one,
 * which the lists show when the address asks for them, offers its reactivation to a session that
 * may modify the cost settings (WF-REF-0150); the forms that create and modify them belong to the
 * epic of the reference data.
 */
import { Layers, Tags } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";

import { listReads } from "./address";
import { Reactivations, StateCell } from "./reactivation";
import { ReferenceSection } from "./section";

type CostType = components["schemas"]["CostType"];
type CostCategory = components["schemas"]["CostCategory"];

/** The natures of cost, each by its code, its name, its type and its state. */
export function CostTypeList({
  types,
  reactivable,
}: {
  readonly types: readonly CostType[];
  /** Whether the session may modify the cost settings (`platformOffer`). */
  readonly reactivable: boolean;
}) {
  const t = useTranslations("reference.costTypes");
  const kind = useTranslations("enums.CostTypeKind");
  const columns = useTranslations("reference.columns");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Layers}
      empty={types.length === 0 ? t("none") : undefined}
    >
      <Reactivations reads={listReads()}>
        <ListTable
          label={t("title")}
          columns={[columns("code"), columns("label"), t("kind"), columns("state")]}
        >
          {types.map((type) => (
            <TableRow key={type.cost_type_id}>
              <TableCell className={CELL}>{type.code}</TableCell>
              <TableCell className={CELL}>{type.label}</TableCell>
              <TableCell className={CELL}>{kind(type.kind)}</TableCell>
              <TableCell className={CELL}>
                <StateCell
                  active={type.is_active}
                  target={{
                    kind: "cost_type",
                    id: type.cost_type_id,
                    lockVersion: type.lock_version,
                  }}
                  name={type.label}
                  reactivable={reactivable}
                />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      </Reactivations>
    </ReferenceSection>
  );
}

/**
 * The categories of cost, each by its code, its name, the nature it is attached to — named as the
 * server resolves it, active or not (WF-REF-0150) —, its accounting code, documentary, and its
 * state.
 */
export function CostCategoryList({
  categories,
  reactivable,
}: {
  readonly categories: readonly CostCategory[];
  /** Whether the session may modify the cost settings (`platformOffer`). */
  readonly reactivable: boolean;
}) {
  const t = useTranslations("reference.costCategories");
  const columns = useTranslations("reference.columns");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Tags}
      empty={categories.length === 0 ? t("none") : undefined}
    >
      <Reactivations reads={listReads()}>
        <ListTable
          label={t("title")}
          columns={[
            columns("code"),
            columns("label"),
            t("costType"),
            t("accountingCode"),
            columns("state"),
          ]}
        >
          {categories.map((category) => (
            <TableRow key={category.cost_category_id}>
              <TableCell className={CELL}>{category.code}</TableCell>
              <TableCell className={CELL}>{category.label}</TableCell>
              <TableCell className={CELL}>{category.cost_type_label}</TableCell>
              <TableCell className={CELL}>{category.accounting_code}</TableCell>
              <TableCell className={CELL}>
                <StateCell
                  active={category.is_active}
                  target={{
                    kind: "cost_category",
                    id: category.cost_category_id,
                    lockVersion: category.lock_version,
                  }}
                  name={category.label}
                  reactivable={reactivable}
                />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      </Reactivations>
    </ReferenceSection>
  );
}
