// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { holdRoute, NO_AUDIT } from "@/test/accounts";
import { atCommit, atFocus } from "@/test/committed";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
} from "@/test/fixtures";
import { dismissLeftRefusals, refusedLeft } from "@/navigation/held-writes";
import { heldLink } from "@/test/held-link";

import { AccessRoleList, PermissionMatrix } from "./account-lists";
import { MatrixWrites } from "./permission-matrix";
import { ROLE_KEPT } from "./role-address";
import { RoleAnswers } from "./role-answers";

// The server of Next, as far as the table of the roles needs it: the fake back, the page read anew
// once a role is written, and the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/access-roles",
  useSearchParams: () => new URLSearchParams(page.search),
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
function serve(answers: FakeAnswers, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(answers, timing);
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
  page.search = "";
  dismissLeftRefusals();
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
      expect(told().textContent).toBe("«\u00A0Contrôle de gestion\u00A0» créé.");
    });
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(label).toHaveValue("");
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      [CREATED, { label: "CG", permissions: [] }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("keeps a label typed while the server answers the one sent", async () => {
    const answer = held();
    serve({ [CREATED]: { example: "access_role_created", status: 201 } }, answer.timing);
    render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "CG{Enter}D");
    answer.release();
    await waitFor(() => {
      expect(told().textContent).toBe("«\u00A0Contrôle de gestion\u00A0» créé.");
    });
    expect(label).toHaveValue("CGD");
  });

  it("holds a link clicked while the creation answers, and does not follow it when the server refuses it: the refusal is told above the table (#688, #889)", async () => {
    const answer = held();
    serve({ [CREATED]: { problem: { code: "PERMISSION_MISSING", status: 403 } } }, answer.timing);
    render(inFrench(table()));
    const link = heldLink();
    try {
      await userEvent.type(screen.getByRole("textbox", { name: "Nouveau rôle" }), "CG{Enter}");
      link.click();
      await act(async () => {
        answer.release();
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      expect(await screen.findByRole("alert")).toHaveTextContent(
        CATALOGUES.fr.errors.PERMISSION_MISSING,
      );
      expect(link.followed).not.toHaveBeenCalled();
    } finally {
      link.remove();
    }
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

  it("notes once, with the label sent, a label the server refuses at its field, which takes the focus described by its refusal", async () => {
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

  it("tells a label refused at its field by the field alone, the list read anew meanwhile: the bar of the shell does not tell it too (#1476)", async () => {
    const answer = held();
    serve(
      {
        "PATCH /me/preferences": "preferences",
        [CREATED]: {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields: [{ pointer: "/label", code: "VALUE_TOO_LONG" }],
          },
        },
      },
      answer.timing,
    );
    const { rerender } = render(inFrench(table()));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "CG{Enter}");
    // The list searched meanwhile: it tells nothing of the reading now shown.
    page.search = "search=Manager";
    rerender(inFrench(table()));
    answer.release();
    await waitFor(() => {
      expect(label).toHaveAccessibleDescription(CATALOGUES.fr.errors.VALUE_TOO_LONG);
    });
    expect(refusedLeft()).toEqual([]);
    expect(readMessages().messages).toHaveLength(1);
  });

  it("tells a label refused at its field by the bar of the shell when the form is gone before the answer [#1896]", async () => {
    const answer = held();
    serve(
      {
        [CREATED]: {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields: [{ pointer: "/label", code: "VALUE_TOO_LONG" }],
          },
        },
      },
      answer.timing,
    );
    const { unmount } = render(inFrench(table()));
    await userEvent.type(screen.getByRole("textbox", { name: "Nouveau rôle" }), "CG{Enter}");
    // The form is unmounted while the write answers: no field is left to tell the refusal.
    unmount();
    await act(async () => {
      answer.release();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    const left = refusedLeft();
    expect(left).toHaveLength(1);
    expect(left[0]?.refusal).toMatchObject({ problem: { fields: [{ pointer: "/label" }] } });
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
        name: "«\u00A0Modifier la planification\u00A0» pour «\u00A0Responsable d'équipe\u00A0»",
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

  it("renames a role whose permission was checked from the version and permissions the write answered, the source shared the other way too (#847)", async () => {
    const client = serve({ [WRITTEN]: ["access_role_updated", "access_role_renamed"] });
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    await userEvent.click(
      await screen.findByRole("checkbox", {
        name: "«\u00a0Modifier la planification\u00a0» pour «\u00a0Manager\u00a0»",
      }),
    );
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    // The renaming leaves from the role the checking answered, not from the role read.
    const checked = example("access_role_updated") as Schemas["AccessRole"];
    const manager = roles.find((role) => role.label === "Manager");
    expect(checked.lock_version).toBeGreaterThan(manager?.lock_version ?? 0);
    expect(client.calls[1]?.body).toEqual({
      label: "Resp",
      permissions: checked.permissions,
      lock_version: checked.lock_version,
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
        name: "«\u00A0Modifier la planification\u00A0» pour «\u00A0Responsable d'équipe\u00A0»",
      }),
    ).toBeInTheDocument();
    expect(within(matrix).queryByRole("checkbox", { name: /Manager/ })).toBeNull();
    // The page not yet read anew: the answer of the renaming alone names the role so.
    expect(refresh).toHaveBeenCalledOnce();
  });
});

describe("the writes of a same role, one at a time (#2261)", () => {
  const DELETED = "DELETE /access-roles/{access_role_id}";
  const planning = "«\u00A0Modifier la planification\u00A0» pour «\u00A0";

  /** The matrix cell of the planning for a role, by the label the screen shows it under. */
  function cell(label: string): HTMLElement {
    return screen.getByRole("checkbox", { name: `${planning}${label}\u00A0»` });
  }

  /** The label of a role in the table, in its cell. */
  function label(name: string): HTMLElement {
    return within(screen.getByRole("grid", { name: "Rôles d’habilitation" })).getByText(name);
  }

  it("marks the label, the cells and the deletion of a role busy while a cell of it is written, sends no renaming, and renames from the version the cell answered, without a 412 [WF-ADM-0010-A]", async () => {
    const hold = holdRoute(WRITTEN);
    const client = serve(
      { [WRITTEN]: ["access_role_updated", "access_role_renamed"] },
      hold.timing,
    );
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    await userEvent.click(await screen.findByRole("checkbox", { name: /Manager/ }));
    await waitFor(() => {
      expect(label("Manager")).toHaveAttribute("aria-busy", "true");
    });
    expect(label("Manager")).toHaveAttribute("aria-disabled", "true");
    expect(cell("Manager")).toHaveAttribute("aria-busy", "true");
    expect(cell("Manager")).toHaveAttribute("aria-disabled", "true");
    // Another role is free, and a renaming of the busy one starts no entry.
    expect(cell("Chiffreur")).toHaveAttribute("aria-busy", "false");
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    expect(client.calls).toHaveLength(1);
    hold.release();
    await waitFor(() => {
      expect(label("Manager")).toHaveAttribute("aria-busy", "false");
    });
    expect(cell("Manager")).not.toHaveAttribute("aria-disabled");
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    const checked = example("access_role_updated") as Schemas["AccessRole"];
    expect(client.calls[1]?.body).toEqual({
      label: "Resp",
      permissions: checked.permissions,
      lock_version: checked.lock_version,
    });
  });

  it("marks the cells of a role busy while its renaming is written, a press sending nothing, and writes a cell from the version the renaming answered [WF-ADM-0010-A]", async () => {
    const hold = holdRoute(WRITTEN);
    const client = serve(
      { [WRITTEN]: ["access_role_renamed", "access_role_updated"] },
      hold.timing,
    );
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(cell("Manager")).toHaveAttribute("aria-busy", "true");
    });
    // The cell shows what was typed until the server answers.
    expect(label("Resp")).toHaveAttribute("aria-busy", "true");
    await userEvent.click(cell("Manager"));
    expect(client.calls).toHaveLength(1);
    hold.release();
    await waitFor(() => {
      expect(cell("Responsable d'équipe")).toHaveAttribute("aria-busy", "false");
    });
    await userEvent.click(cell("Responsable d'équipe"));
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    const renamed = example("access_role_renamed") as Schemas["AccessRole"];
    expect(client.calls[1]?.body).toMatchObject({
      label: renamed.label,
      lock_version: renamed.lock_version,
    });
  });

  it("marks the label, the cells and the deletion of a role busy while its confirmed deletion is written, a press sending nothing, and frees them once it answers [WF-ADM-0010-A]", async () => {
    const hold = holdRoute(DELETED);
    const client = serve(
      { [DELETED]: { status: 204 }, [WRITTEN]: "access_role_updated" },
      hold.timing,
    );
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    await userEvent.click(
      within(grid).getByRole("button", { name: "Supprimer «\u00a0Administrateur\u00a0»" }),
    );
    const confirmation = await screen.findByRole("alertdialog");
    await userEvent.click(within(confirmation).getByRole("button", { name: "Supprimer" }));
    const remove = within(grid).getByRole("button", {
      name: "Supprimer «\u00a0Administrateur\u00a0»",
    });
    await waitFor(() => {
      expect(remove).toHaveAttribute("aria-busy", "true");
    });
    expect(remove).toHaveAttribute("aria-disabled", "true");
    expect(label("Administrateur")).toHaveAttribute("aria-busy", "true");
    expect(cell("Administrateur")).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(cell("Administrateur"));
    await userEvent.click(remove);
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(client.calls.map(({ route }) => route)).toEqual([DELETED]);
    hold.release();
    await waitFor(() => {
      expect(remove).toHaveAttribute("aria-busy", "false");
    });
    expect(cell("Administrateur")).not.toHaveAttribute("aria-disabled");
    expect(label("Administrateur")).toHaveAttribute("aria-busy", "false");
  });

  it("sends no renaming validated while a cell of the role is written, the entry kept, and renames from the version the cell answered once it is free [WF-ADM-0010-A]", async () => {
    const hold = holdRoute(WRITTEN);
    const client = serve(
      { [WRITTEN]: ["access_role_updated", "access_role_renamed"] },
      hold.timing,
    );
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    // The entry is opened first, then a cell of the same role is checked, then the entry validated.
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp");
    // A click from the code, which leaves the focus, and so the entry, where they are.
    act(() => {
      cell("Manager").click();
    });
    await waitFor(() => {
      expect(cell("Manager")).toHaveAttribute("aria-busy", "true");
    });
    await userEvent.keyboard("{Enter}");
    expect(client.calls).toHaveLength(1);
    hold.release();
    await waitFor(() => {
      expect(cell("Manager")).toHaveAttribute("aria-busy", "false");
    });
    // The role is free: the renaming goes from the version the cell answered.
    labelCell("Manager").focus();
    await userEvent.keyboard("Resp{Enter}");
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    const checked = example("access_role_updated") as Schemas["AccessRole"];
    expect(client.calls[1]?.body).toMatchObject({
      label: "Resp",
      lock_version: checked.lock_version,
    });
  });

  it("keeps a confirmation opened before a write of the role open and its command busy, deleting once the role is free [WF-ADM-0010-A]", async () => {
    const hold = holdRoute(WRITTEN);
    const client = serve(
      { [DELETED]: { status: 204 }, [WRITTEN]: "access_role_updated" },
      hold.timing,
    );
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    const box = cell("Administrateur");
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    await userEvent.click(
      within(grid).getByRole("button", { name: "Supprimer «\u00a0Administrateur\u00a0»" }),
    );
    const confirmation = await screen.findByRole("alertdialog");
    // A cell of the role is written while the confirmation is open (set from the code, not a press).
    act(() => {
      box.click();
    });
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    const confirm = within(confirmation).getByRole("button", { name: "Supprimer" });
    expect(confirm).toBeDisabled();
    hold.release();
    await waitFor(() => {
      expect(confirm).toBeEnabled();
    });
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    await userEvent.click(confirm);
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual([WRITTEN, DELETED]);
    });
  });

  it("frees a role whose write the server refuses, the next write going from the version read [WF-ADM-0010-A]", async () => {
    const client = serve({
      [WRITTEN]: [
        { problem: example("access_role_update_refused") as never },
        "access_role_updated",
      ],
    });
    const shown = permissions.filter(({ code }) => code === "planning.write");
    render(inFrench(tableAndMatrix(shown)));
    await userEvent.click(cell("Administrateur"));
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await waitFor(() => {
      expect(cell("Manager")).toHaveAttribute("aria-busy", "false");
    });
    await userEvent.click(cell("Manager"));
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
  });
});
