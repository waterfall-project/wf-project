// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { forgetMessages } from "@/components/notices/message-history";
import { account, accounts, grid, told, users, writes } from "@/test/accounts";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";

import type { User } from "./admin-grids";

// The attachment of an account to a node of the organisation chart, in its cell (US-0840, #379): the
// server of Next as far as the screen needs it, the fake back answering with the examples.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(""),
}));

type OrgNode = components["schemas"]["OrgNode"];

const active = (example("org_nodes") as OrgNode[]).map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
}));
const [inactive] = (example("org_nodes_with_inactive") as OrgNode[]).filter(
  (node) => !node.is_active,
);
if (inactive === undefined) {
  throw new Error("the example holds a deactivated node");
}
const ACHATS = "01926f3a-7c00-7000-8000-000000000473";
const MOREAU_NODE = "01926f3a-7c00-7000-8000-000000000471";

function serve(answers: FakeAnswers = {}) {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers });
  server.client = client;
  return client;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  serve();
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** The list of the attachment of an account, by the name the account bears. */
function listOf(name: string): HTMLElement {
  return within(grid()).getByRole("combobox", {
    name: `Rattachement de «\u00A0${name}\u00A0»`,
  });
}

describe("the attachment of an account, in its cell", () => {
  it("offers the active nodes of the chart in the order of the tree, and none, to a session that may modify the accounts, and breaks no rule of accessibility", async () => {
    const { container } = render(accounts(true, users.items, undefined, active));
    const list = listOf("Alix Moreau");
    expect(list).toHaveValue(MOREAU_NODE);
    const options = within(list).getAllByRole("option");
    expect(options).toHaveLength(active.length + 1);
    expect(options[0]).toHaveTextContent("Aucun");
    active.forEach((node, at) => {
      expect(options[at + 1]).toHaveTextContent(node.label);
    });
    expect(listOf("Lucas Petit")).toHaveValue("");
    await expectAccessible(container);
  });

  it("writes the node chosen with the counter read, and says it", async () => {
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    render(accounts(true, users.items, undefined, active));
    await userEvent.selectOptions(listOf("Lucas Petit"), ACHATS);
    const petit = account("Petit");
    await waitFor(() => {
      expect(told().textContent).toContain("Rattachement de");
    });
    expect(writes(client)).toEqual([
      [
        "PATCH /users/{user_id}",
        `/users/${petit.user_id}`,
        { org_node_id: ACHATS, lock_version: petit.lock_version },
      ],
    ]);
  });

  it("removes the attachment by choosing none, which writes a null node", async () => {
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    render(accounts(true, users.items, undefined, active));
    await userEvent.selectOptions(listOf("Alix Moreau"), "");
    const moreau = account("Moreau");
    await waitFor(() => {
      expect(writes(client)).toHaveLength(1);
    });
    expect(writes(client)[0]).toEqual([
      "PATCH /users/{user_id}",
      `/users/${moreau.user_id}`,
      { org_node_id: null, lock_version: moreau.lock_version },
    ]);
  });

  it("shows a deactivated node the account stays attached to by its label, and does not offer it to the others", () => {
    // Variant of the account of Lucas Petit: attached to a node deactivated since.
    const attached: User = {
      ...account("Petit"),
      org_node_id: inactive.org_node_id,
      org_node_label: inactive.label,
    };
    render(
      accounts(
        true,
        users.items.map((user) => (user.user_id === attached.user_id ? attached : user)),
        undefined,
        active,
      ),
    );
    const list = listOf("Lucas Petit");
    expect(list).toHaveValue(inactive.org_node_id);
    expect(within(list).getByRole("option", { name: inactive.label })).toBeDisabled();
    expect(within(listOf("Alix Moreau")).queryByText(inactive.label)).toBeNull();
  });

  it.each([
    [
      "the node deactivated between the reading and the choice",
      {
        code: "VALIDATION_FAILED",
        status: 422,
        fields: [{ pointer: "/org_node_id", code: "INACTIVE_REFERENCE_OBJECT" }],
      } satisfies Problem & { status: 422 },
      "Les données saisies ne sont pas valides.",
    ],
    [
      "the account changed since it was read",
      { code: "STALE_LOCK_VERSION", status: 412 } satisfies Problem & { status: 412 },
      "rechargez-la pour voir sa dernière version.",
    ],
  ])(
    "tells in the region of the accounts the attachment the server refuses — %s —, the list back at the node read and the focus on its cell [WF-ADM-0050-A]",
    async (_, problem, said) => {
      const client = serve({ "PATCH /users/{user_id}": { problem } });
      render(accounts(true, users.items, undefined, active));
      const list = listOf("Lucas Petit");
      await userEvent.selectOptions(list, ACHATS);
      const alert = await screen.findByRole("alert");
      expect(alert.textContent).toContain(said);
      expect(writes(client)).toHaveLength(1);
      expect(list).toHaveValue("");
      expect(list).not.toHaveAttribute("aria-busy", "true");
      expect(told().textContent).toBe("");
      const cell = list.closest("td");
      await waitFor(() => {
        expect(cell?.contains(document.activeElement)).toBe(true);
      });
    },
  );

  it("shows an anonymised account attached to a node by its label alone, read only, for a session that may modify the accounts [WF-ADM-0060-A]", () => {
    const [anonymised] = (example("users_anonymized") as { items: User[] }).items;
    if (anonymised?.org_node_label == null) {
      throw new Error("the example holds an anonymised account attached to a node");
    }
    render(accounts(true, [anonymised], undefined, active));
    expect(screen.queryByRole("combobox", { name: /^Rattachement de/ })).toBeNull();
    expect(within(grid()).getByText(anonymised.org_node_label)).toBeInTheDocument();
  });

  it("reads the attachment only for a session that may not modify the accounts", () => {
    render(accounts(false, users.items, undefined, active));
    expect(screen.queryByRole("combobox", { name: /^Rattachement de/ })).toBeNull();
    expect(within(grid()).getByText("Bureau d'études électricité")).toBeInTheDocument();
  });
});
