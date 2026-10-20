// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the tasks and the messages of the shell, as a test of a screen reads it: a modal
 * sheet its button opens (`TaskPanel`), outside which nothing is read while it is open.
 */
import { fireEvent, screen } from "@testing-library/react";

/** The button of the bar that opens and closes the panel, read while the panel hides it. */
export function tasksButton(): HTMLElement {
  return screen.getByRole("button", { name: /^Tâches et messages/, hidden: true });
}

/** The region of the tasks followed, in the panel, opened by its button when it is closed. */
export function tasksRegion(): HTMLElement {
  if (screen.queryByRole("dialog") === null) {
    fireEvent.click(tasksButton());
  }
  return screen.getByRole("region", { name: "Tâches de fond" });
}

/** Close the panel, as its button does, for the screen under it to be read again. */
export function closeTasks(): void {
  if (screen.queryByRole("dialog") !== null) {
    fireEvent.click(tasksButton());
  }
}
