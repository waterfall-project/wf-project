// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen says of a marking or of the merge of an amendment whose task failed because the own
 * estimate of some risks could not be updated without presenting its update (US-3140, WF-RIS-0070,
 * `OWN_ESTIMATES_OUT_OF_DATE`): the update keeps a value against the project, or is refused, and nothing
 * was written. The screen names the risks the task names (`params.risks`, in the order of the list of
 * risks), and leads each to its detail, where « Réexaminer » presents the report of the update to
 * confirm or to correct (`own-estimate-first.tsx`); once they are up to date, the gesture is made again.
 *
 * A task that failed for any other motive says nothing here: the tracker tells it.
 */
"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";

import type { Problem } from "@/api/problem";
import { riskHref } from "@/components/risks/address";
import { useWhenTaskFails } from "@/components/tasks/task-tracker";

/** The address of the detail of a risk, in the revision the gesture was made in. */
function detailOf(projectId: string, revisionId: string, riskId: string): string {
  return riskHref(
    `/projects/${encodeURIComponent(projectId)}/revisions/${encodeURIComponent(revisionId)}/risks`,
    new URLSearchParams(),
    riskId,
  );
}

/**
 * The risks a failed task names, each with the way to its report; nothing for another failure, and
 * nothing while no task was started — the tracker of the shell is needed only once one was.
 */
export function OwnEstimatesOutOfDate(props: {
  /** The task of the marking or of the merge, none until one was started. */
  readonly taskId: string | undefined;
  readonly projectId: string;
  readonly revisionId: string;
}) {
  const { taskId, ...where } = props;
  return taskId === undefined ? null : <Named key={taskId} taskId={taskId} {...where} />;
}

/** The risks the task named failed. */
function Named({
  taskId,
  projectId,
  revisionId,
}: {
  readonly taskId: string;
  readonly projectId: string;
  readonly revisionId: string;
}) {
  const t = useTranslations("ownEstimatesOutOfDate");
  const [problem, setProblem] = useState<Problem>();
  useWhenTaskFails(
    taskId,
    useCallback((line) => {
      setProblem(line.problem);
    }, []),
  );
  const risks = problem?.code === "OWN_ESTIMATES_OUT_OF_DATE" ? problem.params?.risks : undefined;
  if (risks === undefined || risks.length === 0) {
    return null;
  }
  return (
    <section aria-label={t("title")} role="alert" className="max-w-xl space-y-2 text-sm">
      <h2 className="text-sm font-semibold">{t("title")}</h2>
      <p>{t("statement", { count: risks.length })}</p>
      <ul className="list-inside list-disc">
        {risks.map((risk) => (
          <li key={risk.risk_id}>
            {risk.label}{" "}
            <Link
              className="underline"
              href={detailOf(projectId, revisionId, risk.risk_id)}
              aria-label={t("readOf", { label: risk.label })}
            >
              {t("read")}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
