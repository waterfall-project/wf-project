// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sections of the screen of the indicators below the cards (US-0240): the tracking of the
 * milestones (FBS-4.8.6), the cumulative costs and their option shifted by the payment delays
 * (FBS-4.8.7), the curves of earned value (FBS-4.8.8), and the workload of the project
 * (FBS-4.4.4) with the choice of its basis and of a node of organisation, and its export.
 *
 * A choice is an address: the payment delays, the basis, the marked revision and the node are
 * parameters of the address of the screen, which the server reads and sends to the API — the
 * front filters nothing, shifts nothing and computes nothing (WF-ARC-0020). A choice keeps the
 * other parameters of the address, the filters of the context among them.
 */
import { Banknote, ListFilter } from "lucide-react";
import Link from "next/link";
import Form from "next/form";
import { useTranslations } from "next-intl";
import { type ReactNode, useId } from "react";

import type { components } from "@/api/generated/schema";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import { type CurveSeries, CurveSeriesChart } from "./curve-series-chart";
import { type MilestoneTracking, MilestoneChart } from "./milestone-chart";
import { type WorkloadPlan, WorkloadChart } from "./workload-chart";

/** The basis of a workload, as the contract names it. */
export type WorkloadBasis = WorkloadPlan["basis"];

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/** A node of the tree of organisation, as the API reads it. */
type OrgNode = components["schemas"]["OrgNode"];

/** The parameters of the address that a choice of the workload sets. */
export const WORKLOAD_PARAMETERS = ["basis", "workload_revision", "org_node_id"] as const;

/** The parameter of the address that shifts the cumulative costs by the payment delays. */
export const PAYMENT_DELAYS = "payment_delays";

/** The address of the screen: its path, and its parameters as Next hands them, in their order. */
export interface ScreenAddress {
  readonly pathname: string;
  readonly parameters: readonly (readonly [string, string])[];
}

/** The address of the screen with one parameter set, or removed when no value is given. */
function addressWith(address: ScreenAddress, name: string, value: string | undefined): string {
  const query = new URLSearchParams(
    address.parameters.filter(([key]) => key !== name).map(([key, kept]) => [key, kept]),
  );
  if (value !== undefined) {
    query.set(name, value);
  }
  const text = query.toString();
  return text === "" ? address.pathname : `${address.pathname}?${text}`;
}

/** A section of the screen under its title. */
function Section({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-2">
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

/** A sentence the screen says in place of a figure: none, or unavailable. */
function Said({ children }: { readonly children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/** The tracking of the milestones: its diagram, or that no milestone is tracked. */
export function MilestoneSection({ tracking }: { readonly tracking: MilestoneTracking }) {
  const t = useTranslations("projectIndicators.milestones");
  return (
    <Section title={t("title")}>
      {tracking.milestones.length === 0 ? (
        <Said>{t("none")}</Said>
      ) : (
        <MilestoneChart tracking={tracking} />
      )}
    </Section>
  );
}

/**
 * The cumulative costs, and the command that shifts them by the payment delays or takes the shift
 * back: the curves are named as the API says they are — shifted or not —, not as asked.
 */
export function CostCurveSection({
  curves,
  address,
}: {
  readonly curves: CurveSeries;
  readonly address: ScreenAddress;
}) {
  const t = useTranslations("projectIndicators.costCurve");
  const shifted = curves.payment_delays;
  return (
    <Section title={t("title")}>
      <Link
        href={addressWith(address, PAYMENT_DELAYS, shifted ? undefined : "true")}
        scroll={false}
        className={buttonVariants({ variant: "outline", size: "sm" })}
      >
        <Banknote aria-hidden="true" />
        {shifted ? t("undelay") : t("delay")}
      </Link>
      <CurveSeriesChart
        curves={curves}
        title={shifted ? t("chartTitleDelayed") : t("chartTitle")}
        description={shifted ? t("descriptionDelayed") : t("description")}
      />
    </Section>
  );
}

/** The curves of earned value. */
export function EarnedValueSection({ curves }: { readonly curves: CurveSeries }) {
  const t = useTranslations("projectIndicators.earnedValue");
  return (
    <Section title={t("title")}>
      <CurveSeriesChart curves={curves} title={t("chartTitle")} description={t("description")} />
    </Section>
  );
}

/** What the workload is asked on, as the address asks it. */
export interface WorkloadAsked {
  readonly basis: WorkloadBasis;
  readonly revision: string | undefined;
  readonly orgNode: string | undefined;
}

/** The workload of the project, what it can be asked on, and where its image comes from. */
export interface WorkloadSectionProps {
  /** What the API computes, `undefined` when it refuses the basis asked. */
  readonly workload: WorkloadPlan | undefined;
  readonly asked: WorkloadAsked;
  /**
   * The bases offered: on a project without a reference revision, only the revision under way;
   * the marked revisions, only when there is one (WF-DEV-0070).
   */
  readonly bases: readonly WorkloadBasis[];
  /** The marked revisions of the project, as the API lists them. */
  readonly marked: readonly Revision[];
  /** The nodes of organisation, as the API lists them. */
  readonly orgNodes: readonly OrgNode[];
  readonly address: ScreenAddress;
  /** The project, which the image names. */
  readonly project: { readonly label: string; readonly code: string };
  /** The name of the revision the workload is computed on. */
  readonly revision: string;
}

/** A field of the choice of the workload: its label and its list. */
function Choice({
  label,
  name,
  selected,
  children,
}: {
  readonly label: string;
  readonly name: string;
  readonly selected: string;
  readonly children: ReactNode;
}) {
  const id = useId();
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
              {revision.version_name ?? t("contextBanner.currentRevision")}
            </option>
          ))}
        </Choice>
      ) : null}
      <Choice label={t("workload.orgNode")} name="org_node_id" selected={asked.orgNode ?? ""}>
        <option value="">{t("workload.allOrgNodes")}</option>
        {orgNodes.map((node) => (
          <option key={node.org_node_id} value={node.org_node_id}>
            {node.label}
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

/**
 * The workload of the project: the choice of what it is computed on, the basis and the revision
 * the API says it read, and its chart — or that the API refuses the basis asked, or that no role
 * has a load on it.
 */
export function WorkloadSection(props: WorkloadSectionProps) {
  const t = useTranslations();
  const { workload, project, revision } = props;
  let content: ReactNode;
  if (workload === undefined) {
    content = <Said>{t("workload.unavailable")}</Said>;
  } else if (workload.roles.length === 0) {
    content = <Said>{t("workload.none")}</Said>;
  } else {
    content = (
      <WorkloadChart
        workload={workload}
        project={project.label}
        revision={revision}
        fileName={t("workload.fileName", { project: project.code })}
      />
    );
  }
  return (
    <Section title={t("workload.title")}>
      <WorkloadChoices {...props} />
      {workload === undefined ? null : (
        <Said>
          {t("workload.reading", {
            basis: t(`enums.WorkloadPlan.basis.${workload.basis}`),
            revision,
          })}
        </Said>
      )}
      {content}
    </Section>
  );
}
