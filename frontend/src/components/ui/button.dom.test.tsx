// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, buttonVariants } from "./button";
import { Input } from "./input";
import { NativeSelect } from "./native-select";

const VARIANTS = ["default", "outline", "ghost", "row"] as const;

/** The classes of a button of a variant, one by one. */
function classes(variant: (typeof VARIANTS)[number]): string[] {
  return buttonVariants({ variant }).split(/\s+/);
}

describe("buttonVariants", () => {
  it.each(VARIANTS)("draws a %s button as a pill #3079", (variant) => {
    expect(classes(variant)).toContain("rounded-full");
    expect(classes(variant)).not.toContain("rounded-md");
  });

  it.each(VARIANTS)(
    "gives a %s button marked aria-disabled the look of a disabled one #3125",
    (variant) => {
      const own = classes(variant);
      // Every look `disabled:` gives, `aria-disabled:` gives too; the pointer alone stays, for the
      // tooltip that says what the command lacks and the press that says it again.
      const looks = own
        .filter((each) => each.startsWith("disabled:"))
        .map((each) => each.slice("disabled:".length))
        .filter((look) => look !== "pointer-events-none");
      expect(looks).toContain("opacity-50");
      expect(own.filter((each) => each.startsWith("aria-disabled:"))).toEqual(
        expect.arrayContaining(looks.map((look) => `aria-disabled:${look}`)),
      );
      expect(own).toContain("aria-disabled:cursor-not-allowed");
      expect(own).not.toContain("aria-disabled:pointer-events-none");
    },
  );

  it("keeps a button marked aria-disabled pressable, its caller saying why it does not run #3125", async () => {
    const pressed = vi.fn();
    render(
      <Button type="button" aria-disabled onClick={pressed}>
        Mark
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Mark" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveClass("aria-disabled:opacity-50", "aria-disabled:cursor-not-allowed");
    await userEvent.click(button);
    expect(pressed).toHaveBeenCalledOnce();
  });

  it("draws the command of a row with the light border of the tables, its label in normal weight #3079", () => {
    render(
      <Button type="button" variant="row" size="sm">
        Modify
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Modify" });
    expect(button).toHaveClass("border", "border-border", "font-normal");
    expect(button).not.toHaveClass("border-input");
    expect(button).not.toHaveClass("font-medium");
    // A filled or an outlined command keeps the weight of a command.
    expect(classes("default")).toContain("font-medium");
    expect(classes("outline")).toEqual(expect.arrayContaining(["border-input", "font-medium"]));
  });

  it("lets a caller's class win over the shape, as every class of the charter #3079", () => {
    render(
      <Button type="button" className="rounded-sm">
        Square
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Square" });
    expect(button).toHaveClass("rounded-sm");
    expect(button).not.toHaveClass("rounded-full");
  });
});

describe("the fields of the charter", () => {
  it("draw a field and a list as pills, bordered by the token of a field #3079", () => {
    render(
      <>
        <Input aria-label="Label" />
        <NativeSelect aria-label="Category">
          <option value="a">A</option>
        </NativeSelect>
      </>,
    );
    for (const field of [
      screen.getByRole("textbox", { name: "Label" }),
      screen.getByRole("combobox", { name: "Category" }),
    ]) {
      expect(field).toHaveClass("rounded-full", "border-input");
    }
  });
});
