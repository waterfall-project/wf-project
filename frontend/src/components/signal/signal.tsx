// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one signal of the application (WF-IHM-0070): the zone of an index, a budget overrun,
 * a cell of the risk matrix, the load of a role, a health signal of the portfolio all show
 * the same way. The zone comes from the API, which classes a value by the reference data —
 * the thresholds of the indices (WF-REF-0170), the zones of the risk matrix (WF-REF-0160);
 * the front never deduces a zone from a value (WF-ARC-0020).
 *
 * Each zone has its own shape, its own name from the catalogues and its own token of the
 * charter: the colour never carries the zone alone, so a grey copy, a printed page or a
 * colour-blind reader still tells the zones apart.
 */
import { CircleCheck, type LucideIcon, OctagonAlert, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

/** The zone of a signal, as the contract names it. */
export type AlertZone = components["schemas"]["AlertZone"];

/** How a zone shows: the shape of its icon, and the class of its token of the charter. */
interface ZoneStyle {
  readonly icon: LucideIcon;
  readonly tone: string;
}

/**
 * The only table of the zones: a circle for nominal, a triangle for watch, an octagon for
 * alert — the shapes of road signs, told apart without their colour. Every zone of the
 * contract has its line: one added there fails the type check until it is here.
 */
const ZONES: Readonly<Record<AlertZone, ZoneStyle>> = {
  nominal: { icon: CircleCheck, tone: "text-signal-nominal" },
  watch: { icon: TriangleAlert, tone: "text-signal-watch" },
  alert: { icon: OctagonAlert, tone: "text-signal-alert" },
};

/**
 * A signal: the zone the API gave, and how much room it takes — its icon and its name
 * written (`label`, the default), or its icon alone, its name given to assistive
 * technologies and to the pointer (`icon`), for a dense grid or a matrix.
 */
export interface SignalProps {
  readonly zone: AlertZone;
  readonly variant?: "label" | "icon";
}

/** Render the signal of a zone, its shape, its name and its colour. */
export function Signal({ zone, variant = "label" }: SignalProps) {
  const t = useTranslations();
  const { icon: Icon, tone } = ZONES[zone];
  const name = t(`enums.AlertZone.${zone}`);
  if (variant === "icon") {
    return (
      <span role="img" aria-label={name} title={name} className={`inline-flex ${tone}`}>
        <Icon aria-hidden="true" className="size-4" />
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${tone}`}>
      <Icon aria-hidden="true" className="size-4 shrink-0" />
      <span>{name}</span>
    </span>
  );
}
