// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command in a cell of a dense grid — modify, deactivate, reactivate, designate by default, mark a
 * backup, restore from it —: a small button, its icon and its word, out of the order of tabulation,
 * the grid being one stop, which Enter on its cell presses (`CELL_COMMAND`). And the same command
 * when the server lists it unavailable (`UnavailableCellCommand`): marked `aria-disabled`, described
 * by the conditions it lacks, and, pressed, saying them where the list tells what it could not do
 * rather than running — the one presentation of every unavailable command of a grid (WF-IHM-0090).
 */
"use client";

import { type ComponentProps, type ReactNode } from "react";

import { useUnmet } from "@/components/commands/command";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { type CommandOffer, UNAVAILABLE } from "@/components/commands/offer";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";

/** What a command of a cell says of itself, in its tooltip (`CommandTooltip`). */
export interface CellCommandSays {
  /** The accessible name of the command, which names the object it is about: the tooltip opens on it. */
  readonly label: string;
  /** What the command does, translated (`commands.<command>.help`). */
  readonly help: string;
  /**
   * The condition the command lacks: said in its tooltip, and the command marked `aria-disabled`
   * and described by it. None for a command available.
   */
  readonly unavailable?: string | undefined;
  /** Whether the command waits without a condition to say — a write of its row under way. */
  readonly waiting?: boolean | undefined;
}

/**
 * Render a command in a cell of a dense grid, with its tooltip. The tooltip sets `aria-disabled`
 * and the description of the condition (`unavailable`): the button sets neither.
 */
export function CellCommand({
  className,
  label,
  help,
  unavailable,
  waiting,
  ...props
}: Omit<ComponentProps<typeof Button>, "type" | "variant" | "size" | "tabIndex" | "aria-label"> &
  CellCommandSays) {
  return (
    <CommandTooltip label={label} help={help} unavailable={unavailable}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        tabIndex={-1}
        {...{ [CELL_COMMAND]: "" }}
        aria-label={label}
        {...(waiting === true && unavailable === undefined ? { "aria-disabled": true } : {})}
        className={cn("h-5 px-1.5 text-xs", className)}
        {...props}
      />
    </CommandTooltip>
  );
}

/**
 * A command of a cell the server lists unavailable, with the conditions it lacks: marked
 * `aria-disabled`, described by them, and, pressed, handing the sentence that names them to the
 * list, which says it in its region. It never runs.
 */
export function UnavailableCellCommand({
  name,
  help,
  offer,
  onPress,
  children,
}: {
  /** The accessible name of the command, which names the object it is about. */
  readonly name: string;
  /** What the command does, translated. */
  readonly help: string;
  readonly offer: CommandOffer;
  /** What the press says, given the sentence that names the conditions the command lacks. */
  readonly onPress: (unmet: string) => void;
  /** The icon and the word of the command. */
  readonly children: ReactNode;
}) {
  const unmet = useUnmet()(offer);
  return (
    <CellCommand
      label={name}
      help={help}
      unavailable={unmet}
      className={UNAVAILABLE}
      onClick={() => {
        onPress(unmet);
      }}
    >
      {children}
    </CellCommand>
  );
}
