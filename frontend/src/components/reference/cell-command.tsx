// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command in a cell of a dense grid of the reference data — modify, deactivate, reactivate,
 * designate by default —: a small button, its icon and its word, out of the order of tabulation, the
 * grid being one stop, which Enter on its cell presses (`CELL_COMMAND`).
 */
"use client";

import type { ComponentProps } from "react";

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
