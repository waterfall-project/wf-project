// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { Shell } from "./shell";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const { permissions } = example("session") as components["schemas"]["Session"];

describe("the shell", () => {
  it.each([
    ["fr", "Appliquer la langue", "Appliquer le mode"],
    ["en", "Apply language", "Apply display mode"],
  ] as const)(
    "names each of its two apply buttons for what it applies, in %s",
    async (locale, language, theme) => {
      const { container } = render(
        <Shell
          locale={locale}
          preference="default"
          theme="default"
          permissions={permissions}
          remembered={undefined}
        >
          <main />
        </Shell>,
      );
      const header = within(screen.getByRole("banner"));
      expect(header.getAllByRole("button").map((button) => button.textContent)).toEqual([
        language,
        theme,
      ]);
      expect(header.getByRole("button", { name: language }).closest("form")).toContainElement(
        header.getAllByRole("combobox")[0] ?? null,
      );
      expect(header.getByRole("button", { name: theme }).closest("form")).toContainElement(
        header.getAllByRole("combobox")[1] ?? null,
      );
      await expectAccessible(container);
    },
  );
});
