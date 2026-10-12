// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";

import { UserList } from "./account-lists";
import type { AccessRole, User } from "./admin-grids";
import { USER_KEPT } from "./user-address";

// The server of Next, as far as the screen needs it: the fake back, the address it reads and the
// navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };
const anonymized = (example("users_anonymized") as { items: User[] }).items;
const roles = (example("access_roles") as AccessRole[]).map((role) => ({
  id: role.access_role_id,
  label: role.label,
}));
const CHIFFREUR = "01926f3a-7c00-7000-8000-000000000705";
const DIRECTION = "01926f3a-7c00-7000-8000-000000000701";
const AUDITEUR = "01926f3a-7c00-7000-8000-000000000707";

/** Serve the fake back, which keeps the settings of the grid, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers }, timing);
  server.client = client;
  return client;
}

/** The calls the screen made, but the settings of its grid. */
function writes(client: FakeClient) {
  return client.calls
    .filter(({ route }) => route !== "PATCH /me/preferences")
    .map(({ route, path, body }) => [route, path, body]);
}

/** The accounts of the witness, in French, as a session that may modify them, or not, reads them. */
function accounts(editable = true, shown: readonly User[] = users.items, kept?: GridPreferences) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={shown}
          page={users.meta}
          query={{ sort: undefined, search: undefined }}
          preferences={kept}
          origins={[]}
          nodes={[]}
          orgNode={undefined}
          roles={roles}
          accessRoles={[]}
          active={undefined}
          editable={editable}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the accounts. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Comptes utilisateurs" });
}

/** The region of the table that says what its last command did, by its name. */
function told(): HTMLElement {
  return screen.getByRole("status", { name: "Commandes des comptes" });
}

/** Hold the answers of a route until released: a write under way. */
function holdRoute(held: string): { readonly timing: FakeTiming; readonly release: () => void } {
  const settles: (() => void)[] = [];
  const until = new Promise<void>((settle) => {
    settles.push(settle);
  });
  return {
    timing: {
      hold: (route) => (route === held ? until : undefined),
    },
    release: () => {
      for (const settle of settles) {
        settle();
      }
    },
  };
}

/** Hold the deactivations until released: a write of a row under way. */
function heldActivation() {
  return holdRoute("PUT /users/{user_id}/activation");
}

/** Open the creation of a local account, and give its form. */
async function openCreation(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
  return screen.findByRole("form", { name: "Créer un compte local" });
}

/** Fill the creation of Léa Garnier, and send it. */
async function createGarnier(form: HTMLElement) {
  await userEvent.type(within(form).getByLabelText("Nom"), "Garnier");
  await userEvent.type(within(form).getByLabelText("Prénom"), "Léa");
  await userEvent.type(within(form).getByLabelText("Adresse électronique"), "l@example.com");
  await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
}

/** An account of the witness, by its last name. */
function account(lastName: string): User {
  const found = users.items.find((user) => user.last_name === lastName);
  if (found === undefined) {
    throw new Error(`no account ${lastName} in the witness`);
  }
  return found;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  serve({});
  page.search = "";
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  router.replace.mockClear();
  refresh.mockReset();
});

describe("the table of the accounts, its own entry", () => {
  it("offers to delete no account [WF-ADM-0060-A]; to a session that may modify them, a switch of the state, the roles, the link of a local account and the anonymisation of a deactivated one on each row, and breaks no rule of accessibility", async () => {
    const { container } = render(accounts());
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
    expect(screen.queryByText(/Supprimer/)).toBeNull();
    expect(screen.getByRole("button", { name: "Créer un compte local" })).toBeInTheDocument();
    expect(within(grid()).getAllByRole("switch")).toHaveLength(7);
    expect(
      within(grid()).getByRole("switch", { name: "Compte de « Alix Moreau » actif" }),
    ).not.toBeChecked();
    expect(within(grid()).getAllByRole("button", { name: /^Rôles de «/ })).toHaveLength(7);
    // The five local accounts have a link; those of the directory and of the provider, none.
    expect(within(grid()).getAllByRole("button", { name: /^Lien de fixation/ })).toHaveLength(5);
    expect(
      within(grid()).queryByRole("button", {
        name: "Lien de fixation du mot de passe de « Dominique Bernard »",
      }),
    ).toBeNull();
    await expectAccessible(container);
  });

  it("offers nothing to write to a session that may not modify the accounts: the state and the roles read only, and no creation", () => {
    render(accounts(false));
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Créer|Rôles de|Lien|Anonymiser)/ })).toBeNull();
    expect(screen.queryByRole("status", { name: "Commandes des comptes" })).toBeNull();
  });

  it("presents no command an account does not list: neither its switch nor its roles", () => {
    // Dominique Bernard read as a session would that the server listed none of her commands for.
    const bernard = account("Bernard");
    render(
      accounts(
        true,
        users.items.map((user) =>
          user.user_id === bernard.user_id ? { ...user, available_commands: [] } : user,
        ),
      ),
    );
    const row = within(grid()).getByText("Bernard").closest("tr") as HTMLElement;
    expect(within(row).queryByRole("switch")).toBeNull();
    expect(within(row).queryByRole("button", { name: /^Rôles de/ })).toBeNull();
    expect(row).toHaveTextContent("Manager");
    expect(row).toHaveTextContent("Actif");
    expect(within(grid()).getAllByRole("switch")).toHaveLength(6);
  });

  it("renames a local account in its cell from the version read, its name shown as the server answers it; the name of an account of the directory is not entered [WF-ADM-0050-A]", async () => {
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    render(accounts());
    const petit = within(grid()).getByText("Petit").closest<HTMLElement>("[tabindex]");
    petit?.focus();
    await userEvent.keyboard("Petit-Laurent{Enter}");
    expect(await within(grid()).findByText("Petit-Laurent")).toBeInTheDocument();
    await waitFor(() => {
      expect(told().textContent).toBe("« Lucas Petit-Laurent » renommé.");
    });
    const lucas = account("Petit");
    expect(writes(client)).toEqual([
      [
        "PATCH /users/{user_id}",
        `/users/${lucas.user_id}`,
        { last_name: "Petit-Laurent", lock_version: lucas.lock_version },
      ],
    ]);
    // Dominique Bernard comes from the directory, which holds her names.
    const bernard = within(grid()).getByText("Bernard").closest<HTMLElement>("[tabindex]");
    bernard?.focus();
    await userEvent.keyboard("Durand{Enter}");
    expect(writes(client)).toHaveLength(1);
  });

  it("writes a name entered while the switch of its row is under way once it is answered, from the version it answered", async () => {
    const held = heldActivation();
    const client = serve(
      {
        "PUT /users/{user_id}/activation": "user_deactivated",
        "PATCH /users/{user_id}": "user_renamed_deactivated",
      },
      held.timing,
    );
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de « Noé Vidal » actif" }),
    );
    within(grid()).getByText("Vidal").closest<HTMLElement>("[tabindex]")?.focus();
    await userEvent.keyboard("Vidal-Roux{Enter}");
    // The name waits for the deactivation of its row.
    expect(writes(client).map(([route]) => route)).toEqual(["PUT /users/{user_id}/activation"]);
    held.release();
    await waitFor(() => {
      expect(told().textContent).toBe("« Noé Vidal-Roux » renommé.");
    });
    const noe = account("Vidal");
    const deactivated = example("user_deactivated") as User;
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/activation",
        `/users/${noe.user_id}/activation`,
        { is_active: false, lock_version: noe.lock_version },
      ],
      [
        "PATCH /users/{user_id}",
        `/users/${noe.user_id}`,
        { last_name: "Vidal-Roux", lock_version: deactivated.lock_version },
      ],
    ]);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(within(grid()).getByText("Vidal-Roux")).toBeInTheDocument();
  });

  it("marks the switch and the roles of a row busy and unavailable while a write of it is under way, a press asking nothing", async () => {
    const held = heldActivation();
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" }, held.timing);
    render(accounts());
    const vidal = within(grid()).getByRole("switch", { name: "Compte de « Noé Vidal » actif" });
    const trigger = within(grid()).getByRole("button", { name: "Rôles de « Noé Vidal »" });
    expect(vidal).not.toHaveAttribute("aria-disabled");
    await userEvent.click(vidal);
    await waitFor(() => {
      expect(vidal).toHaveAttribute("aria-busy", "true");
    });
    expect(vidal).toHaveAttribute("aria-disabled", "true");
    expect(trigger).toHaveAttribute("aria-busy", "true");
    await userEvent.click(trigger);
    const list = await screen.findByRole("group", { name: "Rôles de « Noé Vidal »" });
    const chiffreur = within(list).getByRole("checkbox", { name: "Chiffreur" });
    expect(chiffreur).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(chiffreur);
    expect(chiffreur).not.toBeChecked();
    expect(writes(client)).toHaveLength(1);
    held.release();
    await waitFor(() => {
      expect(chiffreur).not.toHaveAttribute("aria-disabled");
    });
    expect(trigger).toHaveAttribute("aria-busy", "false");
    expect(writes(client)).toHaveLength(1);
  });
});

describe("the anonymisation of an account", () => {
  it("offers the anonymisation of a deactivated account alone, confirmed first as irreversible, then anonymises it from the version read and says so [WF-ADM-0060-A]", async () => {
    const client = serve({ "POST /users/{user_id}/anonymization": "user_anonymized" });
    render(accounts());
    // Alix Moreau is the one account deactivated, and the one offered her anonymisation.
    const anonymization = within(grid()).getByRole("button", { name: /^Anonymiser «/ });
    expect(anonymization).toHaveAccessibleName("Anonymiser «\u00a0Alix Moreau\u00a0»");
    expect(anonymization).not.toHaveAttribute("aria-disabled");
    // Given up, nothing is asked.
    await userEvent.click(anonymization);
    await userEvent.click(await screen.findByRole("button", { name: "Conserver" }));
    expect(writes(client)).toEqual([]);
    await userEvent.click(anonymization);
    const confirmation = await screen.findByRole("alertdialog", {
      name: "Anonymiser «\u00a0Alix Moreau\u00a0»\u00a0?",
    });
    expect(confirmation).toHaveTextContent("est irréversible");
    await userEvent.click(within(confirmation).getByRole("button", { name: "Anonymiser" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Compte anonymisé.");
    });
    const alix = account("Moreau");
    expect(writes(client)).toEqual([
      [
        "POST /users/{user_id}/anonymization",
        `/users/${alix.user_id}/anonymization`,
        { lock_version: alix.lock_version },
      ],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
    // The account answered names her no more.
    expect(grid()).not.toHaveTextContent(/Moreau/);
    expect(
      within(grid()).getByRole("button", { name: "Anonymiser «\u00a0Compte anonymisé\u00a0»" }),
    ).toHaveAttribute("aria-disabled", "true");
  });

  it.each([
    [
      "an account active again, which is to be deactivated first",
      example("user_anonymization_refused") as Problem & { status: 409 },
      "Condition non remplie : compte désactivé.",
    ],
    [
      "the identity provider silent, nothing written",
      {
        code: "COMPONENT_UNAVAILABLE",
        status: 503,
        params: { component: "identity_provider" },
      } satisfies Problem & { status: 503 },
      "Fournisseur d’identité",
    ],
  ])(
    "tells by the catalogue the anonymisation the server refuses — %s [WF-ADM-0060-A]",
    async (_, problem, said) => {
      serve({ "POST /users/{user_id}/anonymization": { problem } });
      render(accounts());
      await userEvent.click(
        within(grid()).getByRole("button", { name: "Anonymiser «\u00a0Alix Moreau\u00a0»" }),
      );
      await userEvent.click(
        within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Anonymiser" }),
      );
      expect(await screen.findByRole("alert")).toHaveTextContent(said);
      expect(told().textContent).toBe("");
      expect(within(grid()).getByText("Moreau")).toBeInTheDocument();
    },
  );

  it("marks the anonymisation of a row busy and unavailable while a write of it is under way, a press asking nothing", async () => {
    const held = heldActivation();
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" }, held.timing);
    render(accounts());
    const anonymization = within(grid()).getByRole("button", {
      name: "Anonymiser «\u00a0Alix Moreau\u00a0»",
    });
    // Her reactivation asked, and unanswered.
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de «\u00a0Alix Moreau\u00a0» actif" }),
    );
    await waitFor(() => {
      expect(anonymization).toHaveAttribute("aria-busy", "true");
    });
    expect(anonymization).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(anonymization);
    expect(screen.queryByRole("alertdialog")).toBeNull();
    held.release();
    await waitFor(() => {
      expect(anonymization).not.toHaveAttribute("aria-disabled");
    });
    expect(anonymization).toHaveAttribute("aria-busy", "false");
    expect(writes(client).map(([route]) => route)).toEqual(["PUT /users/{user_id}/activation"]);
  });

  it("presents the reactivation and the anonymisation of an anonymised account unavailable, each naming the condition it lacks [WF-ADM-0060-A]", async () => {
    const client = serve({});
    render(accounts(true, anonymized));
    const unmet = "Condition non remplie\u00a0: compte non anonymisé.";
    const reactivation = within(grid()).getByRole("switch", {
      name: "Compte de «\u00a0Compte anonymisé\u00a0» actif",
    });
    expect(reactivation).toHaveAttribute("aria-disabled", "true");
    expect(reactivation).toHaveAccessibleDescription(unmet);
    // A press does not run it: it says the condition it lacks.
    await userEvent.click(reactivation);
    expect(reactivation).not.toBeChecked();
    expect(screen.getAllByRole("status").map((region) => region.textContent)).toContain(
      `La réactivation de «\u00a0Compte anonymisé\u00a0» est indisponible. ${unmet}`,
    );
    // Its anonymisation stays listed, unavailable: it is not done twice.
    const anonymization = within(grid()).getByRole("button", {
      name: "Anonymiser «\u00a0Compte anonymisé\u00a0»",
    });
    expect(anonymization).toHaveAttribute("aria-disabled", "true");
    expect(anonymization).toHaveAccessibleDescription(unmet);
    await userEvent.click(anonymization);
    expect(told().textContent).toBe(`Anonymiser «\u00a0Compte anonymisé\u00a0»\u00a0: ${unmet}`);
    expect(screen.queryByRole("alertdialog")).toBeNull();
    // Its roles may still be attributed, as the account lists it.
    expect(
      within(grid()).getByRole("button", { name: "Rôles de «\u00a0Compte anonymisé\u00a0»" }),
    ).not.toHaveAttribute("aria-disabled");
    expect(writes(client)).toEqual([]);
  });

  it("an anonymised account has no name to enter [WF-ADM-0060-A]", async () => {
    // The server would answer a renaming: the cell alone keeps it from being asked.
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    render(accounts(true, anonymized));
    const cell = within(grid()).getByText("Compte anonymisé").closest<HTMLElement>("[tabindex]");
    if (cell === null) {
      throw new Error("no cell for the name of the anonymised account");
    }
    cell.focus();
    expect(cell).toHaveFocus();
    await userEvent.keyboard("X");
    expect(screen.queryByRole("textbox")).toBeNull();
    await userEvent.keyboard("{Enter}");
    expect(writes(client)).toEqual([]);
  });
});

describe("the state of an account, on its switch", () => {
  it("deactivates an account from the version read, says so and reads the page anew; it stays listed", async () => {
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" });
    render(accounts());
    const vidal = within(grid()).getByRole("switch", {
      name: "Compte de « Noé Vidal » actif",
    });
    expect(vidal).toBeChecked();
    await userEvent.click(vidal);
    await waitFor(() => {
      expect(told().textContent).toBe("« Noé Vidal » désactivé.");
    });
    expect(vidal).not.toBeChecked();
    expect(vidal.closest("td")).toHaveTextContent("Désactivé");
    const noe = account("Vidal");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/activation",
        `/users/${noe.user_id}/activation`,
        { is_active: false, lock_version: noe.lock_version },
      ],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("presents the deactivation of the last administrator unavailable, naming the condition she lacks, and asks nothing when pressed [WF-ADM-0120-A]", async () => {
    const client = serve({});
    render(accounts());
    const camille = within(grid()).getByRole("switch", {
      name: "Compte de « Camille Martin » actif",
    });
    const unmet =
      "Condition non remplie : un autre compte actif portant les permissions d’administration.";
    expect(camille).toHaveAttribute("aria-disabled", "true");
    expect(camille).toHaveAccessibleDescription(unmet);
    await userEvent.click(camille);
    expect(camille).toBeChecked();
    expect(screen.getAllByRole("status").map((region) => region.textContent)).toContain(
      `La désactivation de «\u00a0Camille Martin\u00a0» est indisponible. ${unmet}`,
    );
    expect(writes(client)).toEqual([]);
  });

  it("tells a deactivation the server refuses, the account changed since it was read, the switch showing it as it was", async () => {
    serve({
      "PUT /users/{user_id}/activation": { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
    });
    render(accounts());
    const roux = within(grid()).getByRole("switch", {
      name: "Compte de «\u00a0Inès Roux\u00a0» actif",
    });
    await userEvent.click(roux);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Recharger/);
    expect(roux).toBeChecked();
    expect(told().textContent).toBe("");
  });
});

describe("the access roles of an account, cell by cell", () => {
  it("attributes a role of the installation to an account that holds none, from the version read, and says so (WF-ADM-0050, WF-ADM-0090)", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("button", { name: "Rôles de « Sacha Lefèvre »" }),
    );
    const list = await screen.findByRole("group", { name: "Rôles de « Sacha Lefèvre »" });
    // Every role of the installation, whatever the node of the account (WF-ADM-0030).
    expect(within(list).getAllByRole("checkbox")).toHaveLength(roles.length);
    expect(within(list).getByRole("checkbox", { name: "Chiffreur" })).not.toBeChecked();
    await userEvent.click(within(list).getByRole("checkbox", { name: "Chiffreur" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Rôles de « Sacha Lefèvre » attribués.");
    });
    expect(within(list).getByRole("checkbox", { name: "Chiffreur" })).toBeChecked();
    const sacha = account("Lefèvre");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${sacha.user_id}/access-roles`,
        { access_role_ids: [CHIFFREUR], lock_version: sacha.lock_version },
      ],
    ]);
  });

  it("withdraws her one role from an account, which then holds none, and says so (WF-ADM-0050)", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_cleared" });
    render(accounts());
    const trigger = within(grid()).getByRole("button", { name: "Rôles de « Inès Roux »" });
    await userEvent.click(trigger);
    const list = await screen.findByRole("group", { name: "Rôles de « Inès Roux »" });
    await userEvent.click(within(list).getByRole("checkbox", { name: "Pilotage de projet" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Rôles de « Inès Roux » attribués.");
    });
    expect(trigger).toHaveTextContent("Aucun rôle");
    expect(within(list).getByRole("checkbox", { name: "Pilotage de projet" })).not.toBeChecked();
    const ines = account("Roux");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${ines.user_id}/access-roles`,
        { access_role_ids: [], lock_version: ines.lock_version },
      ],
    ]);
  });

  it("attributes a second role to an account, which then holds both, in the order given (WF-ADM-0050)", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_two" });
    render(accounts());
    const trigger = within(grid()).getByRole("button", { name: "Rôles de « Noé Vidal »" });
    await userEvent.click(trigger);
    const list = await screen.findByRole("group", { name: "Rôles de « Noé Vidal »" });
    await userEvent.click(within(list).getByRole("checkbox", { name: "Chiffreur" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Rôles de « Noé Vidal » attribués.");
    });
    expect(trigger).toHaveTextContent(/^AuditeurChiffreur$/);
    expect(within(list).getByRole("checkbox", { name: "Auditeur" })).toBeChecked();
    expect(within(list).getByRole("checkbox", { name: "Chiffreur" })).toBeChecked();
    const noe = account("Vidal");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${noe.user_id}/access-roles`,
        { access_role_ids: [AUDITEUR, CHIFFREUR], lock_version: noe.lock_version },
      ],
    ]);
  });

  it("refuses by the catalogue the withdrawal of her role from the last administrator, her role still checked [WF-ADM-0120-A]", async () => {
    serve({
      "PUT /users/{user_id}/access-roles": {
        problem: example("user_access_roles_refused") as Problem & { status: 409 },
      },
    });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("button", { name: "Rôles de « Camille Martin »" }),
    );
    const list = await screen.findByRole("group", {
      name: "Rôles de « Camille Martin »",
    });
    const direction = roles.find((role) => role.id === DIRECTION)?.label ?? "";
    await userEvent.click(within(list).getByRole("checkbox", { name: direction }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Au moins un compte actif doit garder les permissions d’administration.",
    );
    expect(within(list).getByRole("checkbox", { name: direction })).toBeChecked();
  });

  it("writes the roles of an account deactivated before the page is read anew from the version the deactivation answered", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": "user_deactivated",
      "PUT /users/{user_id}/access-roles": {
        problem: { code: "STALE_LOCK_VERSION", status: 412 },
      },
    });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de « Noé Vidal » actif" }),
    );
    await waitFor(() => {
      expect(told().textContent).toBe("« Noé Vidal » désactivé.");
    });
    await userEvent.click(within(grid()).getByRole("button", { name: "Rôles de « Noé Vidal »" }));
    const list = await screen.findByRole("group", { name: "Rôles de « Noé Vidal »" });
    await userEvent.click(within(list).getByRole("checkbox", { name: "Chiffreur" }));
    await waitFor(() => {
      expect(writes(client)).toHaveLength(2);
    });
    const deactivated = example("user_deactivated") as User;
    expect(writes(client)[1]?.[2]).toEqual({
      access_role_ids: [...deactivated.access_role_ids, CHIFFREUR],
      lock_version: deactivated.lock_version,
    });
  });

  it("opens the roles of the active cell on Enter, the grid one stop of the tabulation, and gives the focus back to the cell on Escape", async () => {
    render(accounts());
    const trigger = within(grid()).getByRole("button", {
      name: "Rôles de « Lucas Petit »",
    });
    expect(trigger).toHaveAttribute("tabindex", "-1");
    const cell = trigger.closest("td") as HTMLElement;
    cell.focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByRole("group", { name: "Rôles de « Lucas Petit »" }),
    ).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(cell).toHaveFocus();
    });
  });
});

describe("the creation of a local account", () => {
  it("creates an account from its names and its address, trimmed, says so, and reads the page anew", async () => {
    const client = serve({ "POST /users": { status: 201, example: "user_created_invited" } });
    render(accounts());
    await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
    const form = await screen.findByRole("form", { name: "Créer un compte local" });
    await userEvent.type(within(form).getByLabelText("Nom"), " Garnier ");
    await userEvent.type(within(form).getByLabelText("Prénom"), "Léa");
    await userEvent.type(
      within(form).getByLabelText("Adresse électronique"),
      "lea.garnier@example.com",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Compte « Léa Garnier » créé.");
    });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Créer un compte local" })).toHaveFocus();
    expect(writes(client)).toEqual([
      [
        "POST /users",
        "/users",
        { last_name: "Garnier", first_name: "Léa", email: "lea.garnier@example.com" },
      ],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("offers at once the link of an account created that no invitation went to, and gives it once asked", async () => {
    const client = serve({
      "POST /users": { status: 201, example: "user_created" },
      "POST /users/{user_id}/password-link": { status: 201, example: "password_setup_link" },
    });
    render(accounts());
    await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
    const form = await screen.findByRole("form", { name: "Créer un compte local" });
    await userEvent.type(within(form).getByLabelText("Nom"), "Garnier");
    await userEvent.type(within(form).getByLabelText("Prénom"), "Léa");
    await userEvent.type(within(form).getByLabelText("Adresse électronique"), "l@example.com");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const offer = await screen.findByRole("button", { name: "Remettre le lien" });
    await waitFor(() => {
      expect(offer).toHaveFocus();
    });
    expect(told().textContent).toBe(
      "Compte «\u00a0Léa Garnier\u00a0» créé\u00a0; aucune invitation n’est partie\u00a0: remettez-lui son lien de fixation.",
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleDescription(/aucune invitation/);
    await userEvent.click(offer);
    const dialog = await screen.findByRole("dialog", {
      name: "Lien de fixation du mot de passe de «\u00a0Léa Garnier\u00a0»",
    });
    expect(within(dialog).getByRole("textbox", { name: "Lien" })).toHaveValue(
      (example("password_setup_link") as Schemas["PasswordSetupLink"]).url,
    );
    const lea = example("user_created") as User;
    expect(writes(client).map(([, path]) => path)).toEqual([
      "/users",
      `/users/${lea.user_id}/password-link`,
    ]);
  });

  it.each([
    ["user_created_invited", "Compte «\u00a0Léa Garnier\u00a0» créé."],
    [
      "user_created",
      "Compte «\u00a0Léa Garnier\u00a0» créé\u00a0; aucune invitation n’est partie\u00a0: remettez-lui son lien de fixation.",
    ],
  ] as const)(
    "keeps the creation opened anew while the one closed before it is answered, its entry kept — %s",
    async (created, said) => {
      const held = holdRoute("POST /users");
      const client = serve({ "POST /users": { status: 201, example: created } }, held.timing);
      render(accounts());
      await createGarnier(await openCreation());
      await waitFor(() => {
        expect(writes(client)).toHaveLength(1);
      });
      await userEvent.keyboard("{Escape}");
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
      const form = await openCreation();
      await userEvent.type(within(form).getByLabelText("Nom"), "Petit");
      held.release();
      await waitFor(() => {
        expect(told().textContent).toBe(said);
      });
      expect(screen.getByRole("form", { name: "Créer un compte local" })).toBe(form);
      expect(within(form).getByLabelText("Nom")).toHaveValue("Petit");
      expect(writes(client)).toHaveLength(1);
    },
  );

  it("refuses at their fields a name left blank and an address left empty, and asks nothing [WF-ADM-0050-A]", async () => {
    const client = serve({});
    render(accounts());
    await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
    const form = await screen.findByRole("form", { name: "Créer un compte local" });
    await userEvent.type(within(form).getByLabelText("Nom"), "   ");
    await userEvent.type(within(form).getByLabelText("Prénom"), "Léa");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const last = within(form).getByLabelText("Nom");
    expect(last).toHaveFocus();
    expect(last).toHaveAttribute("aria-invalid", "true");
    expect(last).toHaveAccessibleDescription(CATALOGUES.fr.errors.VALUE_REQUIRED);
    expect(within(form).getByLabelText("Adresse électronique")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(within(form).getByLabelText("Prénom")).not.toHaveAttribute("aria-invalid");
    expect(writes(client)).toEqual([]);
  });

  it("says at its field the address another account holds, the dialog open to correct it [WF-ADM-0050-A]", async () => {
    serve({
      "POST /users": { problem: example("user_email_taken") as Problem & { status: 409 } },
    });
    render(accounts());
    await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
    const form = await screen.findByRole("form", { name: "Créer un compte local" });
    await userEvent.type(within(form).getByLabelText("Nom"), "Petit");
    await userEvent.type(within(form).getByLabelText("Prénom"), "Lucas");
    await userEvent.type(
      within(form).getByLabelText("Adresse électronique"),
      "lucas.petit@example.com",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const email = within(form).getByLabelText("Adresse électronique");
    await waitFor(() => {
      expect(email).toHaveFocus();
    });
    expect(email).toHaveAccessibleDescription(CATALOGUES.fr.errors.ALREADY_EXISTS);
    expect(within(form).queryByRole("alert")).toBeNull();
  });
});

describe("the link to set the password", () => {
  it("gives the link of a local account in a dialog, whole and selected, with the instant it ceases to be valid; the focus back on its cell once closed", async () => {
    const client = serve({
      "POST /users/{user_id}/password-link": { status: 201, example: "password_setup_link" },
    });
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de « Camille Martin »",
    });
    await userEvent.click(command);
    const dialog = await screen.findByRole("dialog", {
      name: "Lien de fixation du mot de passe de « Camille Martin »",
    });
    const link = (example("password_setup_link") as Schemas["PasswordSetupLink"]).url;
    const field = within(dialog).getByRole("textbox", { name: "Lien" });
    expect(field).toHaveValue(link);
    expect(field).toHaveAttribute("readonly");
    expect(dialog.querySelector("time")).toHaveAttribute("datetime", "2026-06-03T15:05:00Z");
    expect(writes(client).map(([, path]) => path)).toEqual([
      `/users/${account("Martin").user_id}/password-link`,
    ]);
    await userEvent.click(within(dialog).getByRole("button", { name: "Fermer" }));
    await waitFor(() => {
      expect(command.closest("td")).toHaveFocus();
    });
  });

  it("presents the link of a deactivated local account unavailable, naming the condition it lacks, and asks nothing", async () => {
    const client = serve({});
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de « Alix Moreau »",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription("Condition non remplie : compte actif.");
    await userEvent.click(command);
    expect(told().textContent).toBe(
      "Lien de fixation du mot de passe de « Alix Moreau » : Condition non remplie : compte actif.",
    );
    expect(writes(client)).toEqual([]);
  });

  it("marks the link of an account busy and unavailable while its deactivation is asked, a press asking nothing", async () => {
    const held = heldActivation();
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" }, held.timing);
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de «\u00a0Noé Vidal\u00a0»",
    });
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de «\u00a0Noé Vidal\u00a0» actif" }),
    );
    await waitFor(() => {
      expect(command).toHaveAttribute("aria-busy", "true");
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    held.release();
    // Deactivated, the account is given no link: the command stays unavailable.
    await waitFor(() => {
      expect(command).toHaveAttribute("aria-busy", "false");
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(writes(client).map(([route]) => route)).toEqual(["PUT /users/{user_id}/activation"]);
  });
});

describe("the filters of the table", () => {
  it("are kept with the settings of the grid, as the page shows them [WF-IHM-0060-A]", async () => {
    page.search = "search=Mor&origins=local&is_active=false&offset=2";
    render(accounts(false, users.items, { hidden_columns: [], column_widths: {} }));
    const client = server.client as FakeClient;
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual(["PATCH /me/preferences"]);
    });
    expect(client.calls[0]?.body).toEqual({
      grids: {
        users: {
          hidden_columns: [],
          column_widths: {},
          filters: { search: "Mor", origins: "local", is_active: "false" },
        },
      },
    });
  });
});
