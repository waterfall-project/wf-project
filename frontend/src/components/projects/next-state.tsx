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
 * The contract names the trigger by a code it does not enumerate (`NextState.trigger`): the
 * catalogue renders the two of the lifecycle (figure 8 of the specification), and a code it does
 * not know is said to be unknown rather than shown raw — an « Interface contract issue » raised by
 * EP-02/L44a. Neither server nor client: it renders on either side.
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

/** The triggers of the lifecycle the catalogue renders, as the examples of the contract name them. */
const TRIGGERS = ["first_revision_created", "reference_designated_and_code_set"] as const;

/** Whether a trigger is one the catalogue renders. */
function isTrigger(code: string): code is (typeof TRIGGERS)[number] {
  return (TRIGGERS as readonly string[]).includes(code);
}

/** Render the next state of a project, its trigger and the conditions it still lacks. */
export function NextStateFacts({ next }: { readonly next: NextState }) {
  const t = useTranslations("nextState");
  const condition = useTranslations("enums.CommandCondition");
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
          <dt className="text-muted-foreground">{t("trigger")}</dt>
          <dd>
            {trigger !== null && isTrigger(trigger)
              ? t(`triggers.${trigger}`)
              : t("unknownTrigger")}
          </dd>
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
