// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that creates or modifies a nature (WF-REF-0030) or a category of cost (WF-REF-0040), in a
 * dialog over its list (EP-02/L43a, `ReferenceForm`): a nature by its code, its name and its type,
 * offered among the three of the contract; a category by its code, its name, its nature — chosen among
 * the active ones, a deactivated one being no longer offered to an entry (WF-REF-0010), save the one
 * the category is attached to, marked deactivated — and its accounting code, required and unique
 * (WF-REF-0040, decision of the author of 2026-10-09). What the form requires is refused before
 * anything is asked, a category without a nature among them.
 *
 * What a modification may change follows the commands the object lists (WF-IHM-0090, EP-02/L42g):
 * the type of a nature is offered only when it lists `change_kind` available, shown fixed otherwise,
 * the conditions it lacks said under it — a category of it employed, the last nature of provision
 * (#578) —, and the description of the dialog says so; a category is offered a nature of another type
 * only when it lists `change_cost_type` available, and otherwise the natures of its own type alone,
 * the conditions said under the choice — employed, bearing rates (#577), the last category of
 * provision (#578). The type of a nature is that of every nature the page reads for a session that
 * writes, deactivated ones included (`every`); a nature not among them leaves the category its own
 * alone. A code or an accounting code already held names
 * the object that holds it, as the list shows it (`names`).
 */
"use client";

import { useTranslations } from "next-intl";

import { createReferenceObject, updateReferenceObject } from "@/api/actions/reference";
import { useUnmet } from "@/components/commands/command";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import type { ObjectNames } from "@/components/commands/outcome-notice";

import { useListForm } from "./commands";
import {
  COST_TYPE_KIND_VALUES,
  type CostCategory,
  type CostType,
  type CostTypeKind,
  isCostTypeKind,
  type NatureChoice,
} from "./cost-kinds";
import { type Offered, offered } from "./kinds";
import {
  CODE_LENGTH,
  type Draft,
  type FormField,
  LABEL_LENGTH,
  ReferenceForm,
  required,
} from "./reference-form";

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
        accounting_code: row.accounting_code,
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

/** The body a category is written by, from the values checked. */
function categoryOf({ code = "", label = "", cost_type_id = "", accounting_code = "" }: Draft) {
  return { code, label, cost_type_id, accounting_code };
}

/**
 * The natures a category that may not change its type is offered, among those `offered` gives: those
 * of the type of its own nature, as the natures read give it — deactivated ones included for a session
 * that writes —, and its own; its own alone when they do not give its type.
 */
function sameKind<Offer extends { readonly id: string }>(
  choices: readonly Offer[],
  natures: readonly NatureChoice[],
  own: string | undefined,
): Offer[] {
  const kinds = new Map<string, CostTypeKind>(natures.map((nature) => [nature.id, nature.kind]));
  const kind = own === undefined ? undefined : kinds.get(own);
  return choices.filter(
    (choice) => choice.id === own || (kind !== undefined && kinds.get(choice.id) === kind),
  );
}

/** Whether a command is listed with conditions it lacks, which the form then says. */
function lacking(offer: CommandOffer | undefined): offer is CommandOffer {
  return offer !== undefined && offer.missing_conditions.length > 0;
}

/**
 * The field of the type of a nature, and whether it changes: a choice among the three of the
 * contract on a creation, or when the nature lists its change available (`change_kind`); shown fixed
 * otherwise, the conditions it lacks said under it.
 */
function useTypeField(): (nature: CostType | undefined) => {
  readonly field: FormField;
  readonly free: boolean;
} {
  const t = useTranslations("reference.costForm");
  const columns = useTranslations("grid.columns");
  const kinds = useTranslations("enums.CostTypeKind");
  const unmet = useUnmet();
  return (nature) => {
    const change =
      nature === undefined ? undefined : findOffer(nature.available_commands, "change_kind");
    const free = nature === undefined || change?.is_available === true;
    const shared = {
      name: "kind",
      label: columns("costTypeKind"),
      choices: COST_TYPE_KIND_VALUES.map((value) => [value, kinds(value)] as const),
    };
    if (free) {
      return { field: { ...shared, control: "choice", required: true }, free };
    }
    const note = lacking(change) ? t("kindFixedFor", { unmet: unmet(change) }) : t("kindFixed");
    return { field: { ...shared, control: "fixed", note }, free };
  };
}

/**
 * The field of the nature of a category: the active natures, and the one it is attached to; those of
 * its own type alone, the conditions it lacks said under the choice, unless it is created or lists its
 * attachment to a nature of another type available (`change_cost_type`).
 */
function useNatureField(
  natures: readonly NatureChoice[],
  every: readonly NatureChoice[] | undefined,
): (category: CostCategory | undefined) => FormField {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const unmet = useUnmet();
  const read = every ?? natures;
  /**
   * A nature as the choice shows it: by its code and its name — the code of one the natures offered
   * leave out taken from every nature read, by its name alone when none gives it —, marked when
   * deactivated.
   */
  const shownOf = (nature: Offered) => {
    const code = nature.code ?? read.find((each) => each.id === nature.id)?.code;
    const named =
      code === undefined ? nature.label : t("codedChoice", { code, label: nature.label });
    return nature.deactivated
      ? t("form.deactivatedChoice", { choice: named, kind: "cost_type" })
      : named;
  };
  /**
   * Why the choice offers fewer natures: those of the type of its own, or its own alone when no
   * nature read gives its type — a session that may not read the deactivated ones —, and the
   * conditions the attachment to a nature of another type lacks.
   */
  const noteOf = (change: CommandOffer | undefined, known: boolean) => {
    if (!known) {
      return lacking(change)
        ? t("costForm.ownOnlyFor", { unmet: unmet(change) })
        : t("costForm.ownOnly");
    }
    return lacking(change)
      ? t("costForm.sameKindFor", { unmet: unmet(change) })
      : t("costForm.sameKind");
  };
  return (category) => {
    const attached =
      category === undefined
        ? undefined
        : { id: category.cost_type_id, label: category.cost_type_label };
    const change =
      category === undefined
        ? undefined
        : findOffer(category.available_commands, "change_cost_type");
    const free = category === undefined || change?.is_available === true;
    const choices = offered(natures, attached);
    const known = read.some((nature) => nature.id === attached?.id);
    return {
      name: "cost_type_id",
      label: columns("costType"),
      control: "choice",
      required: true,
      choices: (free ? choices : sameKind(choices, read, attached?.id)).map(
        (nature) => [nature.id, shownOf(nature)] as const,
      ),
      note: free ? undefined : noteOf(change, known),
    };
  };
}

/** The dialog of the list of the natures or of the categories, while its form is open. */
export function CostDialog({
  natures,
  every,
  names,
}: {
  /**
   * The natures a category may be attached to, each with its type, in the order of the server; none
   * for the natures.
   */
  readonly natures: readonly NatureChoice[];
  /**
   * Every nature, deactivated ones included, each with its type, which the type of a category is
   * compared by; none read, the natures offered.
   */
  readonly every?: readonly NatureChoice[] | undefined;
  /** The objects the list shows, by identifier, which name the one that holds a code taken. */
  readonly names: ObjectNames;
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const typeField = useTypeField();
  const natureField = useNatureField(natures, every);
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
    names,
  };
  const common = [
    required("code", columns("code"), CODE_LENGTH),
    required("label", columns("label"), LABEL_LENGTH),
  ];
  if (kind === "cost_type") {
    const nature = row as CostType | undefined;
    const { field, free } = typeField(nature);
    return (
      <ReferenceForm
        {...shared}
        hint={t(free ? "costForm.costTypeHint" : "costForm.costTypeFixedHint")}
        fields={[...common, field]}
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
  return (
    <ReferenceForm
      {...shared}
      hint={t("costForm.costCategoryHint")}
      fields={[
        ...common,
        natureField(category),
        required("accounting_code", columns("accountingCode"), CODE_LENGTH),
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
