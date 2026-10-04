// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workload of a project (FBS-4.4.4, WF-DEV-0070), below the head of its screen: the choice of
 * what it is computed on — its basis, the marked revision of that basis, the node of organisation
 * —, the basis and the revision the API says it read, and its chart, exported as a PNG image that
 * names them (WF-IHM-0130).
 *
 * A choice is an address: the basis, the marked revision and the node are parameters of the address
 * of the screen, which the server reads and sends to the API — the front filters nothing and
 * computes nothing (WF-ARC-0020); the choice keeps the other parameters of the address, the
 * filters of the context among them. Only the bases the project admits are offered: on a project
 * without a reference revision, the revision under way alone; the marked revisions, only when the
 * project has one. A basis the API refuses all the same is said unavailable, and why.
 *
 * The section is named by `aria-label`, and each field by an identifier of its own: an identifier
 * of `useId` in a server component may meet one of a client component of the shell (#251).
 */
import { ListFilter } from "lucide-react";
import Form from "next/form";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import type { ReadOrRefused } from "@/api/problem";
import type { ChartProvenance } from "@/components/chart/chart";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import { type WorkloadPlan, WorkloadChart } from "./workload-chart";

/** The basis of a workload, as the contract names it. */
export type WorkloadBasis = WorkloadPlan["basis"];

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/** A node of the tree of organisation, as the API reads it. */
type OrgNode = components["schemas"]["OrgNode"];

/** The parameters of the address that the choice of the workload sets. */
export const WORKLOAD_PARAMETERS = ["basis", "workload_revision", "org_node_id"] as const;

/**
 * The refusals of what the workload is asked on, which the screen says unavailable, and why
 * (`refusalReason`): a project without a reference revision (409), a parameter the API does not
 * take (422).
 */
export const BASIS_REFUSED = [
  { status: 409, code: "STATE_FORBIDS_OPERATION" },
  { status: 422, code: "VALIDATION_FAILED" },
] as const;

/** A refusal of what the workload is asked on. */
export type BasisRefused = (typeof BASIS_REFUSED)[number];

/** The workload as the API gave it, or the refusal of what it is asked on. */
export type WorkloadRead = ReadOrRefused<WorkloadPlan, BasisRefused>;

/** The parameters of `getProjectWorkload` a refusal may name, and the key of its reason. */
const REFUSED_PARAMETERS: Readonly<Record<string, RefusalReason>> = {
  revision_id: "markedRevision",
  org_node_id: "orgNode",
};

/** Why the screen says the workload unavailable: the key of its sentence in the catalogue. */
export type RefusalReason = "noReference" | "markedRevision" | "orgNode" | "invalid";

/**
 * Why the API refused the workload: a project without a reference revision (409); on a 422, the
 * parameter its envelope points at (`fields[].pointer`, by its last segment) — the marked revision
 * missing or not marked, the node of organisation —, and a reason that names none when the
 * envelope points at none of them, or at both.
 */
export function refusalReason(refused: Extract<WorkloadRead, { kind: "refused" }>): RefusalReason {
  if (refused.refusal.status === 409) {
    return "noReference";
  }
  const named = new Set(
    (refused.problem.fields ?? []).flatMap((field) => {
      const reason = REFUSED_PARAMETERS[field.pointer.slice(field.pointer.lastIndexOf("/") + 1)];
      return reason === undefined ? [] : [reason];
    }),
  );
  const [only] = named;
  return named.size === 1 && only !== undefined ? only : "invalid";
}

/** What the workload is asked on, as the address asks it. */
export interface WorkloadAsked {
  readonly basis: WorkloadBasis;
  readonly revision: string | undefined;
  readonly orgNode: string | undefined;
}

/** The address of the screen: its path, and its parameters as Next hands them, in their order. */
export interface WorkloadAddress {
  readonly pathname: string;
  readonly parameters: readonly (readonly [string, string])[];
}

/** The workload of the project, what it can be asked on, and where its image comes from. */
export interface WorkloadSectionProps {
  readonly workload: WorkloadRead;
  readonly asked: WorkloadAsked;
  /** The bases offered: those the project admits (WF-DEV-0070). */
  readonly bases: readonly WorkloadBasis[];
  /** The marked revisions of the project, as the API lists them. */
  readonly marked: readonly Revision[];
  /** The nodes of organisation, as the API lists them. */
  readonly orgNodes: readonly OrgNode[];
  readonly address: WorkloadAddress;
  /** The project, which the image names. */
  readonly project: { readonly label: string; readonly code: string };
  /** The revision of the address, which may be the one the workload is computed on. */
  readonly shown: Revision | undefined;
}

/** The name of a marked revision: its version name, or that it has none — never the one under way. */
function useMarkedName(): (revision: Revision) => string {
  const t = useTranslations("workload");
  return (revision) => revision.version_name ?? t("unnamedRevision");
}

/**
 * The name of the revision the workload is computed on, which the API names by its identifier:
 * the revision of the address or a marked revision of the project, by its name — a marked one
 * without a name said so, never the one under way —; one neither of them is, the revision under way
 * when the API says it is in progress, unnamed otherwise.
 */
function useComputedOn(): (workload: WorkloadPlan, known: readonly Revision[]) => string {
  const t = useTranslations();
  const markedName = useMarkedName();
  return ({ context }, known) => {
    const found = known.find((revision) => revision.revision_id === context.revision_id);
    if (found !== undefined) {
      return found.status === "marked" ? markedName(found) : t("contextBanner.currentRevision");
    }
    return context.revision_status === "draft"
      ? t("contextBanner.currentRevision")
      : t("projectIndicators.elsewhere.unknown");
  };
}

/** A field of the choice of the workload: its label and its list, named by its parameter. */
function Choice({
  label,
  name,
  selected,
  children,
}: {
  readonly label: string;
  readonly name: (typeof WORKLOAD_PARAMETERS)[number];
  readonly selected: string;
  readonly children: ReactNode;
}) {
  const id = `workload-${name}`;
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect id={id} name={name} defaultValue={selected}>
        {children}
      </NativeSelect>
    </div>
  );
}

/** The choice of the basis, of the marked revision and of the node of organisation. */
function WorkloadChoices({
  asked,
  bases,
  marked,
  orgNodes,
  address,
}: Pick<WorkloadSectionProps, "asked" | "bases" | "marked" | "orgNodes" | "address">) {
  const t = useTranslations();
  const markedName = useMarkedName();
  const carried = address.parameters.filter(
    ([name]) => !(WORKLOAD_PARAMETERS as readonly string[]).includes(name),
  );
  return (
    <Form action={address.pathname} scroll={false} className="flex flex-wrap items-end gap-3">
      {carried.map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      <Choice label={t("workload.basis")} name="basis" selected={asked.basis}>
        {bases.map((basis) => (
          <option key={basis} value={basis}>
            {t(`enums.WorkloadBasis.${basis}`)}
          </option>
        ))}
      </Choice>
      {bases.includes("marked_remaining") ? (
        <Choice
          label={t("workload.markedRevision")}
          name="workload_revision"
          selected={asked.revision ?? marked[0]?.revision_id ?? ""}
        >
          {marked.map((revision) => (
            <option key={revision.revision_id} value={revision.revision_id}>
              {markedName(revision)}
            </option>
          ))}
        </Choice>
      ) : null}
      {/* The nodes in the order of the API, each with the label of its parent: the tree is not
          drawn (#297). */}
      <Choice label={t("workload.orgNode")} name="org_node_id" selected={asked.orgNode ?? ""}>
        <option value="">{t("workload.allOrgNodes")}</option>
        {orgNodes.map((node) => (
          <option key={node.org_node_id} value={node.org_node_id}>
            {node.parent_label === null
              ? node.label
              : t("workload.orgNodeIn", { node: node.label, parent: node.parent_label })}
          </option>
        ))}
      </Choice>
      <Button type="submit" variant="outline" size="sm">
        <ListFilter aria-hidden="true" />
        {t("workload.show")}
      </Button>
    </Form>
  );
}

/** A sentence the screen says in place of the chart: none, or unavailable and why. */
function Said({ children }: { readonly children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/**
 * The workload the API computed: the basis and the revision it says it read, and its chart — or
 * that no role has a load on it, of the node filtered if one is.
 */
function ComputedWorkload({
  workload,
  node,
  project,
  known,
}: {
  readonly workload: WorkloadPlan;
  /** The label of the node of organisation filtered, if one is. */
  readonly node: string | undefined;
  readonly project: WorkloadSectionProps["project"];
  /** The revisions the screen read, which may name the one the workload is computed on. */
  readonly known: readonly Revision[];
}) {
  const t = useTranslations();
  const revision = useComputedOn()(workload, known);
  const basis = t(`enums.WorkloadPlan.basis.${workload.basis}`);
  const provenance: ChartProvenance = {
    project: project.label,
    code: project.code,
    revision,
    detail: t("workload.exportDetail", { basis, node: node ?? t("workload.allOrgNodes") }),
  };
  return (
    <>
      <Said>{t("workload.reading", { basis, revision })}</Said>
      {workload.roles.length === 0 ? (
        <Said>{node === undefined ? t("workload.none") : t("workload.noneInNode", { node })}</Said>
      ) : (
        <WorkloadChart workload={workload} provenance={provenance} />
      )}
    </>
  );
}

/**
 * The workload of the project: the choice of what it is computed on, then the workload — or why
 * the API refuses the basis asked.
 */
export function WorkloadSection(props: WorkloadSectionProps) {
  const t = useTranslations();
  const { workload, asked, orgNodes, project, shown, marked } = props;
  const node =
    asked.orgNode === undefined
      ? undefined
      : (orgNodes.find((each) => each.org_node_id === asked.orgNode)?.label ??
        t("workload.unknownOrgNode"));
  return (
    <section aria-label={t("workload.title")} className="space-y-3">
      <WorkloadChoices {...props} />
      {workload.kind === "refused" ? (
        <Said>{t(`workload.refused.${refusalReason(workload)}`)}</Said>
      ) : (
        <ComputedWorkload
          workload={workload.data}
          node={node}
          project={project}
          known={[...(shown === undefined ? [] : [shown]), ...marked]}
        />
      )}
    </section>
  );
}
