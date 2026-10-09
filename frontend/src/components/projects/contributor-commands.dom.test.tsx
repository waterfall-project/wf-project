// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { CommandOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import type { ContributorReading, Suggestion } from "./contributor-commands";
import { ContributorList } from "./settings-lists";

// The server of Next, as far as the list needs it: the fake back, the page read anew once the list
// is written, the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/settings",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const SET = "PUT /projects/{project_id}/contributors";
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };
const WHOLE = example("contributors") as ContributorReading;
const SUGGESTIONS = example("contributor_suggestions") as Suggestion[];

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({ [SET]: "contributors_set", ...answers });
  server.client = client;
  return client;
}

/**
 * The list of the contributors, in French, read whole unless another reading is shown; `whole` is
 * the list the page read whole besides, which a write starts from.
 */
function list(
  offer: CommandOffer = AVAILABLE,
  shown: ContributorReading = WHOLE,
  whole: ContributorReading = WHOLE,
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ContributorList
          contributors={shown.items}
          editing={{
            project: PROJECT,
            offer,
            counter: shown.lock_version,
            whole,
            suggestions: SUGGESTIONS,
          }}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The bodies of the lists written. */
function written(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === SET).map((call) => call.body);
}

/** Open the modification of the list, and give back its dialog. */
async function modify(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: "Modifier les contributeurs" }));
  return screen.getByRole("dialog", { name: "Modifier les contributeurs" });
}

/** The rows of the grid of the contributors, their names. */
function names(): string[] {
  return within(screen.getByRole("grid", { name: "Contributeurs" }))
    .getAllByRole("row")
    .slice(1, -1)
    .map((row) => row.querySelector('[data-column="name"]')?.textContent ?? "");
}

/** The account of an identifier of the witness. */
const user = (number: number) => `01926f3a-7c00-7000-8000-000000000${String(number)}`;

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the modification of the contributors of a project", () => {
  it("writes the whole list with its counter, a capacity changed, and shows the list the server answered", async () => {
    const client = serve();
    const { container } = render(list());
    const form = await modify();
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Qualité de Inès Roux" }),
      "Chef de projet",
    );
    await expectAccessible(container);
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(written(client)).toEqual([
      {
        contributors: [
          { user_id: user(301), kind: "project_manager" },
          { user_id: user(303), kind: "contributor" },
          { user_id: user(305), kind: "contributor" },
          { user_id: user(306), kind: "project_manager" },
        ],
        lock_version: 4,
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(names()).toEqual([
      "Camille Martin",
      "Inès Roux",
      "Sacha Lefèvre",
      "Alix Moreau",
      "Lucas Petit",
    ]);
    expect(screen.getByRole("status")).toHaveTextContent("Liste des contributeurs enregistrée.");
  });

  it("inscribes a contributor proposed only once the project manager confirms it, the list unchanged until then [WF-PRJ-0070-A]", async () => {
    const client = serve();
    render(list());
    expect(screen.getByText(/Proposé d’après les rôles du devis/)).toHaveTextContent(
      "Sacha Lefèvre",
    );
    let form = await modify();
    expect(within(form).getByRole("region", { name: "Contributeurs proposés" })).toHaveTextContent(
      "Sacha Lefèvre",
    );
    // Tant que la proposition n'est pas confirmée, la liste est inchangée.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toEqual([]);
    expect(names()).not.toContain("Sacha Lefèvre");
    form = await modify();
    await userEvent.click(within(form).getByRole("button", { name: "Inscrire Sacha Lefèvre" }));
    expect(within(form).queryByRole("region", { name: "Contributeurs proposés" })).toBeNull();
    expect(within(form).getByRole("combobox", { name: "Qualité de Sacha Lefèvre" })).toHaveValue(
      "contributor",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    const [body] = written(client) as { contributors: unknown[] }[];
    expect(body?.contributors).toContainEqual({ user_id: user(304), kind: "contributor" });
    // Inscribed, as the list answered counts him, Sacha is proposed no more under the list.
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(names()).toContain("Sacha Lefèvre");
    expect(screen.queryByText(/Proposé d’après les rôles du devis/)).toBeNull();
  });

  it("refuses before asking a list without a project manager, and accepts it once a second one is inscribed [WF-PRJ-0060-A]", async () => {
    const client = serve();
    render(list());
    const form = await modify();
    // Le retrait du seul chef de projet d'un projet est refusé, de même que son passage en
    // participant ; il est accepté dès qu'un second chef de projet est inscrit.
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Qualité de Camille Martin" }),
      "Contributeur",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "Un projet garde au moins un chef de projet.",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Retirer Camille Martin" }));
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "Un projet garde au moins un chef de projet.",
    );
    expect(client.calls).toEqual([]);
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Qualité de Lucas Petit" }),
      "Chef de projet",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]).toMatchObject({
      contributors: [
        { user_id: user(303), kind: "contributor" },
        { user_id: user(305), kind: "project_manager" },
        { user_id: user(306), kind: "contributor" },
      ],
    });
  });

  it("says a refusal by field at the row of the account it points at, naming it, and the rest under the form", async () => {
    serve({
      [SET]: {
        problem: {
          code: "VALIDATION_FAILED",
          status: 422,
          fields: [
            { pointer: "/contributors/1/user_id", code: "INACTIVE_REFERENCE_OBJECT" },
            { pointer: "/lock_version", code: "VALUE_REQUIRED" },
          ],
        },
      },
    });
    render(list());
    const form = await modify();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const capacity = within(form).getByRole("combobox", { name: "Qualité de Alix Moreau" });
    await vi.waitFor(() => {
      expect(capacity).toHaveAttribute("aria-invalid", "true");
    });
    expect(capacity).toHaveAccessibleDescription(
      "Alix Moreau : Cet élément du référentiel est désactivé.",
    );
    expect(capacity).toHaveFocus();
    // What points at no row is told under the form, without the row said already.
    const alert = within(form).getByRole("alert");
    expect(alert).toHaveTextContent("Les données saisies ne sont pas valides.");
    expect(alert).not.toHaveTextContent("désactivé");
  });

  it("says under the form what the server refuses as a whole, the form kept", async () => {
    serve({ [SET]: { problem: { code: "LAST_PROJECT_MANAGER", status: 409 } } });
    render(list());
    const form = await modify();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Un projet garde au moins un chef de projet.",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("writes from the list read whole while the grid shows a reading filtered, which keeps its rows", async () => {
    const client = serve();
    render(list(AVAILABLE, example("contributors_search") as ContributorReading));
    expect(names()).toEqual(["Lucas Petit"]);
    const form = await modify();
    expect(within(form).getAllByRole("combobox")).toHaveLength(4);
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]).toMatchObject({ lock_version: 4 });
    // A reading filtered shows what it retains, never the whole list answered.
    expect(names()).toEqual(["Lucas Petit"]);
  });

  it("writes from the reading the dialog was opened on, a newer one read while it is open neither shown nor sent", async () => {
    const client = serve();
    const view = render(list());
    const form = await modify();
    expect(within(form).getAllByRole("combobox")).toHaveLength(4);
    // The page is read anew while the dialog is open: a fifth version, a fifth contributor.
    const reread = example("contributors_set") as ContributorReading;
    view.rerender(list(AVAILABLE, reread, reread));
    expect(within(form).getAllByRole("combobox")).toHaveLength(4);
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]).toMatchObject({ lock_version: 4 });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(names()).toHaveLength(5);
    // Opened again, the dialog starts from the reading newer.
    expect(within(await modify()).getAllByRole("combobox")).toHaveLength(5);
  });

  it("presents the command unavailable with the conditions it lacks, and opens nothing", async () => {
    serve();
    render(list({ is_available: false, missing_conditions: ["is_project_manager"] }));
    const command = screen.getByRole("button", { name: "Modifier les contributeurs" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription("Condition non remplie : être chef de projet.");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
