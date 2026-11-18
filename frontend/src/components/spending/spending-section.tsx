// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The spending projection of a project (FBS-4.4.5, WF-DEV-0100), below the head of its screen: the
 * choice of what it is computed on — its basis, the marked revision of that basis, the date it is
 * read at (consumption or payment), the sub-project —, the basis and the revision the API says it
 * read, and its chart, exported as a PNG image that names them (WF-IHM-0130).
 *
 * A choice is an address: the basis, the marked revision, the date and the sub-project are
 * parameters of the address of the screen, which the server reads and sends to the API — the front
 * filters nothing and computes nothing (WF-ARC-0020); the choice keeps the other parameters of the
 * address. Only the bases the project admits are offered. A projection the API refuses — a project
 * without a reference revision, a marked revision or a sub-project it does not know, a labour
 * category without an hourly rate — is said unavailable, and why.
 *
 * The section is the card of the screen (`SectionCard`), the choice in it. The card is named by
 * `aria-label`, and each field by an identifier of its own: an identifier of `useId` in a server
 * component may meet one of a client component of the shell (#251).
 */
import { Banknote, ListFilter } from "lucide-react";
import Form from "next/form";
import { useLocale, useMessages, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import type { ReadOrRefused } from "@/api/problem";
import type { ChartProvenance } from "@/components/chart/chart";
import { SectionCard } from "@/components/shell/section-card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { problemMessage } from "@/i18n/problem";
import { UNASSIGNED } from "@/navigation/context";

import { SpendingChart } from "./spending-chart";
import type { SpendingPlan } from "./spending-rows";

/** The basis of a projection, as the contract names it. */
export type SpendingBasis = SpendingPlan["basis"];

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/** A sub-project of the project, as the API reads it. */
type Subproject = components["schemas"]["Subproject"];

/** The parameter of the address that asks the date of payment, as the indicators ask it. */
export const PAYMENT_DELAYS = "payment_delays";

/** The parameter of the address that names the marked revision of the basis. */
export const SPENDING_REVISION = "spending_revision";

/** The parameters of the address that the choice of the projection sets. */
export const SPENDING_PARAMETERS = [
  "basis",
  SPENDING_REVISION,
  "subproject_id",
  PAYMENT_DELAYS,
] as const;

/**
 * The refusals of what the projection is asked on, which the screen says unavailable, and why
 * (`refusalReason`): a project without the revision of the basis asked (409), a parameter the
 * API does not take or a labour category without an hourly rate (422).
 */
export const SPENDING_REFUSED = [
  { status: 409, code: "STATE_FORBIDS_OPERATION" },
  { status: 422, code: "HOURLY_RATE_MISSING" },
  { status: 422, code: "VALIDATION_FAILED" },
] as const;

/** A refusal of what the projection is asked on. */
export type SpendingRefused = (typeof SPENDING_REFUSED)[number];

/** The projection as the API gave it, or the refusal of what it is asked on. */
export type SpendingRead = ReadOrRefused<SpendingPlan, SpendingRefused>;

/** The parameters of `getProjectSpending` a refusal may point at, and the reason it gives. */
const REFUSED_PARAMETERS: ReadonlyMap<string, "markedRevision" | "subproject"> = new Map([
  ["/query/revision_id", "markedRevision"],
  ["/query/subproject_id", "subproject"],
]);

/** Why the screen says the projection unavailable: the key of its sentence in the catalogue. */
export type RefusalReason =
  "noReference" | "noCurrent" | "rateMissing" | "markedRevision" | "subproject" | "invalid";

/**
 * Why the API refused the projection: the basis it lacks (409) — the reference revision of
 * `reference_budget`, the current revision of `current_remaining`, each said by its own sentence;
 * on the basis of a marked revision the contract gives no 409, so none is guessed; a labour
 * category without a rate (422, `HOURLY_RATE_MISSING`); otherwise the parameter the envelope points
 * at (`fields[].pointer`, whole), and a reason that names none when it points at none of them, or
 * at both.
 */
export function refusalReason(
  refused: Extract<SpendingRead, { kind: "refused" }>,
  basis: SpendingBasis,
): RefusalReason {
  if (refused.refusal.status === 409) {
    return basis === "reference_budget"
      ? "noReference"
      : basis === "current_remaining"
        ? "noCurrent"
        : "invalid";
  }
  if (refused.refusal.code === "HOURLY_RATE_MISSING") {
    return "rateMissing";
  }
  const named = new Set(
    (refused.problem.fields ?? []).flatMap((field) => {
      const reason = REFUSED_PARAMETERS.get(field.pointer);
      return reason === undefined ? [] : [reason];
    }),
  );
  const [only] = named;
  return named.size === 1 && only !== undefined ? only : "invalid";
}

/** What the projection is asked on, as the address asks it. */
export interface SpendingAsked {
  readonly basis: SpendingBasis;
  readonly revision: string | undefined;
  /** The sub-project, or `unassigned`; none, the whole project. */
  readonly subproject: string | undefined;
  /** Whether the amounts are read at the date of payment. */
  readonly payment: boolean;
}

/** The address of the screen: its path, and its parameters as Next hands them, in their order. */
export interface SpendingAddress {
  readonly pathname: string;
  readonly parameters: readonly (readonly [string, string])[];
}

/** The projection of the project, what it can be asked on, and where its image comes from. */
export interface SpendingSectionProps {
  readonly spending: SpendingRead;
  readonly asked: SpendingAsked;
  /** The bases offered: those the project admits (WF-DEV-0100). */
  readonly bases: readonly SpendingBasis[];
  /** The marked revisions of the project, as the API lists them. */
  readonly marked: readonly Revision[];
  /** The sub-projects of the project, as the API lists them. */
  readonly subprojects: readonly Subproject[];
  readonly address: SpendingAddress;
  /** The project, which the image names. */
  readonly project: { readonly label: string; readonly code: string };
  /** The revision of the address, which may be the one the projection is computed on. */
  readonly shown: Revision | undefined;
}

/** The name of a marked revision: its version name, or that it has none. */
function useMarkedName(): (revision: Revision) => string {
  const t = useTranslations("spending");
  return (revision) => revision.version_name ?? t("unnamedRevision");
}

/**
 * The name of the revision the projection is computed on, which the API names by its identifier:
 * the revision of the address or a marked revision of the project, by its name; one neither of them
 * is, the revision under way when the API says it is in progress, unnamed otherwise.
 */
function useComputedOn(): (plan: SpendingPlan, known: readonly Revision[]) => string {
  const t = useTranslations();
  const markedName = useMarkedName();
  return ({ context }, known) => {
    const found = known.find((revision) => revision.revision_id === context.revision_id);
    if (found !== undefined) {
      return found.status === "marked" ? markedName(found) : t("contextBanner.currentRevision");
    }
    return context.revision_status === "draft"
      ? t("contextBanner.currentRevision")
      : t("contextBanner.unnamedRevision");
  };
}

/** A field of the choice of the projection: its label and its list, named by its parameter. */
function Choice({
  label,
  name,
  selected,
  children,
}: {
  readonly label: string;
  readonly name: (typeof SPENDING_PARAMETERS)[number];
  readonly selected: string;
  readonly children: ReactNode;
}) {
  const id = `spending-${name}`;
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect id={id} name={name} defaultValue={selected}>
        {children}
      </NativeSelect>
    </div>
  );
}

/** The choice of the basis, of the marked revision, of the date and of the sub-project. */
function SpendingChoices({
  asked,
  bases,
  marked,
  subprojects,
  address,
}: Pick<SpendingSectionProps, "asked" | "bases" | "marked" | "subprojects" | "address">) {
  const t = useTranslations();
  const markedName = useMarkedName();
  const carried = address.parameters.filter(
    ([name]) => !(SPENDING_PARAMETERS as readonly string[]).includes(name),
  );
  return (
    <Form action={address.pathname} scroll={false} className="flex flex-wrap items-end gap-3">
      {carried.map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <Choice label={t("spending.basis")} name="basis" selected={asked.basis}>
        {bases.map((basis) => (
          <option key={basis} value={basis}>
            {t(`enums.WorkloadBasis.${basis}`)}
          </option>
        ))}
      </Choice>
      {bases.includes("marked_remaining") ? (
        <Choice
          label={t("spending.markedRevision")}
          name={SPENDING_REVISION}
          selected={asked.revision ?? marked[0]?.revision_id ?? ""}
        >
          {marked.map((revision) => (
            <option key={revision.revision_id} value={revision.revision_id}>
              {markedName(revision)}
            </option>
          ))}
        </Choice>
      ) : null}
      <Choice
        label={t("spending.date")}
        name={PAYMENT_DELAYS}
        selected={asked.payment ? "true" : ""}
      >
        <option value="">{t("spending.consumption")}</option>
        <option value="true">{t("spending.payment")}</option>
      </Choice>
      <Choice
        label={t("spending.subproject")}
        name="subproject_id"
        selected={asked.subproject ?? ""}
      >
        <option value="">{t("spending.allSubprojects")}</option>
        <option value={UNASSIGNED}>{t("spending.noSubproject")}</option>
        {subprojects.map((subproject) => (
          <option key={subproject.subproject_id} value={subproject.subproject_id}>
            {t("spending.subprojectChoice", { code: subproject.code, label: subproject.label })}
          </option>
        ))}
      </Choice>
      <Button type="submit" variant="outline" size="sm">
        <ListFilter aria-hidden="true" />
        {t("spending.show")}
      </Button>
    </Form>
  );
}

/** A sentence the screen says in place of the chart: none, or unavailable and why. */
function Said({ children }: { readonly children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/** Why the API refused the projection, in a sentence. */
function Refused({
  refused,
  basis,
}: {
  readonly refused: Extract<SpendingRead, { kind: "refused" }>;
  readonly basis: SpendingBasis;
}) {
  const t = useTranslations("spending");
  const locale = useLocale();
  const messages = useMessages();
  const reason = refusalReason(refused, basis);
  return (
    <Said>
      {reason === "rateMissing"
        ? problemMessage(refused.problem, { locale, messages })
        : t(`refused.${reason}`)}
    </Said>
  );
}

/**
 * The projection the API computed: the basis and the revision it says it read, and its chart — or
 * that no cost type carries an amount on it.
 */
function ComputedSpending({
  spending,
  asked,
  subprojectName,
  project,
  known,
}: {
  readonly spending: SpendingPlan;
  readonly asked: SpendingAsked;
  /** The name of the sub-project filtered, if one is. */
  readonly subprojectName: string | undefined;
  readonly project: SpendingSectionProps["project"];
  /** The revisions the screen read, which may name the one the projection is computed on. */
  readonly known: readonly Revision[];
}) {
  const t = useTranslations();
  const revision = useComputedOn()(spending, known);
  const basis = t(`enums.SpendingProjection.basis.${spending.basis}`);
  const date = t(asked.payment ? "spending.payment" : "spending.consumption");
  const provenance: ChartProvenance = {
    project: project.label,
    code: project.code,
    revision,
    detail: t("spending.exportDetail", {
      basis,
      date,
      subproject: subprojectName ?? t("spending.allSubprojects"),
    }),
  };
  return (
    <>
      <Said>{t("spending.reading", { basis, revision, date })}</Said>
      {spending.cost_types.length === 0 ? (
        <Said>{t("spending.none")}</Said>
      ) : (
        <SpendingChart spending={spending} provenance={provenance} />
      )}
    </>
  );
}

/**
 * The projection of the project: the choice of what it is computed on, then the projection — or why
 * the API refuses what is asked.
 */
export function SpendingSection(props: SpendingSectionProps) {
  const t = useTranslations("spending");
  const { spending, asked, subprojects, project, shown, marked } = props;
  const subprojectName =
    asked.subproject === undefined
      ? undefined
      : asked.subproject === UNASSIGNED
        ? t("noSubproject")
        : (subprojects.find((each) => each.subproject_id === asked.subproject)?.label ??
          t("unknownSubproject"));
  return (
    <SectionCard title={t("title")} icon={Banknote}>
      <div className="flex min-w-0 flex-col gap-3">
        <SpendingChoices {...props} />
        {spending.kind === "refused" ? (
          <Refused refused={spending} basis={asked.basis} />
        ) : (
          <ComputedSpending
            spending={spending.data}
            asked={asked}
            subprojectName={subprojectName}
            project={project}
            known={[...(shown === undefined ? [] : [shown]), ...marked]}
          />
        )}
      </div>
    </SectionCard>
  );
}
