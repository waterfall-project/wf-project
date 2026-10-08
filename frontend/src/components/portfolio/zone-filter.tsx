// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the list of the projects of the portfolio by the zone of their indices (#313,
 * WF-IHM-0130): a button for each zone of the contract, named by the one signal of the application
 * (WF-IHM-0070), pressed when the address filters on it, and one for every zone. A zone chosen only
 * changes the address (`zones`, as the contract names it), back to the first page; the page reads
 * the projects anew, which the server retains when their cost index or their schedule index is in
 * one of the zones, with their number (`meta.total`). The front filters nothing. A zone chosen goes
 * on from the address last asked (`usePendingAddress`).
 */
"use client";

import { Circle, CircleCheck, ListFilter } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { usePendingAddress } from "@/components/grid/pending-address";
import { Signal } from "@/components/signal/signal";
import { Button } from "@/components/ui/button";

import {
  type AlertZone,
  INDEX_ZONES,
  parametersHref,
  readZones,
  ZONES,
  zonesValue,
} from "./address";

/** Render the filter of the projects by the zone of their indices, the zones asked pressed. */
export function ZoneFilter({ zones }: { readonly zones: readonly AlertZone[] }) {
  const t = useTranslations("portfolio.projects");
  const pathname = usePathname();
  const { request } = usePendingAddress();
  /** Filter on the zones a change makes of those last asked. */
  const filter = (change: (asked: readonly AlertZone[]) => readonly AlertZone[]) => {
    request((query) =>
      parametersHref(pathname, query, { [ZONES]: zonesValue(change(readZones(query))) }),
    );
  };
  const every = zones.length === 0;
  return (
    <div role="group" aria-label={t("zones")} className="flex flex-wrap items-center gap-1.5">
      <Button
        size="sm"
        variant={every ? "default" : "outline"}
        aria-pressed={every}
        onClick={() => {
          filter(() => []);
        }}
      >
        <ListFilter aria-hidden="true" className="size-4" />
        {t("everyZone")}
      </Button>
      {INDEX_ZONES.map((zone) => {
        // Pressed as the address shows it, by its mark and its shade, never by a colour alone.
        const pressed = zones.includes(zone);
        const Mark = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={zone}
            size="sm"
            variant="outline"
            aria-pressed={pressed}
            className={pressed ? "bg-accent text-accent-foreground" : undefined}
            onClick={() => {
              filter((asked) =>
                asked.includes(zone) ? asked.filter((each) => each !== zone) : [...asked, zone],
              );
            }}
          >
            <Mark aria-hidden="true" className="size-4" />
            <Signal zone={zone} />
          </Button>
        );
      })}
    </div>
  );
}
