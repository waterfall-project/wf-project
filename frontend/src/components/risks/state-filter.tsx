// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the risks by state (WF-RIS-0040): a button for each state of the contract, pressed
 * when the address filters on it, and one for every state. A state chosen only changes the address
 * (`states`, as the contract names it); the page reads the risks anew, which the server filters,
 * with the totals of those it retained (WF-IHM-0130). The front filters nothing.
 */
"use client";

import { Circle, CircleCheck, ListFilter } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

import { RISK_STATES, type RiskState, statesHref } from "./address";

/** Render the filter of the risks by state, the states the address filters on pressed. */
export function RiskStateFilter({ states }: { readonly states: readonly RiskState[] }) {
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const query = useSearchParams();
  const filter = (next: readonly RiskState[]) => {
    router.push(statesHref(pathname, new URLSearchParams(query), next), { scroll: false });
  };
  const every = states.length === 0;
  return (
    <div
      role="group"
      aria-label={t("risks.filter")}
      className="flex flex-wrap items-center gap-1.5"
    >
      <Button
        size="sm"
        variant={every ? "default" : "outline"}
        aria-pressed={every}
        onClick={() => {
          filter([]);
        }}
      >
        <ListFilter aria-hidden="true" className="size-4" />
        {t("risks.everyState")}
      </Button>
      {RISK_STATES.map((state) => {
        const pressed = states.includes(state);
        const Icon = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={state}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              filter(pressed ? states.filter((each) => each !== state) : [...states, state]);
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            {t(`enums.RiskState.${state}`)}
          </Button>
        );
      })}
    </div>
  );
}
