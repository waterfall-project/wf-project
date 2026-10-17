// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { PermissionMatrix } from "./account-lists";
import { MatrixWrites } from "./permission-matrix";

// The server of Next, as far as the matrix needs it: the fake back, the page read anew once a role
// is written, and the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/access-roles",
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const ROLE = "PATCH /access-roles/{access_role_id}";
const roles = example("access_roles") as Schemas["AccessRole"][];
const permissions = example("permissions") as Schemas["Permission"][];
const LAST_ADMINISTRATOR = example("access_role_update_refused") as Problem & { status: 409 };
const STALE = { code: "STALE_LOCK_VERSION", status: 412 } as const;

/** The role of the example by its label. */
function roleNamed(label: string): Schemas["AccessRole"] {
  const found = roles.find((role) => role.label === label);
  if (found === undefined) {
    throw new Error(`the example holds ${label}`);
  }
  return found;
}

/** The codes of the catalogue a role holds, a code added, in the order of the catalogue. */
function withCode(role: Schemas["AccessRole"], code: string): string[] {
  return ORDER.filter((each) => each === code || role.permissions.includes(each));
}

/** Every code of the catalogue, in its order: what a write sends, whatever rows the matrix shows. */
const ORDER = permissions.map((permission) => permission.code);

/**
 * The permissions of the catalogue whose codes are given, in its order: a window of the matrix, so
 * that a test renders a few rows and not the fifty-one of the catalogue, each with a cell for each of
 * the seven roles (défaut n° 23 de `typescript.md`).
 */
function windowOf(...codes: string[]): Schemas["Permission"][] {
  return permissions.filter((permission) => codes.includes(permission.code));
}

/** The matrix as a session that may modify the roles has it: its cells within its writes. */
function Written({
  permissions: shown,
  roles: retained,
}: {
  readonly permissions: readonly Schemas["Permission"][];
  readonly roles: readonly Schemas["AccessRole"][];
}) {
  return (
    <MatrixWrites order={ORDER} roles={retained}>
      <PermissionMatrix permissions={shown} roles={retained} editable />
    </MatrixWrites>
  );
}

/** Render in a language. */
function rendered(children: ReactNode, locale: Locale = "fr") {
  return render(inLanguage(children, locale));
}

/** A part of the screen in a language. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** Serve the fake back, its answers held as the test says, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: () => Promise<unknown>): FakeClient {
  const client = fakeClient(answers, hold === undefined ? {} : { hold });
  server.client = client;
  return client;
}

/**
 * The checkbox of a permission for a role, found in the row the permission heads: the name of a
 * row is that of all its cells (EP-02/L46).
 */
function cell(permission: string, role: string): HTMLElement {
  const row = screen.getByRole("rowheader", { name: permission }).closest("tr");
  if (row === null) {
    throw new Error(`${permission} heads no row`);
  }
  return within(row).getByRole("checkbox", {
    name: `«\u00a0${permission}\u00a0» pour «\u00a0${role}\u00a0»`,
  });
}

/** The body of the write the fake back received, by its rank. */
function sent(client: FakeClient, rank: number): Schemas["AccessRoleUpdate"] {
  return client.calls[rank]?.body as Schemas["AccessRoleUpdate"];
}

beforeEach(() => {
  page.search = "";
  refresh.mockReset();
});

describe("the matrix of the permissions", () => {
  it("is a table whose rows a reader finds by their permission, under their function, and whose cells say whether each role holds it", () => {
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable={false} />);
    const matrix = screen.getByRole("table", { name: "Permissions par fonction" });
    // The row is found by its header, the permission: the name of a row is that of all its cells,
    // and computing it for the sixty rows took a second under load (EP-02/L46).
    const restore = within(matrix)
      .getByRole("rowheader", { name: "Restaurer la plateforme" })
      .closest("tr");
    if (restore === null) {
      throw new Error("the permission heads no row");
    }
    expect(
      within(restore)
        .getAllByRole("cell")
        .map((each) => each.textContent),
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
    // Read only: nothing to check.
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("breaks no rule of accessibility, each kind of group of rows rendered, read or written", async () => {
    // A function of one permission, one of two, and the actions outside any function: every
    // shape of row and of group the matrix draws. The rules of axe hold for each row alike, and
    // the sixty rows took longer to check than the test may last under load (EP-02/L46).
    const shapes = permissions.filter((permission) =>
      [null, "FBS-1.2", "FBS-1.5"].includes(permission.fbs_code ?? null),
    );
    const read = rendered(<PermissionMatrix permissions={shapes} roles={roles} editable={false} />);
    expect(read.container.querySelectorAll('th[scope="rowgroup"]')).toHaveLength(4);
    await expectAccessible(read.container);
    read.unmount();
    const written = rendered(<Written permissions={shapes} roles={roles} />);
    await expectAccessible(written.container);
  });

  it("speaks English in English", () => {
    rendered(<Written permissions={windowOf("platform_restore")} roles={roles} />, "en");
    expect(screen.getByRole("rowheader", { name: "Irreversible action" })).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: "“Restore the platform” for “Administrateur”" }),
    ).toBeChecked();
  });

  it("has a column for each role the table retains, in its order, and none for another", () => {
    const retained = [roleNamed("Manager"), roleNamed("Auditeur")];
    rendered(<PermissionMatrix permissions={permissions} roles={retained} editable={false} />);
    const matrix = screen.getByRole("table", { name: "Permissions par fonction" });
    expect(
      within(matrix)
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual(["Fonction", "Permission", "Manager", "Auditeur"]);
  });
});

describe("the matrix of the permissions, where they are modified", () => {
  it("composes a role of the permissions of two actors: a manager given the modification of the planning, the role written whole from the version read [WF-ADM-0020-A]", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    const client = serve(
      { [ROLE]: "access_role_updated" },
      () => new Promise((settle) => (answer = settle)),
    );
    rendered(
      <Written
        permissions={windowOf("planning.write", "risks.write", "all_projects_read")}
        roles={roles}
      />,
    );
    const planning = cell("Modifier la planification", "Manager");
    expect(planning).not.toBeChecked();
    expect(cell("Consulter tous les projets", "Manager")).toBeChecked();

    await userEvent.click(planning);
    const manager = roleNamed("Manager");
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.path).toBe(`/access-roles/${manager.access_role_id}`);
    // The role whole, every permission of the catalogue it holds, whatever rows the matrix shows.
    expect(sent(client, 0)).toEqual({
      label: "Manager",
      permissions: withCode(manager, "planning.write"),
      lock_version: manager.lock_version,
    });
    // What was asked shows until the server answers, and the other cells of the role wait for it.
    expect(planning).toBeChecked();
    const other = cell("Modifier la gestion des risques", "Manager");
    expect(other).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(other);
    expect(client.calls).toHaveLength(1);
    // The cells of another role do not.
    expect(cell("Modifier la gestion des risques", "Chiffreur")).not.toHaveAttribute(
      "aria-disabled",
    );
    // Answered: the manager holds the permissions of both actors, its other cells are available
    // again, and the page is read anew.
    answer();
    await waitFor(() => {
      expect(other).not.toHaveAttribute("aria-disabled");
    });
    expect(planning).toBeChecked();
    expect(cell("Consulter tous les projets", "Manager")).toBeChecked();
    expect(other).not.toBeChecked();
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps each irreversible or structuring action a cell of its own, written alone: the modification of the estimate without the marking, the marking without the merge, nor the creation of a project [WF-ADM-0100-A]", async () => {
    const client = serve({ [ROLE]: "access_role_marking_granted" });
    rendered(
      <Written
        permissions={windowOf(
          "estimate.write",
          "revision_mark",
          "structure_merge",
          "project_create",
        )}
        roles={roles}
      />,
    );
    // The estimator modifies the estimate and marks no revision, merges no differential, creates no
    // project: four cells, one checked.
    expect(cell("Modifier le chiffrage et le devis", "Chiffreur")).toBeChecked();
    const marking = cell("Marquer une révision", "Chiffreur");
    expect(marking).not.toBeChecked();
    expect(cell("Fusionner un différentiel", "Chiffreur")).not.toBeChecked();
    expect(cell("Créer un projet", "Chiffreur")).not.toBeChecked();

    await userEvent.click(marking);
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    const asked = sent(client, 0).permissions;
    expect(asked).toEqual(withCode(roleNamed("Chiffreur"), "revision_mark"));
    expect(asked).toContain("estimate.write");
    expect(asked).not.toContain("structure_merge");
    expect(asked).not.toContain("project_create");
    // Answered: the marking granted alone, the merge and the creation of a project still refused.
    await waitFor(() => {
      expect(marking).not.toHaveAttribute("aria-disabled");
    });
    expect(marking).toBeChecked();
    expect(cell("Modifier le chiffrage et le devis", "Chiffreur")).toBeChecked();
    expect(cell("Fusionner un différentiel", "Chiffreur")).not.toBeChecked();
    expect(cell("Créer un projet", "Chiffreur")).not.toBeChecked();
  });

  it("writes a second cell of a role, before the page is read anew, from the version and the permissions the first answered", async () => {
    const client = serve({ [ROLE]: "access_role_updated" });
    rendered(<Written permissions={windowOf("planning.write", "risks.write")} roles={roles} />);
    await userEvent.click(cell("Modifier la planification", "Manager"));
    const risks = cell("Modifier la gestion des risques", "Manager");
    await waitFor(() => {
      expect(risks).not.toHaveAttribute("aria-disabled");
    });
    await userEvent.click(risks);
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    const first = example("access_role_updated") as Schemas["AccessRole"];
    expect(sent(client, 1)).toEqual({
      label: "Manager",
      permissions: withCode(first, "risks.write"),
      lock_version: first.lock_version,
    });
  });

  it("keeps the role answered over the same role read older, and takes the one read newer", async () => {
    serve({ [ROLE]: "access_role_updated" });
    const shown = windowOf("planning.write");
    const { rerender } = rendered(<Written permissions={shown} roles={roles} />);
    const planning = cell("Modifier la planification", "Manager");
    await userEvent.click(planning);
    await waitFor(() => {
      expect(planning).not.toHaveAttribute("aria-disabled");
    });
    // The page read anew before it holds the write: the answer prevails, by its counter.
    rerender(inLanguage(<Written permissions={shown} roles={[...roles]} />));
    expect(planning).toBeChecked();
    // A reading newer than the answer — the role written since, elsewhere — prevails over it.
    const manager = roleNamed("Manager");
    const since = roles.map((role) => (role === manager ? { ...manager, lock_version: 3 } : role));
    rerender(inLanguage(<Written permissions={shown} roles={since} />));
    expect(planning).not.toBeChecked();
  });

  it("tells the last administrator the server refuses to deprive by the catalogue, shows the role as it was, and gives the focus back to the cell once the refusal is dismissed", async () => {
    const client = serve({ [ROLE]: { problem: LAST_ADMINISTRATOR } });
    rendered(<Written permissions={windowOf("users.write", "access_roles.write")} roles={roles} />);
    const users = cell("Modifier les utilisateurs", "Direction de projet");
    await userEvent.click(users);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(CATALOGUES.fr.errors.LAST_ADMINISTRATOR);
    expect(users).toBeChecked();
    expect(users).not.toHaveAttribute("aria-disabled");
    const asked = sent(client, 0).permissions;
    expect(asked).not.toContain("users.write");
    expect(asked).toContain("access_roles.write");
    expect(refresh).not.toHaveBeenCalled();
    await userEvent.click(within(alert).getByRole("button", { name: /Fermer l’avis/ }));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(users).toHaveFocus();
  });

  it("offers to read the page anew when the role changed since it was read", async () => {
    serve({ [ROLE]: { problem: STALE } });
    rendered(<Written permissions={windowOf("audit_log.read")} roles={roles} />);
    await userEvent.click(cell("Consulter le journal d’audit", "Manager"));
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("button", { name: /Recharger/ })).toBeInTheDocument();
  });

  it("tells a refusal only on the reading it was asked from", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [ROLE]: { problem: LAST_ADMINISTRATOR } },
      () => new Promise((settle) => (answer = settle)),
    );
    const shown = windowOf("users.write");
    const { rerender } = rendered(<Written permissions={shown} roles={roles} />);
    await userEvent.click(cell("Modifier les utilisateurs", "Direction de projet"));
    // The table searched meanwhile: the refusal says nothing of the reading now shown.
    page.search = "search=Direction";
    rerender(
      inLanguage(<Written permissions={shown} roles={[roleNamed("Direction de projet")]} />),
    );
    const users = cell("Modifier les utilisateurs", "Direction de projet");
    expect(users).toHaveAttribute("aria-busy", "true");
    answer();
    await waitFor(() => {
      expect(users).toHaveAttribute("aria-busy", "false");
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(users).toBeChecked();
  });
});
