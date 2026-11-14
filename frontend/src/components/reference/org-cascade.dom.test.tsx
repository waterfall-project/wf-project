// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { type OrgNode, type ResourceRole } from "./resource-grids";
import { type NodeOffered, OrgNodeList } from "./resource-lists";

// The server of Next, as far as the list needs it: the fake back, the page rendered again once an
// object is written, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));

const NODE = "PATCH /reference/org-nodes/{org_node_id}";
const NODE_ACTIVATION = "PUT /reference/org-nodes/{org_node_id}/activation";
const NO_BOUNDS = { min: undefined, max: undefined };
const tree = example("org_nodes_with_inactive") as OrgNode[];
const choices: NodeOffered[] = tree.map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
  active: node.is_active,
}));

/** The node of the tree read by its code. */
function nodeOf(code: string): OrgNode {
  const found = tree.find((node) => node.code === code);
  if (found === undefined) {
    throw new Error(`the tree holds ${code}`);
  }
  return found;
}

/** The state cell of the row of a node, by its code. */
function stateOf(code: string): Element | null {
  const label = nodeOf(code).label;
  const row = [...document.querySelectorAll<HTMLElement>("tbody tr")].find((candidate) =>
    candidate.querySelector('td[data-column="label"]')?.textContent.includes(label),
  );
  return row?.querySelector('td[data-column="state"]') ?? null;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
});

describe("the cascade of the deactivation of a node", () => {
  it("shows every descendant of a deactivated node deactivated, at the version of the answer, before the page is read anew [WF-REF-0080-A]", async () => {
    const answer = example("org_node_deactivated_with_descendants") as {
      org_nodes: OrgNode[];
      resource_roles: ResourceRole[];
    };
    const client = fakeClient({
      [NODE]: "org_node_updated",
      [NODE_ACTIVATION]: { example: "org_node_deactivated_with_descendants", status: 200 },
    });
    server.client = client;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PendingAddress>
          <OrgNodeList
            rows={tree.filter((node) => node.is_active)}
            query={{ sort: undefined, search: undefined, size: undefined }}
            preferences={undefined}
            editable
            filters={{ code: undefined, level: undefined, state: undefined, levels: NO_BOUNDS }}
            levels={[1, 2, 3]}
            nodes={choices}
          />
        </PendingAddress>
      </NextIntlClientProvider>,
    );
    // The direction carries two levels of descendants, and roles attached to some of them.
    const codes = ["DT", "BE-ELEC", "AT-CABL", "ACHATS"];
    for (const code of codes) {
      expect(stateOf(code)).toHaveTextContent(/^Actif/);
    }
    await userEvent.click(
      screen.getByRole("button", { name: "Désactiver «\u00A0Direction technique\u00A0»" }),
    );
    await vi.waitFor(() => {
      expect(stateOf("DT")).toHaveTextContent(/^Désactivé/);
    });
    // La désactivation d'un nœud portant deux niveaux de descendants et des rôles les désactive tous.
    expect(answer.org_nodes.map((node) => node.code)).toEqual(codes);
    // This test carries the tree only: no list reads the roles of this answer, so they are not asked.
    for (const node of answer.org_nodes) {
      expect(stateOf(node.code)).toHaveTextContent(/^Désactivé/);
    }
    expect(client.calls.map(({ route, path, body }) => ({ route, path, body }))).toEqual([
      {
        route: NODE_ACTIVATION,
        path: `/reference/org-nodes/${nodeOf("DT").org_node_id}/activation`,
        body: { is_active: false, lock_version: 1 },
      },
    ]);
    // The page is asked once, and the rows shown are those of the answer.
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // A descendant is written from the version of the answer, with no page read anew.
    const descendant = answer.org_nodes.find((node) => node.code === "AT-CABL");
    expect(descendant).toBeDefined();
    expect(descendant?.lock_version).not.toBe(nodeOf("AT-CABL").lock_version);
    await userEvent.click(
      screen.getByRole("button", { name: `Modifier «\u00A0${nodeOf("AT-CABL").label}\u00A0»` }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === NODE).map((call) => call.body)).toEqual([
        expect.objectContaining({ lock_version: descendant?.lock_version }),
      ]);
    });
  });
});
