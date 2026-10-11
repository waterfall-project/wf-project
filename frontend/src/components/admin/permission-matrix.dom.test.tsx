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

import { PermissionMatrix } from "./permission-matrix";

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
  return permissions
    .map((permission) => permission.code)
    .filter((each) => each === code || role.permissions.includes(each));
}

/** Render in a language. */
function rendered(children: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {children}
    </NextIntlClientProvider>,
  );
}

/** Serve the fake back, its answers held as the test says, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: () => Promise<unknown>): FakeClient {
  const client = fakeClient(answers, hold === undefined ? {} : { hold });
  server.client = client;
  return client;
}

/** The checkbox of a permission for a role, as a reader finds it. */
function cell(permission: string, role: string): HTMLElement {
  return screen.getByRole("checkbox", {
    name: `«\u00a0${permission}\u00a0» pour «\u00a0${role}\u00a0»`,
  });
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
    const written = rendered(<PermissionMatrix permissions={shapes} roles={roles} editable />);
    await expectAccessible(written.container);
  });

  it("speaks English in English", () => {
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable />, "en");
    expect(screen.getByRole("rowheader", { name: "Irreversible action" })).toHaveAttribute(
      "rowspan",
      "8",
    );
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
      { [ROLE]: { problem: STALE } },
      () => new Promise((settle) => (answer = settle)),
    );
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable />);
    const planning = cell("Modifier la planification", "Manager");
    expect(planning).not.toBeChecked();
    expect(cell("Consulter tous les projets", "Manager")).toBeChecked();

    await userEvent.click(planning);
    const manager = roleNamed("Manager");
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.path).toBe(`/access-roles/${manager.access_role_id}`);
    expect(client.calls[0]?.body).toEqual({
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
    answer();
    await screen.findByRole("alert");
  });

  it("keeps each irreversible or structuring action a cell of its own, written alone: the modification of the estimate without the marking, the marking without the merge, nor the creation of a project [WF-ADM-0100-A]", async () => {
    const client = serve({ [ROLE]: { problem: STALE } });
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable />);
    // The estimator modifies the estimate and marks no revision, merges no differential, creates no
    // project: four cells, one checked.
    expect(cell("Modifier le chiffrage et le devis", "Chiffreur")).toBeChecked();
    expect(cell("Marquer une révision", "Chiffreur")).not.toBeChecked();
    expect(cell("Fusionner un différentiel", "Chiffreur")).not.toBeChecked();
    expect(cell("Créer un projet", "Chiffreur")).not.toBeChecked();

    await userEvent.click(cell("Marquer une révision", "Chiffreur"));
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    const sent = (client.calls[0]?.body as { permissions: string[] }).permissions;
    expect(sent).toEqual(withCode(roleNamed("Chiffreur"), "revision_mark"));
    expect(sent).toContain("estimate.write");
    expect(sent).not.toContain("structure_merge");
    expect(sent).not.toContain("project_create");
  });

  it("tells the last administrator the server refuses to deprive by the catalogue, and shows the role as it was", async () => {
    const client = serve({ [ROLE]: { problem: LAST_ADMINISTRATOR } });
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable />);
    const users = cell("Modifier les utilisateurs", "Direction de projet");
    await userEvent.click(users);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(CATALOGUES.fr.errors.LAST_ADMINISTRATOR);
    expect(users).toBeChecked();
    expect(users).not.toHaveAttribute("aria-disabled");
    const sent = (client.calls[0]?.body as { permissions: string[] }).permissions;
    expect(sent).not.toContain("users.write");
    expect(sent).toContain("access_roles.write");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("offers to read the page anew when the role changed since it was read", async () => {
    serve({ [ROLE]: { problem: STALE } });
    rendered(<PermissionMatrix permissions={permissions} roles={roles} editable />);
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
    const { rerender } = rendered(
      <PermissionMatrix permissions={permissions} roles={roles} editable />,
    );
    await userEvent.click(cell("Modifier les utilisateurs", "Direction de projet"));
    // The table searched meanwhile: the refusal says nothing of the reading now shown.
    page.search = "search=Direction";
    rerender(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PermissionMatrix
          permissions={permissions}
          roles={[roleNamed("Direction de projet")]}
          editable
        />
      </NextIntlClientProvider>,
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
