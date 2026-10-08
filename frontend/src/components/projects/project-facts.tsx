// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of a project say of it, as the API reads it (WF-PRJ-0080): on its page, its
 * code, its state by its badge — its word, its icon and its colour —, the date its order was received and its description; on its
 * settings, its inflation rate and its probability of winning, formatted from the exact decimal
 * of the contract. A value the project does not have yet is said to be missing, never invented.
 * An icon before each fact, which a screen reader leaves out.
 */
import {
  CalendarCheck,
  FileText,
  Hash,
  type LucideIcon,
  Percent,
  Target,
  Workflow,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { Project } from "@/components/context/reading";
import { formatPercent, formatPlanningDate } from "@/i18n/format";

import { ProjectStateBadge } from "./project-state-badge";

/** A fact of a project: its name, and what the project has of it. */
function Fact({
  icon: Icon,
  term,
  children,
}: {
  readonly icon: LucideIcon;
  readonly term: string;
  readonly children: ReactNode;
}) {
  return (
    <>
      <dt className="flex items-center gap-1.5 text-muted-foreground">
        <Icon aria-hidden="true" className="size-4 shrink-0" />
        {term}
      </dt>
      <dd>{children}</dd>
    </>
  );
}

/** A list of the facts of a project. */
function Facts({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return (
    <dl aria-label={label} className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
      {children}
    </dl>
  );
}

/** The code, the state, the order and the description of a project. */
export function ProjectFacts({ project }: { readonly project: Project }) {
  const t = useTranslations("projectFacts");
  const locale = useLocale();
  return (
    <Facts label={t("label")}>
      <Fact icon={Hash} term={t("code")}>
        {project.code ?? t("missing")}
      </Fact>
      <Fact icon={Workflow} term={t("state")}>
        <ProjectStateBadge state={project.state} />
      </Fact>
      <Fact icon={CalendarCheck} term={t("orderReceivedOn")}>
        {project.order_received_on == null
          ? t("missing")
          : formatPlanningDate(project.order_received_on, locale)}
      </Fact>
      <Fact icon={FileText} term={t("description")}>
        {project.description ?? t("missing")}
      </Fact>
    </Facts>
  );
}

/** The settings of a project that are values of its own: its inflation, its chance of winning. */
export function SettingsFacts({ project }: { readonly project: Project }) {
  const t = useTranslations("projectFacts");
  const locale = useLocale();
  return (
    <Facts label={t("settings")}>
      <Fact icon={Percent} term={t("inflationRate")}>
        {formatPercent(project.inflation_rate, locale)}
      </Fact>
      <Fact icon={Target} term={t("winProbability")}>
        {formatPercent(project.win_probability, locale)}
      </Fact>
    </Facts>
  );
}
