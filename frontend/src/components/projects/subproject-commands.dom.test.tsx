// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import type { Subproject } from "./settings-grids";
import { SubprojectList } from "./settings-lists";

// The server of Next, as far as the list needs it: the fake back, the page read anew once a write is
// answered, the address it reads.
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

type Problem = components["schemas"]["Problem"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const CREATE = "POST /projects/{project_id}/subprojects";
const UPDATE = "PATCH /projects/{project_id}/subprojects/{subproject_id}";
const DELETE = "DELETE /projects/{project_id}/subprojects/{subproject_id}";
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };
const SUBPROJECTS = example("subprojects") as Subproject[];
// Both sub-projects of the example are charged with actual costs and cited by the reference revision
// (EP-14/L45a, L42l): none deletes. The one a test deletes is a counterfactual variant of the
// sub-project created (`subproject_created`), « SP-REC », which no marked revision cites, relieved of
// its costs and its deletion listed available as the server would then list it, the rest of the
// example kept; it is listed after the two of `subprojects`.
const CREATED = example("subproject_created") as Subproject;
const DELETABLE: Subproject[] = [
  ...SUBPROJECTS,
  {
    ...CREATED,
    has_actual_costs: false,
    available_commands: CREATED.available_commands.map((each) =>
      each.command === "delete" ? { ...each, is_available: true, missing_conditions: [] } : each,
    ),
  },
];

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({
    [CREATE]: { example: "subproject_created", status: 201 },
    [UPDATE]: "subproject_updated",
    [DELETE]: { status: 204 },
    ...answers,
  });
  server.client = client;
  return client;
}

/** The list of the sub-projects, in French, as the project lists `update` — or does not. */
function list(offer: CommandOffer | null = AVAILABLE, rows = SUBPROJECTS) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <SubprojectList
          subprojects={rows}
          editing={{ project: PROJECT, offer: offer ?? undefined }}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The calls the list made of the fake back. */
function writes(client: FakeClient) {
  return client.calls.map(({ route, path, body }) => ({ route, path, body }));
}

/** What the regions of the list announce. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The grid of the sub-projects. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Sous-projets" });
}

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

describe("the creation and the modification of a sub-project", () => {
  it("creates a sub-project from a project that has none, its code and its label required before anything is asked [WF-PRJ-0050-A]", async () => {
    const client = serve();
    const { container } = render(list(AVAILABLE, []));
    // Un projet se chiffre sans aucun sous-projet : the list says so, and offers to create one.
    expect(screen.getByText("Ce projet n’a aucun sous-projet.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Nouveau sous-projet" }));
    const form = screen.getByRole("dialog", { name: "Nouveau sous-projet" });
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const code = within(form).getByRole("textbox", { name: "Code ERP" });
    expect(code).toHaveAccessibleDescription("Une valeur est requise.");
    expect(code).toHaveFocus();
    expect(client.calls).toEqual([]);
    await userEvent.type(code, " SP-REC ");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Réception");
    await expectAccessible(container);
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)).toEqual([
      {
        route: CREATE,
        path: `/projects/${PROJECT}/subprojects`,
        body: { code: "SP-REC", label: "Réception" },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(announced()).toContain("« SP-REC » créé.");
  });

  it("modifies a sub-project from the version read, and shows its row as the server answered it", async () => {
    const client = serve();
    render(list());
    await userEvent.click(within(grid()).getByRole("button", { name: "Modifier « SP-ESS »" }));
    const form = screen.getByRole("dialog", { name: "Modifier « SP-ESS »" });
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    expect(label).toHaveValue("Essais et mise en service");
    await userEvent.clear(label);
    await userEvent.type(label, "Essais, mise en service et réception");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(writes(client)[0]?.body).toEqual({
      code: "SP-ESS",
      label: "Essais, mise en service et réception",
      lock_version: 1,
    });
    expect(within(grid()).getByRole("row", { name: /^SP-ESS/ })).toHaveTextContent(
      "Essais, mise en service et réception",
    );
    expect(announced()).toContain("« SP-ESS » enregistré.");
  });

  it("tells the modification of a sub-project answered for another one as a failure of the service, the form kept open", async () => {
    const client = serve();
    render(list());
    // The example answers « SP-ESS », whatever sub-project was modified: here « SP-CMD ».
    await userEvent.click(within(grid()).getByRole("button", { name: "Modifier « SP-CMD »" }));
    const form = screen.getByRole("dialog", { name: "Modifier « SP-CMD »" });
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Erreur inattendue du service.",
    );
    expect(client.calls).toHaveLength(1);
    // Nothing takes the place of any row: the form closed, « SP-ESS » keeps its label read,
    // and nothing is said saved.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(within(grid()).getByRole("row", { name: /^SP-ESS/ })).toHaveTextContent(
      "Essais et mise en service",
    );
    expect(within(grid()).getByRole("row", { name: /^SP-CMD/ })).toHaveTextContent(
      "Poste de commande",
    );
    expect(announced()).not.toContain("« SP-ESS » enregistré.");
    expect(announced()).not.toContain("« SP-CMD » enregistré.");
  });

  it("says at the code a code another sub-project of the project bears, the form kept to be corrected [WF-PRJ-0050-A]", async () => {
    serve({
      [UPDATE]: { problem: { ...(example("subproject_code_taken") as Problem), status: 409 } },
    });
    render(list());
    await userEvent.click(within(grid()).getByRole("button", { name: "Modifier « SP-ESS »" }));
    const form = screen.getByRole("dialog", { name: "Modifier « SP-ESS »" });
    const code = within(form).getByRole("textbox", { name: "Code ERP" });
    await userEvent.clear(code);
    await userEvent.type(code, "SP-CMD");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    // La création de deux sous-projets de même code dans un même projet est refusée.
    // Said at its field, which takes the focus — the holder named by the label the refusal gives it
    // (EP-14/L42i), the form not knowing the rows the list shows —; the refusal is not told again
    // under the form.
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAttribute("aria-invalid", "true");
    expect(code).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par « Poste de commande ».",
    );
    expect(within(form).queryByRole("alert")).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the version stale under the form, with the offer to read the page anew", async () => {
    serve({ [UPDATE]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } });
    render(list());
    await userEvent.click(within(grid()).getByRole("button", { name: "Modifier « SP-ESS »" }));
    const form = screen.getByRole("dialog", { name: "Modifier « SP-ESS »" });
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });
});

describe("the deletion of a sub-project", () => {
  it("deletes a sub-project once confirmed, saying which ones never delete, and takes its row away; cancelled, asks nothing", async () => {
    const client = serve();
    render(list(AVAILABLE, DELETABLE));
    const command = within(grid()).getByRole("button", { name: "Supprimer « SP-REC »" });
    await userEvent.click(command);
    const title = "Supprimer le sous-projet « SP-REC » ?";
    expect(screen.getByRole("dialog", { name: title })).toHaveAccessibleDescription(
      "Le sous-projet « SP-REC », Réception sur site, sera supprimé. " +
        "Un sous-projet auquel des coûts réels sont imputés, ou qu’une révision marquée cite, ne se " +
        "supprime pas.",
    );
    await userEvent.click(
      within(screen.getByRole("dialog", { name: title })).getByRole("button", { name: "Annuler" }),
    );
    expect(client.calls).toEqual([]);
    await userEvent.click(command);
    const confirmation = screen.getByRole("dialog", { name: title });
    await userEvent.click(within(confirmation).getByRole("button", { name: "Supprimer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)).toEqual([
      {
        route: DELETE,
        path: `/projects/${PROJECT}/subprojects/${CREATED.subproject_id}`,
        body: undefined,
      },
    ]);
    expect(within(grid()).queryByText("SP-REC")).toBeNull();
    expect(announced()).toContain("« SP-REC » supprimé.");
  });

  it("presents unavailable the deletion of a sub-project charged with actual costs and cited by a marked revision, as the row lists it, and asks nothing [WF-PRJ-0050-A]", async () => {
    const client = serve();
    render(list());
    // La suppression d'un sous-projet portant des coûts réels est refusée : the row lists `delete`
    // unavailable, `subproject_not_cited` and `subproject_without_actual_costs` lacking (EP-14/L42l).
    const unmet =
      "Conditions non remplies : sous-projet cité par aucune révision marquée et aucun coût " +
      "réel imputé au sous-projet.";
    const charged = within(grid()).getByRole("button", { name: "Supprimer « SP-CMD »" });
    expect(charged).toHaveAttribute("aria-disabled", "true");
    expect(charged).toHaveAccessibleDescription(unmet);
    await userEvent.click(charged);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(announced()).toContain(`Supprimer «\u00a0SP-CMD\u00a0»\u00a0: indisponible. ${unmet}`);
    expect(client.calls).toEqual([]);
  });

  it("tells above the list a deletion the server refuses, naming the first condition it misses", async () => {
    // Listed available on the reading, refused by the server, a marked revision citing the
    // sub-project meanwhile (§4.4.1, EP-14/L42l).
    serve({
      [DELETE]: { problem: { ...(example("subproject_delete_cited") as Problem), status: 409 } },
    });
    render(list(AVAILABLE, DELETABLE));
    await userEvent.click(within(grid()).getByRole("button", { name: "Supprimer « SP-REC »" }));
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Supprimer" }),
    );
    const refusal = await screen.findByRole("alert");
    expect(refusal).toHaveTextContent(
      "Condition non remplie : sous-projet cité par aucune révision marquée.",
    );
    expect(within(grid()).getByText("SP-REC")).toBeInTheDocument();
  });
});

describe("the commands a sub-project lists", () => {
  it("offers on a row only the commands it lists", () => {
    // A counterfactual variant of the example: « SP-CMD » listing no command, the rest kept.
    const rows: Subproject[] = SUBPROJECTS.map((row) =>
      row.code === "SP-CMD" ? { ...row, available_commands: [] } : row,
    );
    serve();
    render(list(AVAILABLE, rows));
    // The grid has no row header: the row is the one of the code's cell.
    const cmd = within(grid()).getByText("SP-CMD").closest("tr");
    expect(cmd).not.toBeNull();
    expect(within(cmd as HTMLElement).queryByRole("button")).toBeNull();
    expect(within(grid()).getByRole("button", { name: "Modifier « SP-ESS »" })).not.toHaveAttribute(
      "aria-disabled",
    );
  });
});

describe("the commands a project lists", () => {
  it("presents on a terminal project the creation and the commands of each row unavailable, naming the conditions, and asks nothing", async () => {
    // A counterfactual variant of the example, as the server lists the sub-projects of a terminal
    // project: each command unavailable, `project_not_terminal` last (EP-14/L42l), the rest kept.
    const rows: Subproject[] = SUBPROJECTS.map((row) => ({
      ...row,
      available_commands: row.available_commands.map((each) => ({
        ...each,
        is_available: false,
        missing_conditions: [...each.missing_conditions, "project_not_terminal" as const],
      })),
    }));
    const client = serve();
    render(list({ is_available: false, missing_conditions: ["project_not_terminal"] }, rows));
    const create = screen.getByRole("button", { name: "Nouveau sous-projet" });
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).toHaveAccessibleDescription("Condition non remplie : projet non clos.");
    const modify = within(grid()).getByRole("button", { name: "Modifier « SP-ESS »" });
    expect(modify).toHaveAttribute("aria-disabled", "true");
    expect(modify).toHaveAccessibleDescription("Condition non remplie : projet non clos.");
    const remove = within(grid()).getByRole("button", { name: "Supprimer « SP-ESS »" });
    expect(remove).toHaveAttribute("aria-disabled", "true");
    expect(remove).toHaveAccessibleDescription(
      "Conditions non remplies : sous-projet cité par aucune révision marquée, aucun coût " +
        "réel imputé au sous-projet et projet non clos.",
    );
    await userEvent.click(modify);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(announced()).toContain(
      `Modifier «\u00a0SP-ESS\u00a0»\u00a0: indisponible. Condition non remplie\u00a0: projet non clos.`,
    );
    expect(client.calls).toEqual([]);
  });

  it("offers nothing when the project lists no command `update`", () => {
    serve();
    render(list(null));
    expect(screen.queryAllByRole("button", { name: /Nouveau|Modifier|Supprimer/ })).toEqual([]);
  });
});
