// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The export of the Gantt as a PNG image (WF-IHM-0130, US-0530): its command beside the zoom, in
 * the corner of its header, and in the menu of a cell, the keyboard reaching it there; the probes
 * of its colours, which the image is drawn in (`gantt-image.ts`). Offered where the grid names where
 * the Gantt comes from, unavailable, saying why, when its image is too large for a canvas.
 */
"use client";

import { ImageDown } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { RefObject } from "react";

import { Probes, useProvenance } from "@/components/chart/chart";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { MenuCommand } from "@/components/commands/menu-command";
import { UNAVAILABLE } from "@/components/commands/offer";
import { Button } from "@/components/ui/button";
import { ContextMenuItem } from "@/components/ui/context-menu";

import { axisWriter, labelsOf } from "./axis-labels";
import { DAY_OFF_HATCH } from "./days-off";
import type { GanttExporting, GanttView } from "./gantt";
import { type AxisLabel, exportGanttPng, GANTT_PROBES, readGanttColours } from "./gantt-image";

/** The probes of the colours of the Gantt, hidden: those of a chart, its bars, its days off. */
export function GanttProbes({ probes }: { readonly probes: RefObject<HTMLSpanElement | null> }) {
  return (
    <span ref={probes} hidden>
      <Probes />
      <span data-probe={GANTT_PROBES.critical} className="text-destructive" />
      <span data-probe={GANTT_PROBES.primary} className="text-primary" />
      <svg>
        <rect data-probe={GANTT_PROBES.dayOff} className={DAY_OFF_HATCH.fillClass} />
        <line data-probe={GANTT_PROBES.dayOffMark} className={DAY_OFF_HATCH.markClass} />
      </svg>
    </span>
  );
}

/**
 * The export of the Gantt as a PNG image, of the image it draws (`exportGanttPng`): its rows and
 * its axis as the Gantt shows them, the labels written as its header writes them; nothing when it
 * is too large to draw.
 */
function useGanttExport(view: GanttView, exporting: GanttExporting): () => void {
  const t = useTranslations("gantt");
  const locale = useLocale();
  const image = useProvenance(
    exporting.exported.provenance,
    t("title"),
    exporting.exported.scheduledAt,
    t("file"),
  );
  return () => {
    const probes = exporting.probes.current;
    if (probes === null || !exporting.fits) {
      return;
    }
    const write = axisWriter(t, locale, view);
    const labels = (which: "lower" | "upper"): AxisLabel[] =>
      labelsOf(view[which], exporting.width, which, view.layout.at).map(
        ([tick, x]) => [x, write(which, tick)] as const,
      );
    exportGanttPng(
      {
        rows: exporting.rows,
        layout: view.layout,
        width: exporting.width,
        lower: view.lower,
        upper: view.upper,
        labels: { upper: labels("upper"), lower: labels("lower") },
        dayWidth: view.dayWidth,
        legend: view.tinted ? t("dayOff") : undefined,
      },
      readGanttColours(probes),
      image(),
    );
  };
}

/** The command that exports the Gantt, beside its zoom; unavailable, saying why, when too large. */
export function GanttExportButton({
  view,
  exporting,
}: {
  readonly view: GanttView;
  readonly exporting: GanttExporting;
}) {
  const t = useTranslations("chart");
  const said = useTranslations("commands");
  const run = useGanttExport(view, exporting);
  return (
    <CommandTooltip
      label={t("exportPng")}
      help={said("exportGantt.help")}
      unavailable={exporting.fits ? undefined : said("exportGantt.unavailable")}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        tabIndex={-1}
        className={`size-5 [&_svg]:size-3.5 ${UNAVAILABLE}`}
        aria-label={t("exportPng")}
        onClick={run}
      >
        <ImageDown aria-hidden="true" />
      </Button>
    </CommandTooltip>
  );
}

/** The command that exports the Gantt, in the menu of a cell, after its zoom. */
export function GanttExportItem({
  view,
  exporting,
}: {
  readonly view: GanttView;
  readonly exporting: GanttExporting;
}) {
  const t = useTranslations("chart");
  const said = useTranslations("commands");
  const run = useGanttExport(view, exporting);
  return (
    <MenuCommand
      item={ContextMenuItem}
      label={t("exportPng")}
      help={said("exportGantt.help")}
      unavailable={exporting.fits ? undefined : said("exportGantt.unavailable")}
      icon={<ImageDown aria-hidden="true" />}
      className={UNAVAILABLE}
      onSelect={(event) => {
        if (!exporting.fits) {
          event.preventDefault();
          return;
        }
        run();
      }}
    />
  );
}
