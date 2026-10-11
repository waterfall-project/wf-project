// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { ListPages } from "@/components/grid/list-pages";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { BACKUPS_LIST } from "./backup-address";
import {
  AlertList,
  BackupList,
  BackupScheduleFacts,
  ComponentList,
  OperationList,
  StorageFacts,
} from "./platform-lists";

// The address of the screen of the backups, which the links of its pages keep.
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const failed = example("system_status_backup_failed") as Schemas["SystemStatus"];
const backups = example("backups") as {
  items: Schemas["Backup"][];
  meta: Schemas["PaginationMeta"];
};
const suspended = example("backup_schedule_disabled") as Schemas["BackupSchedule"];

/** Render in a language. */
function rendered(children: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {children}
    </NextIntlClientProvider>,
  );
}

describe("the pages of a list of the administration", () => {
  it("break no rule of accessibility, the links of the pages keeping the rest of the address", async () => {
    page.search = "include_inactive=true&offset=2";
    const { container } = rendered(
      <ListPages
        list={BACKUPS_LIST}
        texts="admin.pages"
        page={{ limit: 2, offset: 2, total: 5 }}
        shown={2}
      />,
    );
    expect(screen.getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/admin/backups?include_inactive=true",
    );
    expect(screen.getByRole("link", { name: /Page suivante/ })).toHaveAttribute(
      "href",
      "/admin/backups?include_inactive=true&offset=4",
    );
    await expectAccessible(container);
  });

  it("lead back to the last page from a page asked beyond the end", () => {
    page.search = "offset=8";
    rendered(
      <ListPages
        list={BACKUPS_LIST}
        texts="admin.pages"
        page={{ limit: 2, offset: 8, total: 5 }}
        shown={0}
      />,
    );
    expect(screen.getByText("Cette page est au-delà de la fin de la liste.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/admin/backups?offset=4",
    );
  });
});

describe("the state of the platform and its backups", () => {
  it("break no rule of accessibility, and show each instant in the local time", async () => {
    const { container } = rendered(
      <>
        <AlertList alerts={failed.alerts} />
        <ComponentList components={failed.components} />
        <StorageFacts storage={failed.storage} />
        <OperationList status={failed} />
        <BackupScheduleFacts schedule={suspended} />
        <BackupList backups={backups.items} page={backups.meta} />
      </>,
    );
    const alerts = screen.getByRole("table", { name: "Alertes en cours" });
    expect(
      within(alerts)
        .getAllByRole("row")
        .slice(1)
        .map((row) => row.firstElementChild?.textContent),
    ).toEqual(["Alerte", "Alerte"]);
    const operations = screen.getByRole("table", { name: "Dernières opérations" });
    expect(
      within(operations)
        .getByRole("row", { name: /^Sauvegarde/ })
        .querySelector("time"),
    ).toHaveAttribute("datetime", "2026-06-03T01:00:00Z");
    expect(screen.getByText("Désactivée")).toBeInTheDocument();
    expect(screen.getByText("7 sauvegardes conservées")).toBeInTheDocument();
    expect(screen.queryByText("Fréquence")).toBeNull();
    // A schedule suspended keeps its copy set, as it keeps its retention.
    expect(
      screen.getByText("Vers secours-lyon, dossier waterfall/sauvegardes — 30 copies gardées"),
    ).toBeInTheDocument();
    await expectAccessible(container);
  });
});
