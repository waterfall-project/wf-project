// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "./alert-dialog";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./dialog";

describe("DialogContent", () => {
  it("scrolls to what takes the focus, a field a dialog taller than its box holds out of sight [WF-IHM-0100-A]", async () => {
    // jsdom lays nothing out and scrolls nothing: the call is what is held.
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(() => {
      /* nothing to scroll in jsdom */
    });
    try {
      render(
        <Dialog open>
          <DialogContent>
            <DialogTitle>Long form</DialogTitle>
            <DialogDescription>Taller than its box.</DialogDescription>
            <input aria-label="First field" />
            <input aria-label="Last field" />
          </DialogContent>
        </Dialog>,
      );
      const last = await screen.findByRole("textbox", { name: "Last field" });
      scroll.mockClear();
      last.focus();
      expect(scroll).toHaveBeenCalledTimes(1);
      expect(scroll.mock.contexts[0]).toBe(last);
      expect(scroll).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
      // Moved by the keyboard too: Tab onto the next stop scrolls to it.
      scroll.mockClear();
      await userEvent.tab();
      expect(scroll).toHaveBeenCalled();
      expect(scroll.mock.contexts[0]).toBe(document.activeElement);
    } finally {
      scroll.mockRestore();
    }
  });
});

describe("AlertDialogContent", () => {
  it("says it is modal [WF-IHM-0100-A]", async () => {
    render(
      <AlertDialog open>
        <AlertDialogContent>
          <AlertDialogTitle>Sure?</AlertDialogTitle>
          <AlertDialogDescription>Irreversible.</AlertDialogDescription>
        </AlertDialogContent>
      </AlertDialog>,
    );
    expect(await screen.findByRole("alertdialog")).toHaveAttribute("aria-modal", "true");
  });
});
