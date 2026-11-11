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
import { menuSummary, openAudit, openMenu } from "@/test/check-menu";
import { openFilters } from "@/test/accounts";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { keysOf } from "@/test/grid-preferences";

import { AccessRoleList, UserList } from "./account-lists";
import { type AccessRole, accessRoleGrid, type User } from "./admin-grids";
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
          query={{ sort: undefined, search: undefined, size: undefined }}
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
          query={{ sort: undefined, search: undefined, size: undefined }}
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

/** The choice of the author of a column, by its heading: its menu opened, its list. */
async function author(column: "Créé par" | "Modifié par"): Promise<HTMLElement> {
  // The table of the roles has no panel: its filters stand over it.
  if (screen.queryByRole("button", { name: /^Filtres( \(|$)/ }) !== null) {
    await openFilters();
  }
  await openAudit();
  return openMenu(column);
}

/** The names of the authors a list offers, in its order. */
function offered(list: HTMLElement): (string | null | undefined)[] {
  return within(list)
    .getAllByRole("radio")
    .map((radio) => radio.closest("label")?.textContent);
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
    const { rerender } = render(accounts());
    const created = await author("Créé par");
    expect(offered(created)).toEqual([
      "Tous les auteurs",
      "Un compte",
      "La plateforme",
      "Camille Martin",
    ]);
    await userEvent.click(within(created).getByRole("radio", { name: "La plateforme" }));
    expect(lastAddress()).toBe("/admin/users?origins=local&created_by_kind=platform");
    // An account chosen replaces the kind of author, and the kind an account.
    page.search = "origins=local&created_by_kind=platform";
    rerender(accounts(audit(page.search)));
    const again = await author("Créé par");
    await userEvent.click(within(again).getByRole("radio", { name: "Camille Martin" }));
    expect(lastAddress()).toBe(`/admin/users?origins=local&created_by_user_id=${CAMILLE}`);
    page.search = `origins=local&created_by_user_id=${CAMILLE}`;
    rerender(accounts(audit(page.search)));
    const last = await author("Créé par");
    await userEvent.click(within(last).getByRole("radio", { name: "Tous les auteurs" }));
    expect(lastAddress()).toBe("/admin/users?origins=local");
  });

  it("shows the author the address names, an account or the platform, each column its own", async () => {
    page.search = `created_by_kind=platform&updated_by_user_id=${CAMILLE}`;
    render(accounts(audit(page.search)));
    await openFilters();
    await openAudit();
    expect(menuSummary("Créé par")).toBe("La plateforme");
    expect(menuSummary("Modifié par")).toBe("Camille Martin");
  });

  it("finds the accounts to choose by a search inside the list, sent to the server once the typing pauses, deactivated ones included, and says how many it found", async () => {
    const client = serve({ "GET /users": "users_search" });
    render(accounts());
    const modified = await author("Modifié par");
    // No button to press: the search is inside the list, and goes to the server as the typing pauses.
    expect(screen.queryByRole("button", { name: "Chercher" })).toBeNull();
    await userEvent.type(
      within(modified).getByRole("searchbox", {
        name: "Rechercher dans «\u00A0Modifié par\u00A0»",
      }),
      "ines roux",
    );
    expect((await screen.findByText(/^1 compte trouvé/)).textContent).toBe(
      "1 compte trouvé, à choisir dans «\u00A0Modifié par\u00A0».",
    );
    expect(client.calls.find(({ route }) => route === "GET /users")?.query.toString()).toBe(
      "search=ines+roux&include_inactive=true&limit=20",
    );
    await userEvent.click(within(modified).getByRole("radio", { name: "Inès Roux" }));
    expect(lastAddress()).toBe(`/admin/users?updated_by_user_id=${INES}`);
  });

  it("filters the list by what is typed before the server answers, and offers the accounts of the page alone in the other column", async () => {
    serve({ "GET /users": "users_search" });
    render(accounts());
    const created = await author("Créé par");
    expect(within(created).queryByRole("radio", { name: "Inès Roux" })).toBeNull();
    await userEvent.type(
      within(created).getByRole("searchbox", {
        name: "Rechercher dans «\u00A0Créé par\u00A0»",
      }),
      "cam",
    );
    expect(offered(created)).toEqual(["Tous les auteurs", "Camille Martin"]);
  });

  it("tells a search the server refuses by the catalogue, and offers nothing more", async () => {
    serve({ "GET /users": { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } });
    render(accounts());
    const created = await author("Créé par");
    expect(within(created).getAllByRole("radio")).toHaveLength(4);
    await userEvent.type(
      within(created).getByRole("searchbox", {
        name: "Rechercher dans «\u00A0Créé par\u00A0»",
      }),
      "Mor",
    );
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    // Nothing found is added to the list.
    expect(within(created).queryByRole("radio", { name: "Inès Roux" })).toBeNull();
  });

  it("names on the screen of the roles every author of the roles, and sends no search to the server there", async () => {
    page.path = "/admin/access-roles";
    const client = serve();
    render(accessRoles(example("access_roles_updated_by_anonymized") as AccessRole[]));
    const modified = await author("Modifié par");
    // The anonymised author by the neutral label, never by a name it no longer has.
    expect(offered(modified)).toEqual([
      "Tous les auteurs",
      "Un compte",
      "La plateforme",
      "Compte anonymisé",
    ]);
    await userEvent.type(
      within(modified).getByRole("searchbox", {
        name: "Rechercher dans «\u00A0Modifié par\u00A0»",
      }),
      "Anon",
    );
    expect(offered(modified)).toEqual(["Tous les auteurs", "Compte anonymisé"]);
    await new Promise((resolve) => setTimeout(resolve, 400));
    expect(client.calls.filter(({ route }) => route === "GET /users")).toEqual([]);
  });
});

describe("the filter of a table on the period of an audit column", () => {
  it("writes the local days entered as the instants of the contract, under the names of its column, back to the first page [WF-IHM-0130-A]", async () => {
    page.search = "offset=2";
    render(accounts());
    await openFilters();
    await openAudit();
    const form = screen.getByRole("form", { name: "Créé le" });
    fireEvent.change(within(form).getByLabelText("Du"), { target: { value: "2026-01-01" } });
    fireEvent.change(within(form).getByLabelText("Au"), { target: { value: "2026-01-31" } });
    // Sent on Enter, once the page is hydrated, which the browser knows its time zone by.
    await waitFor(() => {
      fireEvent.keyDown(within(form).getByLabelText("Au"), { key: "Enter" });
      expect(router.push).toHaveBeenCalled();
    });
    const query = new URLSearchParams({
      created_at_from: new Date(2026, 0, 1).toISOString(),
      created_at_to: new Date(2026, 1, 1).toISOString(),
    });
    expect(lastAddress()).toBe(`/admin/users?${query.toString()}`);
  });

  it("folds the audit filters at the bottom of the panel, closed until opened and not kept, #2916", async () => {
    render(accounts());
    await openFilters();
    const section = screen.getByRole("button", {
      name: "Filtres d’audit — création et modification",
    });
    expect(section).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("form", { name: "Créé le" })).toBeNull();
    await userEvent.click(section);
    expect(section).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("form", { name: "Créé le" })).toBeVisible();
    expect(screen.getByRole("form", { name: "Modifié le" })).toBeVisible();
    expect(menuSummary("Créé par")).toBe("Tous les auteurs");
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
          known_columns: keysOf(accessRoleGrid(false).columns),
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
