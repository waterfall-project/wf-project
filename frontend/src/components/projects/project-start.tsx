// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The encart « Démarrer le projet » of the page of a project (US-0490, #1058): shown while the main
 * structure of the revision in progress bears no task — or, from the creation of the project, while
 * it has no revision (#1358) —, for whoever may modify the planning: the page reads both from the
 * server (`startOffers`) and renders it only then. Three choices. « Planning
 * automatique depuis le lotissement » leads to the work breakdown of the project, in entry, where the
 * planning is generated (`GeneratePlanning`): the order of WF-PRJ-0030, the work breakdown first,
 * then the skeleton; unavailable, it says what it lacks (WF-IHM-0090). « Importer un fichier MS
 * Project » opens the drop zone (`FileDrop`), which sends the file the way the screen of the imports
 * does. « Plus tard » folds the encart, for the session of the tab (`useFolded`); the button that
 * unfolds it stays on the page, which keeps the encart available as long as the structure is empty.
 */
"use client";

import { ChevronDown, Clock, Rocket, Workflow } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { Command } from "@/components/commands/command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { FileDrop } from "@/components/exchanges/file-drop";
import { Button, buttonVariants } from "@/components/ui/button";

import type { StartOffers } from "./start-offers";
import { keepFolded, useFolded } from "./start-fold";

/** The encart, the project it starts, and the addresses it leads to. */
export interface ProjectStartProps {
  readonly projectId: string;
  readonly offers: StartOffers;
  /** The work breakdown of the project in entry, from the encart, its context kept. */
  readonly breakdownHref: string;
  /** The address of the page, its context kept, from which the report of the import is shown. */
  readonly start: string;
}

/** Offer to start the planning of the project, or the way back to the encart once it is folded. */
export function ProjectStart({ projectId, offers, breakdownHref, start }: ProjectStartProps) {
  const t = useTranslations("projectStart");
  const folded = useFolded(projectId);
  const [dropping, setDropping] = useState(false);
  const drop = useId();
  const reopen = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const moved = useRef(false);
  // The focus follows the fold: to the button that unfolds, to the title once unfolded — never at the
  // first rendering, which is the page's.
  useEffect(() => {
    if (!moved.current) {
      return;
    }
    (folded ? reopen.current : heading.current)?.focus();
  }, [folded]);
  const fold = (next: boolean) => {
    moved.current = true;
    if (next) {
      setDropping(false);
    }
    keepFolded(projectId, next);
  };
  if (folded) {
    return (
      <Button
        ref={reopen}
        type="button"
        variant="outline"
        size="sm"
        aria-expanded={false}
        onClick={() => {
          fold(false);
        }}
      >
        <Rocket aria-hidden="true" />
        {t("reopen")}
      </Button>
    );
  }
  const skeleton = offers.skeleton;
  return (
    <section aria-label={t("title")} className="space-y-3 rounded-md border p-4">
      <h2
        ref={heading}
        tabIndex={-1}
        className="flex items-center gap-2 text-base font-semibold outline-none"
      >
        <Rocket aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        {t("title")}
      </h2>
      <p className="text-sm text-muted-foreground">{t("lead")}</p>
      <div className="flex flex-wrap items-start gap-2">
        {skeleton.is_available ? (
          <Link href={breakdownHref} className={buttonVariants({ variant: "outline", size: "sm" })}>
            <Workflow aria-hidden="true" />
            {t("skeleton")}
          </Link>
        ) : (
          <Command offer={skeleton} label={t("skeleton")} icon={<Workflow aria-hidden="true" />} />
        )}
        <Command
          offer={offers.planningImport}
          label={t("import")}
          icon={commandIcon(PROJECT_COMMAND_ICONS.import_planning)}
          disclosure={{
            expanded: dropping,
            controls: drop,
            toggle: () => {
              setDropping(!dropping);
            },
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            fold(true);
          }}
        >
          <Clock aria-hidden="true" />
          {t("later")}
          <ChevronDown aria-hidden="true" />
        </Button>
      </div>
      <ul className="space-y-1 text-xs text-muted-foreground">
        <li>{t("skeletonHint")}</li>
        <li>{t("importHint")}</li>
      </ul>
      <div id={drop}>
        {dropping && offers.planningImport?.is_available === true ? (
          <FileDrop projectId={projectId} start={start} />
        ) : null}
      </div>
    </section>
  );
}
