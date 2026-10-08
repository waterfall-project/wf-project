// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one badge of the state of a project (#523), wherever a screen shows it: the list of projects
 * of the home and of the portfolio, the page, the settings and the lifecycle of a project. A list
 * is read at a glance by its colour, a token of the charter for each state (`--state-…`), in the
 * palette the author chose; but the colour never says a state alone (WF-IHM-0070): the badge
 * writes the word of the state, from the catalogues, and draws its own icon, so that a grey copy,
 * a printed page or a colour-blind reader still tells the states apart. The state is the API's;
 * the front deduces none.
 *
 * Neither server nor client: a page renders it on the server, a grid in the browser.
 */
import {
  Ban,
  Calculator,
  CircleDashed,
  CirclePlay,
  CircleX,
  type LucideIcon,
  SquareCheckBig,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/components/ui/utils";
import type { ProjectState } from "@/navigation/home";

/** How a state shows: its icon, and the classes of its tokens, its fill and its text. */
interface StateStyle {
  readonly icon: LucideIcon;
  readonly tone: string;
}

/**
 * The only table of the states: every state of the contract has its line — one added there fails
 * the type check until it is here —, its icon apart from the others and from the shapes of the
 * signals, its tokens written whole for Tailwind to find them.
 */
const STATES: Readonly<Record<ProjectState, StateStyle>> = {
  created: { icon: CircleDashed, tone: "bg-state-created text-state-created-foreground" },
  pricing: { icon: Calculator, tone: "bg-state-pricing text-state-pricing-foreground" },
  in_progress: {
    icon: CirclePlay,
    tone: "bg-state-in-progress text-state-in-progress-foreground",
  },
  completed: { icon: SquareCheckBig, tone: "bg-state-completed text-state-completed-foreground" },
  lost: { icon: CircleX, tone: "bg-state-lost text-state-lost-foreground" },
  abandoned: { icon: Ban, tone: "bg-state-abandoned text-state-abandoned-foreground" },
};

/** The state of a project, and the classes of where it sits — a cell truncates it. */
export interface ProjectStateBadgeProps {
  readonly state: ProjectState;
  readonly className?: string | undefined;
}

/** Render the state of a project: its word, its icon and its colour. */
export function ProjectStateBadge({ state, className }: ProjectStateBadgeProps) {
  const t = useTranslations("enums.ProjectState");
  const { icon: Icon, tone } = STATES[state];
  return (
    <span
      className={cn(
        "inline-flex w-fit shrink-0 items-center gap-1 overflow-hidden rounded-full px-2 py-px text-xs font-medium whitespace-nowrap",
        tone,
        className,
      )}
    >
      <Icon aria-hidden="true" className="size-3 shrink-0" />
      <span className="truncate">{t(state)}</span>
    </span>
  );
}
