// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { PermissionMatrix } from "./account-lists";
import { AdminListPages } from "./list-pages";
import {
  AlertList,
  BackupList,
  BackupScheduleFacts,
  ComponentList,
  OperationList,
  StorageFacts,
} from "./platform-lists";

type Schemas = components["schemas"];

const roles = example("access_roles") as Schemas["AccessRole"][];
const permissions = example("permissions") as Schemas["Permission"][];
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

describe("the matrix of the permissions", () => {
  it("is a table whose rows a reader finds by their permission, under their function, and whose cells say whether each role holds it", async () => {
    const { container } = rendered(<PermissionMatrix permissions={permissions} roles={roles} />);
    const matrix = screen.getByRole("table", { name: "Permissions par fonction" });
    const restore = within(matrix).getByRole("row", { name: /^Restaurer la plateforme/ });
    expect(
      within(restore)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual([
      "Accordée",
      "Non accordée",
      "Non accordée",
      "Non accordée",
      "Accordée",
      "Non accordée",
      "Non accordée",
    ]);
    // Each of the twenty-five functions heads its group by its name alone: no code of the FBS is
    // shown to the user (decision of the author on #515) — the journal of audit, FBS-1.5, too.
    expect(within(matrix).getByRole("rowheader", { name: "Journal d’audit" })).toBeInTheDocument();
    expect(
      within(matrix).getByRole("rowheader", { name: "Gestion des rôles d’habilitation" }),
    ).toHaveAttribute("rowspan", "2");
    // Twenty-five functions, the journal of audit among them, and the irreversible and the
    // structuring actions.
    expect(matrix.querySelectorAll('th[scope="rowgroup"]')).toHaveLength(27);
    expect(matrix.textContent).not.toContain("FBS-");
    await expectAccessible(container);
  });

  it("speaks English in English", () => {
    rendered(<PermissionMatrix permissions={permissions} roles={roles} />, "en");
    expect(screen.getByRole("rowheader", { name: "Irreversible action" })).toHaveAttribute(
      "rowspan",
      "8",
    );
  });
});

describe("the pages of a list of the administration", () => {
  it("break no rule of accessibility, the links of the pages keeping the rest of the address", async () => {
    const { container } = rendered(
      <AdminListPages
        path="/admin/backups"
        query={new URLSearchParams("include_inactive=true&offset=2")}
        page={{ limit: 2, offset: 2, total: 5 }}
        shown={2}
        count="5"
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
    rendered(
      <AdminListPages
        path="/admin/backups"
        query={new URLSearchParams("offset=8")}
        page={{ limit: 2, offset: 8, total: 5 }}
        shown={0}
        count="5"
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
