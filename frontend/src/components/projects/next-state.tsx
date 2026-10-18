// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The next state of a project, as the server reads it (`getProjectNextState`, WF-CYC-0050): the
 * state its trigger will lead it to, the trigger itself, and the conditions it still lacks, one by
 * one — none of them a command: the transitions to pricing and in progress follow their facts alone
 * (WF-CYC-0020). A project that no fact leads further has no next state, and the screen says why:
 * in progress, only the exits of its lifecycle remain; terminal, it is closed, and no state follows it
 * (WF-CYC-0080) — the terminal states being those an exit leads to (`EXIT_STATES`), from the contract.
 *
 * The trigger is one of the two facts of the lifecycle the contract enumerates (`LifecycleTrigger`,
 * figure 8 of the specification, EP-14/L42i), rendered by the catalogue of the enumeration; the server
 * answers a project in progress or terminal without a next state nor a trigger. Neither server nor
 * client: it renders on either side.
 */
import { CircleArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { EXIT_STATES } from "@/components/commands/exits";

import { ProjectStateBadge } from "./project-state-badge";

type NextState = components["schemas"]["NextState"];
type ProjectState = components["schemas"]["ProjectState"];

/** The terminal states of a project: those an exit of its lifecycle leads to (WF-CYC-0080). */
const TERMINAL: readonly ProjectState[] = Object.values(EXIT_STATES);

/** Render the next state of a project, its trigger and the conditions it still lacks. */
export function NextStateFacts({ next }: { readonly next: NextState }) {
  const t = useTranslations("nextState");
  const condition = useTranslations("enums.CommandCondition");
  const triggers = useTranslations("enums.LifecycleTrigger");
  const { next_state: state, trigger, missing_conditions: missing } = next;
  return (
    <section aria-label={t("title")} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <CircleArrowRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        {t("title")}
      </h2>
      {state === null ? (
        <p className="text-sm">{t(TERMINAL.includes(next.current_state) ? "closed" : "none")}</p>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-muted-foreground">{t("state")}</dt>
          <dd>
            <ProjectStateBadge state={state} />
          </dd>
          {trigger === null ? null : (
            <>
              <dt className="text-muted-foreground">{t("trigger")}</dt>
              <dd>{triggers(trigger)}</dd>
            </>
          )}
          <dt className="text-muted-foreground">{t("conditions")}</dt>
          <dd>
            {missing.length === 0 ? (
              t("noCondition")
            ) : (
              <ul className="list-inside list-disc">
                {missing.map((code) => (
                  <li key={code}>{condition(code)}</li>
                ))}
              </ul>
            )}
          </dd>
        </dl>
      )}
    </section>
  );
}
