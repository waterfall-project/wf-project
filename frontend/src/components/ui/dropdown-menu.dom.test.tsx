// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./dropdown-menu";

function menu() {
  return render(
    <div>
      <button type="button">Elsewhere</button>
      <DropdownMenu>
        <DropdownMenuTrigger>Account</DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem>Profile</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>,
  );
}

describe("DropdownMenu, not modal", () => {
  it("closes on Escape and gives the focus back to its trigger [WF-IHM-0100-A]", async () => {
    menu();
    const trigger = screen.getByRole("button", { name: "Account" });
    trigger.focus();
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByRole("menu")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });

  it("closes on a click outside it, the rest of the page not hidden from a reader of the screen meanwhile [WF-IHM-0100-A]", async () => {
    menu();
    screen.getByRole("button", { name: "Account" }).focus();
    await userEvent.keyboard("{Enter}");
    await screen.findByRole("menu");
    // Not modal: the page is not hidden (`aria-hidden`) while the menu is open.
    expect(screen.getByRole("button", { name: "Elsewhere" })).toBeVisible();
    expect(document.body.querySelector("[aria-hidden='true']")).toBeNull();
    fireEvent.pointerDown(document.body);
    await waitFor(() => {
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });
});
