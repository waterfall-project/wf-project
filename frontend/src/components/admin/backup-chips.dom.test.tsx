// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { NEWEST_FIRST, readBackupFilters } from "./backup-address";
import { BackupList } from "./platform-lists";

// The filters of the backups folded into the bar of their table (#2916, WF-IHM-0130, WF-IHM-0060):
// the chips told from the address, each lifted by the parameters it says, and the panel.
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const backups = example("backups") as {
  items: components["schemas"]["Backup"][];
  meta: components["schemas"]["PaginationMeta"];
};

function list() {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <BackupList
          read={{ kind: "read", items: backups.items, page: backups.meta }}
          filters={readBackupFilters(new URLSearchParams(page.search))}
          query={{ sort: NEWEST_FIRST, search: undefined, size: undefined }}
          preferences={undefined}
          startable={false}
          refused={undefined}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

let zone: string | undefined;
beforeEach(() => {
  zone = process.env.TZ;
  process.env.TZ = "UTC";
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.search = "";
});
afterEach(() => {
  if (zone === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = zone;
  }
  vi.restoreAllMocks();
  router.push.mockClear();
});

const FROM = "2026-03-01T00:00:00.000Z";
const TO = "2026-03-06T00:00:00.000Z";

const CASES = [
  {
    name: "the period between two days",
    search: `from=${FROM}&to=${TO}`,
    chip: "Date : du 1 mars 2026 au 5 mars 2026",
    lifts: ["from", "to"],
  },
  {
    name: "the origins",
    search: "origins=manual",
    chip: "Déclenchement : Manuelle",
    lifts: ["origins"],
  },
  {
    name: "the verifications",
    search: "verifications=passed%2Cfailed",
    chip: "Vérification : Vérifiée, Vérification échouée",
    lifts: ["verifications"],
  },
  {
    name: "the marking",
    search: "is_retained=true",
    chip: "Conservation : Marquées à conserver",
    lifts: ["is_retained"],
  },
  {
    name: "the bounds of the size, both",
    search: "size_bytes_min=1024&size_bytes_max=2097152",
    chip: "Taille : de 1 kilooctet à 2 mégaoctets",
    lifts: ["size_bytes_min", "size_bytes_max"],
  },
  {
    name: "the least size",
    search: "size_bytes_min=1024",
    chip: "Taille : 1 kilooctet au moins",
    lifts: ["size_bytes_min"],
  },
] as const;

describe("the chips of the filters of the backups", () => {
  it.each(CASES)(
    "tell $name, and lift it by the parameters of the address that say it [WF-IHM-0130-A]",
    async ({ search, chip, lifts }) => {
      page.search = `sort_by=taken_at&${search}`;
      render(list());
      const cross = screen.getByRole("button", {
        name: (name) => name.replace(/\s/g, " ") === `Retirer le filtre ${chip}`,
      });
      await userEvent.click(cross);
      const rest = new URLSearchParams(page.search);
      for (const name of lifts) {
        rest.delete(name);
      }
      expect(router.push.mock.calls.at(-1)?.[0]).toBe(`/admin/backups?${rest.toString()}`);
    },
  );

  it("fold the filters into a panel closed until « Filtres » opens it [WF-IHM-0130-A]", async () => {
    render(list());
    const toggle = screen.getByRole("button", { name: /^Filtres/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("group", { name: "Filtres" })).toBeVisible();
  });

  it("clear every filter at once, the sort kept [WF-IHM-0130-A]", async () => {
    page.search = "sort_by=taken_at&origins=manual&is_retained=false";
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    expect(router.push.mock.calls.at(-1)?.[0]).toBe("/admin/backups?sort_by=taken_at");
  });
});
