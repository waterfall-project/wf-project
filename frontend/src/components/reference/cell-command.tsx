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

import { type ComponentProps, type ReactNode, useId } from "react";

import { useUnmet } from "@/components/commands/command";
import { type CommandOffer, UNAVAILABLE } from "@/components/commands/offer";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";

/** Render a command in a cell of a dense grid. */
export function CellCommand({
  className,
  ...props
}: Omit<ComponentProps<typeof Button>, "type" | "variant" | "size" | "tabIndex">) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      tabIndex={-1}
      {...{ [CELL_COMMAND]: "" }}
      className={cn("h-5 px-1.5 text-xs", className)}
      {...props}
    />
  );
}

/**
 * A command of a cell the server lists unavailable, with the conditions it lacks: marked
 * `aria-disabled`, described by them, and, pressed, handing the sentence that names them to the
 * list, which says it in its region. It never runs.
 */
export function UnavailableCellCommand({
  name,
  offer,
  onPress,
  children,
}: {
  /** The accessible name of the command, which names the object it is about. */
  readonly name: string;
  readonly offer: CommandOffer;
  /** What the press says, given the sentence that names the conditions the command lacks. */
  readonly onPress: (unmet: string) => void;
  /** The icon and the word of the command. */
  readonly children: ReactNode;
}) {
  const unmet = useUnmet()(offer);
  const described = `${useId()}-unmet`;
  return (
    <>
      <CellCommand
        aria-label={name}
        aria-disabled
        aria-describedby={described}
        title={unmet}
        className={UNAVAILABLE}
        onClick={() => {
          onPress(unmet);
        }}
      >
        {children}
      </CellCommand>
      <span id={described} className="sr-only">
        {unmet}
      </span>
    </>
  );
}
