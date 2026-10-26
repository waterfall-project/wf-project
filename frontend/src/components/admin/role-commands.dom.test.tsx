// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { NO_AUDIT } from "@/test/accounts";
import { atCommit, atFocus } from "@/test/committed";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { AccessRoleList, PermissionMatrix } from "./account-lists";
import { MatrixWrites } from "./permission-matrix";
import { ROLE_KEPT } from "./role-address";
import { RoleAnswers } from "./role-answers";

// The server of Next, as far as the table of the roles needs it: the fake back, the page read anew
// once a role is written, and the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/access-roles",
  useSearchParams: () => new URLSearchParams(),
}));

type Schemas = components["schemas"];

const CREATED = "POST /access-roles";
const WRITTEN = "PATCH /access-roles/{access_role_id}";
const roles = example("access_roles") as Schemas["AccessRole"][];
const permissions = example("permissions") as Schemas["Permission"][];

/** The table of the roles, for a session that may modify them, as the screen shares its address. */
function table(shown: readonly Schemas["AccessRole"][] = roles): ReactNode {
  return (
    <AccessRoleList
      roles={shown}
      query={{ sort: undefined, search: undefined, size: undefined }}
      preferences={undefined}
      filters={{
        predefined: undefined,
        holders: { min: undefined, max: undefined },
        audit: NO_AUDIT,
        authors: [],
      }}
      editable
    />
  );
}

/** A part of the screen of the roles, in French, sharing the address as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={ROLE_KEPT}>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** Serve the fake back, its answers held as the test says, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: () => Promise<unknown>): FakeClient {
  const client = fakeClient(answers, hold === undefined ? {} : { hold });
  server.client = client;
  return client;
}

/** The region of the table of the roles that says what its last command did, by its name. */
function told(): HTMLElement {
  return screen.getByRole("status", { name: "Commandes des rôles d’habilitation" });
}

/** The cell of the label of a role, made active for an entry. */
function labelCell(label: string): HTMLElement {
  const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
  const cell = within(grid).getByText(label).closest<HTMLElement>("[tabindex]");
  if (cell === null) {
    throw new Error(`no cell holds ${label}`);
  }
  return cell;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockReset();
});

describe("the creation of a role in line", () => {
  it("creates a role from its label alone, empties its field, says so and reads the page anew", async () => {
    const client = serve({ [CREATED]: { example: "access_role_created", status: 201 } });
    render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    // Whether the creation was still busy in the commit that told the role created: the request
    // over, never while it holds a press (#1484).
    const create = within(label.closest("form") ?? document.body).getByRole("button");
    const busyWhenTold = atCommit(
      document.body,
      () => told().textContent !== "",
      () => create.getAttribute("aria-busy"),
    );
    await userEvent.type(label, "CG{Enter}");
    await waitFor(() => {
      expect(told().textContent).toBe("« Contrôle de gestion » créé.");
    });
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(label).toHaveValue("");
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      [CREATED, { label: "CG", permissions: [] }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("keeps a label typed while the server answers the one sent", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [CREATED]: { example: "access_role_created", status: 201 } },
      () => new Promise((settle) => (answer = settle)),
    );
    render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "CG{Enter}D");
    answer();
    await waitFor(() => {
      expect(told().textContent).toBe("« Contrôle de gestion » créé.");
    });
    expect(label).toHaveValue("CGD");
  });

  it("refuses at its field a label left blank, as the entry of the grid does, and asks nothing", async () => {
    const client = serve({});
    render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "  {Enter}");
    expect(label).toHaveAttribute("aria-invalid", "true");
    expect(label).toHaveAccessibleDescription(CATALOGUES.fr.errors.VALUE_REQUIRED);
    expect(label).toHaveFocus();
    expect(client.calls).toEqual([]);
    expect(refresh).not.toHaveBeenCalled();
    expect(readMessages().messages).toEqual([]);
  });

  it("notes once, with the label sent, a label the server refuses at its field, which takes the focus described by its refusal [WF-IHM-0090-A]", async () => {
    serve({
      [CREATED]: {
        problem: {
          code: "VALIDATION_FAILED",
          status: 422,
          fields: [{ pointer: "/label", code: "VALUE_TOO_LONG" }],
        },
      },
    });
    render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "CG");
    // Described by its refusal as it takes the focus, never before the commit that says it (#1484).
    const focusing = atFocus(label);
    await userEvent.click(within(label.closest("form") ?? document.body).getByRole("button"));
    await waitFor(() => {
      expect(label).toHaveFocus();
    });
    expect(focusing.stop()).toEqual([CATALOGUES.fr.errors.VALUE_TOO_LONG]);
    expect(label).toHaveAccessibleDescription(CATALOGUES.fr.errors.VALUE_TOO_LONG);
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "refusal",
        sentence: "Les données saisies ne sont pas valides.",
        detail: CATALOGUES.fr.errors.VALUE_TOO_LONG,
        object: "CG",
      }),
    ]);
  });
});

/** The table and the matrix of the roles, sharing the roles answered, as the page renders them. */
function tableAndMatrix(shown: readonly Schemas["Permission"][]) {
  return (
    <RoleAnswers>
      {table()}
      <MatrixWrites order={permissions.map(({ code }) => code)} roles={roles}>
        <PermissionMatrix permissions={shown} roles={roles} editable />
      </MatrixWrites>
    </RoleAnswers>
  );
}

describe("the renaming of a role in its cell", () => {
  it("shows the label the server answered, before the page is read anew and over the role read older", async () => {
    const client = serve({ [WRITTEN]: "access_role_renamed" });
    const { rerender } = render(inFrench(table()));
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    const manager = roles.find((role) => role.label === "Manager");
    expect(client.calls.map(({ body }) => body)).toEqual([
      { label: "Resp", permissions: manager?.permissions, lock_version: manager?.lock_version },
    ]);
    // The answer shows, not what was typed; the page read anew with the role as it was read
    // before keeps it, by its counter.
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    await within(grid).findByText("Responsable d'équipe");
    rerender(inFrench(table([...roles])));
    expect(within(grid).getByText("Responsable d'équipe")).toBeInTheDocument();
    expect(within(grid).queryByText("Manager")).toBeNull();
  });

  it("writes the permissions of a role renamed, before the page is read anew, from the version the renaming answered", async () => {
    const client = serve({ [WRITTEN]: ["access_role_renamed", "access_role_updated"] });
    const order = permissions.map(({ code }) => code);
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    await userEvent.click(
      await screen.findByRole("checkbox", {
        name: "« Modifier la planification » pour « Responsable d'équipe »",
      }),
    );
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    const renamed = example("access_role_renamed") as Schemas["AccessRole"];
    expect(client.calls[1]?.body).toEqual({
      label: renamed.label,
      permissions: order.filter(
        (code) => code === "planning.write" || renamed.permissions.includes(code),
      ),
      lock_version: renamed.lock_version,
    });
  });
  it("names the column of a role renamed and each of its cells in the matrix by the label the server answered, before the page is read anew (#976) [WF-ADM-0010-A]", async () => {
    serve({ [WRITTEN]: "access_role_renamed" });
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    const matrix = screen.getByRole("table", { name: "Permissions par fonction" });
    expect(
      await within(matrix).findByRole("columnheader", { name: "Responsable d'équipe" }),
    ).toBeInTheDocument();
    expect(within(matrix).queryByRole("columnheader", { name: "Manager" })).toBeNull();
    expect(
      within(matrix).getByRole("checkbox", {
        name: "« Modifier la planification » pour « Responsable d'équipe »",
      }),
    ).toBeInTheDocument();
    expect(within(matrix).queryByRole("checkbox", { name: /Manager/ })).toBeNull();
    // The page not yet read anew: the answer of the renaming alone names the role so.
    expect(refresh).toHaveBeenCalledOnce();
  });
});
