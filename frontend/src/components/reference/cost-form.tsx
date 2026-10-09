// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that creates or modifies a nature (WF-REF-0030) or a category of cost (WF-REF-0040), in a
 * dialog over its list (EP-02/L43a, `ReferenceForm`): a nature by its code, its name and its type,
 * offered among the three of the contract — its modification says that the type no longer changes
 * once a category attached to it is employed, as the contract does (`CostTypeKind`,
 * `updateCostType`); a category by its code, its name, its nature — chosen among the active ones, a
 * deactivated one being no longer offered to an entry (WF-REF-0010), save the one the category is
 * attached to, marked deactivated — and its accounting code, which may stay empty, sent as none. A
 * category without a nature is refused before anything is asked (WF-REF-0040).
 */
"use client";

import { useTranslations } from "next-intl";

import { createReferenceObject, updateReferenceObject } from "@/api/actions/reference";

import { useListForm } from "./commands";
import {
  COST_TYPE_KIND_VALUES,
  type CostCategory,
  type CostType,
  isCostTypeKind,
} from "./cost-kinds";
import { type Choice, offered } from "./kinds";
import { CODE_LENGTH, type Draft, LABEL_LENGTH, ReferenceForm, required } from "./reference-form";

/** What a nature or a category starts from: the object modified, or nothing typed. */
function draftOf(row: CostType | CostCategory | undefined): Draft {
  if (row === undefined) {
    return {};
  }
  return "cost_category_id" in row
    ? {
        code: row.code,
        label: row.label,
        cost_type_id: row.cost_type_id,
        accounting_code: row.accounting_code ?? "",
      }
    : { code: row.code, label: row.label, kind: row.kind };
}

/** The body a nature is written by, from the values checked. */
function natureOf({ code = "", label = "", kind = "" }: Draft) {
  if (!isCostTypeKind(kind)) {
    // The type is chosen among those of the contract, and required before anything is asked.
    throw new Error("a nature is written with a type of the contract");
  }
  return { code, label, kind };
}

/** The body a category is written by, from the values checked: an empty accounting code none. */
function categoryOf({ code = "", label = "", cost_type_id = "", accounting_code = "" }: Draft) {
  return {
    code,
    label,
    cost_type_id,
    accounting_code: accounting_code === "" ? null : accounting_code,
  };
}

/** The dialog of the list of the natures or of the categories, while its form is open. */
export function CostDialog({
  natures,
}: {
  /** The natures a category may be attached to, in the order of the server; none for the natures. */
  readonly natures: readonly Choice[];
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const kinds = useTranslations("enums.CostTypeKind");
  const form = useListForm();
  if (form === undefined) {
    return null;
  }
  const { row, ...rest } = form;
  const { kind } = form;
  const shared = {
    ...rest,
    title:
      row === undefined
        ? t(kind === "cost_type" ? "costForm.createCostType" : "costForm.createCostCategory")
        : t("modifyNamed", { name: row.label }),
    creating: row === undefined,
  };
  const common = [
    required("code", columns("code"), CODE_LENGTH),
    required("label", columns("label"), LABEL_LENGTH),
  ];
  if (kind === "cost_type") {
    const nature = row as CostType | undefined;
    return (
      <ReferenceForm
        {...shared}
        hint={t(nature === undefined ? "costForm.costTypeHint" : "costForm.costTypeModifyHint")}
        fields={[
          ...common,
          {
            name: "kind",
            label: columns("costTypeKind"),
            control: "choice",
            required: true,
            choices: COST_TYPE_KIND_VALUES.map((value) => [value, kinds(value)] as const),
          },
        ]}
        initial={draftOf(nature)}
        ask={(values) =>
          nature === undefined
            ? createReferenceObject({ kind, body: natureOf(values) })
            : updateReferenceObject(nature.cost_type_id, {
                kind,
                body: { ...natureOf(values), lock_version: nature.lock_version },
              })
        }
      />
    );
  }
  const category = row as CostCategory | undefined;
  const attached =
    category === undefined
      ? undefined
      : { id: category.cost_type_id, label: category.cost_type_label };
  return (
    <ReferenceForm
      {...shared}
      hint={t("costForm.costCategoryHint")}
      fields={[
        ...common,
        {
          name: "cost_type_id",
          label: columns("costType"),
          control: "choice",
          required: true,
          choices: offered(natures, attached).map((nature) => {
            const named = t("codedChoice", { code: nature.code ?? "", label: nature.label });
            const shown = nature.deactivated
              ? t("form.deactivatedChoice", { choice: named, kind: "cost_type" })
              : named;
            return [nature.id, shown] as const;
          }),
        },
        { name: "accounting_code", label: columns("accountingCode"), control: "text" },
      ]}
      initial={draftOf(category)}
      ask={(values) =>
        category === undefined
          ? createReferenceObject({ kind: "cost_category", body: categoryOf(values) })
          : updateReferenceObject(category.cost_category_id, {
              kind: "cost_category",
              body: { ...categoryOf(values), lock_version: category.lock_version },
            })
      }
    />
  );
}
