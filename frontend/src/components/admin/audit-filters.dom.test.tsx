// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { AccessRoleList, UserList } from "./account-lists";
import type { AccessRole, User } from "./admin-grids";
import { type AuditFilters, authorsOf, readAuditFilters } from "./audit-address";
import { ROLE_KEPT } from "./role-address";
import { USER_KEPT } from "./user-address";

// The server of Next, as far as the filters need it: the fake back, which finds the accounts and
// keeps the settings of the grids, the address they read and the navigations they ask.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/users", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };
const roles = example("access_roles") as AccessRole[];
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";
const INES = "01926f3a-7c00-7000-8000-000000000306";

/** The filters of the audit columns an address asks. */
function audit(search = ""): AuditFilters {
  return readAuditFilters(new URLSearchParams(search));
}

/** The table of the accounts of the witness, in French, as the address asks it. */
function accounts(filters: AuditFilters = audit(), kept?: GridPreferences): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={users.items}
          page={users.meta}
          query={{ sort: undefined, search: undefined }}
          preferences={kept}
          origins={[]}
          nodes={[]}
          orgNode={undefined}
          roles={[]}
          accessRoles={[]}
          active={undefined}
          audit={filters}
          authors={authorsOf(users.items)}
          editable={false}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The table of the access roles of the witness, in French, as the address asks it. */
function accessRoles(shown: readonly AccessRole[], filters: AuditFilters = audit()): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={ROLE_KEPT}>
        <AccessRoleList
          roles={shown}
          query={{ sort: undefined, search: undefined }}
          preferences={undefined}
          filters={{
            predefined: undefined,
            holders: { min: undefined, max: undefined },
            audit: filters,
            authors: authorsOf(shown),
          }}
          editable={false}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers });
  server.client = client;
  return client;
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

/** The choice of the author of a column, by its heading. */
function author(column: "Créé par" | "Modifié par"): HTMLElement {
  return screen.getByRole("combobox", { name: column });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.path = "/admin/users";
  page.search = "";
  serve();
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  router.replace.mockClear();
});

describe("the filter of a table on the author of an audit column", () => {
  it("offers any account, the platform and the accounts that wrote the rows, and writes the one chosen under the names of the contract, back to the first page [WF-IHM-0130-A]", async () => {
    page.search = "origins=local&offset=2";
    render(accounts());
    const created = author("Créé par");
    expect([...within(created).getAllByRole("option")].map((option) => option.textContent)).toEqual(
      ["Tous les auteurs", "Un compte", "La plateforme", "Camille Martin"],
    );
    await userEvent.selectOptions(created, "La plateforme");
    expect(lastAddress()).toBe("/admin/users?origins=local&created_by_kind=platform");
    // An account chosen replaces the kind of author, and the kind an account.
    page.search = "origins=local&created_by_kind=platform";
    await userEvent.selectOptions(created, "Camille Martin");
    expect(lastAddress()).toBe(`/admin/users?origins=local&created_by_user_id=${CAMILLE}`);
    page.search = `origins=local&created_by_user_id=${CAMILLE}`;
    await userEvent.selectOptions(created, "Tous les auteurs");
    expect(lastAddress()).toBe("/admin/users?origins=local");
  });

  it("shows the author the address names, an account or the platform, each column its own", () => {
    page.search = `created_by_kind=platform&updated_by_user_id=${CAMILLE}`;
    render(accounts(audit(page.search)));
    expect(author("Créé par")).toHaveValue("platform");
    expect(author("Modifié par")).toHaveValue(CAMILLE);
  });

  it("finds the accounts to choose by a search of the server, deactivated ones included, and says how many it found", async () => {
    const client = serve({ "GET /users": "users_search" });
    render(accounts());
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Chercher un compte pour « Modifié par »" }),
      "ines roux{Enter}",
    );
    expect((await screen.findByText(/^1 compte trouvé/)).textContent).toBe(
      "1 compte trouvé, à choisir dans « Modifié par ».",
    );
    expect(client.calls.find(({ route }) => route === "GET /users")?.query.toString()).toBe(
      "search=ines+roux&include_inactive=true&limit=20",
    );
    await userEvent.selectOptions(author("Modifié par"), "Inès Roux");
    expect(lastAddress()).toBe(`/admin/users?updated_by_user_id=${INES}`);
    // The other column offers the accounts of the page alone.
    expect(within(author("Créé par")).queryByRole("option", { name: "Inès Roux" })).toBeNull();
  });

  it("tells a search the server refuses by the catalogue, and offers nothing more", async () => {
    serve({ "GET /users": { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } });
    render(accounts());
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Chercher un compte pour « Créé par »" }),
      "Mor{Enter}",
    );
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(within(author("Créé par")).getAllByRole("option")).toHaveLength(4);
  });

  it("names on the screen of the roles every author of the roles, and offers no search there", () => {
    page.path = "/admin/access-roles";
    render(accessRoles(example("access_roles_updated_by_anonymized") as AccessRole[]));
    // The anonymised author by the neutral label, never by a name it no longer has.
    expect(
      [...within(author("Modifié par")).getAllByRole("option")].map((option) => option.textContent),
    ).toEqual(["Tous les auteurs", "Un compte", "La plateforme", "Compte anonymisé"]);
    expect(screen.queryByRole("searchbox", { name: /Chercher un compte/ })).toBeNull();
  });
});

describe("the filter of a table on the period of an audit column", () => {
  it("writes the local days entered as the instants of the contract, under the names of its column, back to the first page [WF-IHM-0130-A]", async () => {
    page.search = "offset=2";
    render(accounts());
    const form = screen.getByRole("form", { name: "Créé le" });
    // Sent once the page is hydrated, which the browser knows its time zone by.
    await waitFor(() => {
      expect(within(form).getByRole("button", { name: "Filtrer" })).toBeEnabled();
    });
    fireEvent.change(within(form).getByLabelText("Du"), { target: { value: "2026-01-01" } });
    fireEvent.change(within(form).getByLabelText("Au"), { target: { value: "2026-01-31" } });
    await userEvent.click(within(form).getByRole("button", { name: "Filtrer" }));
    const query = new URLSearchParams({
      created_at_from: new Date(2026, 0, 1).toISOString(),
      created_at_to: new Date(2026, 1, 1).toISOString(),
    });
    expect(lastAddress()).toBe(`/admin/users?${query.toString()}`);
  });

  it("says at its field the end the server refuses for preceding the start, the grid unread, and breaks no rule of accessibility", async () => {
    page.path = "/admin/access-roles";
    page.search = "updated_at_from=2026-06-01T00:00:00Z&updated_at_to=2026-05-01T00:00:00Z";
    const filters: AuditFilters = {
      ...audit(page.search),
      refused: {
        updated: { to: { code: "VALUE_OUT_OF_RANGE", minimum: "2026-06-01T00:00:00Z" } },
      },
    };
    const { container } = render(accessRoles([], filters));
    const end = within(screen.getByRole("form", { name: "Modifié le" })).getByLabelText("Au");
    expect(end).toHaveAttribute("aria-invalid", "true");
    expect(end).toHaveFocus();
    expect(screen.queryByRole("grid", { name: "Rôles d’habilitation" })).toBeNull();
    expect(document.body.textContent).toContain(CATALOGUES.fr.reference.boundsRefused);
    await expectAccessible(container);
  });
});

describe("the filters of the audit columns, kept", () => {
  it("are kept with the settings of the grid, as the page shows them [WF-IHM-0060-A]", async () => {
    page.path = "/admin/access-roles";
    page.search = `created_by_kind=platform&updated_by_user_id=${CAMILLE}&updated_at_from=2025-09-01T00:00:00Z`;
    render(accessRoles(roles, audit(page.search)));
    const client = server.client as FakeClient;
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual(["PATCH /me/preferences"]);
    });
    expect(client.calls[0]?.body).toEqual({
      grids: {
        access_roles: {
          hidden_columns: [],
          column_widths: {},
          filters: {
            created_by_kind: "platform",
            updated_by_user_id: CAMILLE,
            updated_at_from: "2025-09-01T00:00:00Z",
          },
        },
      },
    });
  });
});
