// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { cleanup, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { Project } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
} from "@/test/fixtures";

import { CreateProject, ProjectIdentity } from "./project-form";

// The server of Next, as far as the forms need it: the fake back, the page rendered again once the
// project is modified, and the navigations they ask.
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

const CREATE = "POST /projects";
const UPDATE = "PATCH /projects/{project_id}";
const witness = example("project") as Project;
const pricing = example("project_pricing") as Project;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [CREATE]: { example: "project_created", status: 201 },
      [UPDATE]: "project_updated",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** A part of the screen, in French. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** The open dialog, by its name. */
function dialog(name: string): HTMLElement {
  return screen.getByRole("dialog", { name });
}

/** Open the creation of a project, and give its form back. */
async function openCreation(): Promise<HTMLElement> {
  render(inFrench(<CreateProject ready />));
  await userEvent.click(screen.getByRole("button", { name: "Créer un projet" }));
  return dialog("Créer un projet");
}

/** Open the modification of a project, and give its form back. */
async function openModification(project: Project = witness): Promise<HTMLElement> {
  render(inFrench(<ProjectIdentity project={project} />));
  await userEvent.click(screen.getByRole("button", { name: "Modifier le projet" }));
  return dialog(`Modifier «\u00a0${project.label}\u00a0»`);
}

afterEach(() => {
  refresh.mockClear();
  router.push.mockClear();
  router.refresh.mockClear();
});

describe("the creation of a project", () => {
  it("refuses a project without a label before asking anything, the label taking the focus [WF-PRJ-0080-A]", async () => {
    // La création d'un projet sans libellé est refusée.
    const client = serve();
    const form = await openCreation();
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    expect(label).toHaveFocus();
    expect(label).toHaveAttribute("aria-invalid", "true");
    expect(label).toHaveAccessibleDescription("Une valeur est requise.");
    expect(client.calls).toEqual([]);
  });

  it("creates a project without a code, which waits for the order, and leads to the project the server created [WF-PRJ-0010-A]", async () => {
    // Un projet se crée et se chiffre sans code projet.
    const client = serve();
    const form = await openCreation();
    expect(within(form).getByRole("textbox", { name: "Code projet" })).not.toHaveAttribute(
      "aria-required",
    );
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      " Rénovation du poste de livraison ",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(router.push).toHaveBeenCalledWith("/projects/01926f3a-7c00-7000-8000-000000000003");
    });
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      {
        route: CREATE,
        body: { label: "Rénovation du poste de livraison", code: null, description: null },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("tells under the form each prerequisite a refusal names, the minimum reference data incomplete meanwhile [WF-CYC-0120-A]", async () => {
    serve({
      [CREATE]: {
        problem: {
          code: "REFERENCE_INCOMPLETE",
          status: 409,
          params: { missing_prerequisites: ["active_cost_category", "active_resource_role"] },
        },
      },
    });
    const form = await openCreation();
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Rénovation");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const refusal = await within(form).findByRole("alert");
    expect(refusal).toHaveTextContent("Le référentiel minimal est incomplet.");
    expect(refusal).toHaveTextContent(/catégorie de coût active.*rôle de ressource actif/);
    expect(router.push).not.toHaveBeenCalled();
  });

  it("leads nowhere once the home is gone: a creation answered after the user left does not take the place of their navigation", async () => {
    const settles: (() => void)[] = [];
    const until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    const client = serve({}, { hold: () => until });
    const { unmount } = render(inFrench(<CreateProject ready />));
    await userEvent.click(screen.getByRole("button", { name: "Créer un projet" }));
    const form = dialog("Créer un projet");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Rénovation");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    unmount();
    for (const settle of settles) {
      settle();
    }
    // The answer arrives, and is left to fall: nothing navigates.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(router.push).not.toHaveBeenCalled();
  });

  it("presents the creation unavailable while the reference data is incomplete: pressed, it opens nothing", async () => {
    const client = serve();
    render(inFrench(<CreateProject ready={false} />));
    const create = screen.getByRole("button", { name: "Créer un projet" });
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).toHaveAccessibleDescription("Le référentiel minimal est incomplet.");
    await userEvent.click(create);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
  });
});

describe("the modification of a project", () => {
  it("modifies the identity and the facts of the project from the version read, shows the answer in place of the reading, and reads the page anew [WF-PRJ-0080-A]", async () => {
    // La date de réception de la commande est saisissable à tout moment et n'est exigée par
    // aucune transition : offerte au projet en cours, et laissée vide, elle part nulle.
    const client = serve();
    const form = await openModification();
    // Under the modal dialog, the rest of the screen is hidden from a reader of the screen.
    expect(screen.getByRole("note", { hidden: true })).toHaveTextContent(
      "le service simulé répond",
    );
    expect(within(form).getByLabelText("Commande reçue le")).not.toHaveAttribute("aria-required");
    await userEvent.clear(within(form).getByLabelText("Commande reçue le"));
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Description" }),
      "Remplacement des automates et de la supervision du poste de commande.",
    );
    const inflation = within(form).getByRole("textbox", { name: "Taux d’inflation annuel (%)" });
    expect(inflation).toHaveValue("3");
    await userEvent.clear(inflation);
    await userEvent.type(inflation, "3,5");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(client.calls.map(({ route, path, body }) => ({ route, path, body }))).toEqual([
      {
        route: UPDATE,
        path: `/projects/${witness.project_id}`,
        body: {
          label: witness.label,
          code: "PRJ-001",
          description: "Remplacement des automates et de la supervision du poste de commande.",
          order_received_on: null,
          inflation_rate: "0.035",
          lock_version: 7,
        },
      },
    ]);
    // The answer of the server, newer than the reading, takes its place.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(
      screen.getAllByRole("status").find((region) => region.textContent !== ""),
    ).toHaveTextContent("Paramètres du projet enregistrés.");
    expect(screen.getByLabelText("Paramètres du projet")).toHaveTextContent(
      "DescriptionRemplacement des automates et de la supervision du poste de commande.",
    );
    expect(screen.getByRole("button", { name: "Modifier le projet" })).toHaveFocus();
    await expectAccessible(document.body);
  });

  it("refuses a date half entered before asking anything, rather than sending none", async () => {
    // A date control half entered gives an empty text, which it says is no date (`badInput`).
    const client = serve();
    const form = await openModification();
    const received = within(form).getByLabelText("Commande reçue le");
    await userEvent.clear(received);
    Object.defineProperty(received, "validity", { value: { badInput: true }, configurable: true });
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(received).toHaveAttribute("aria-invalid", "true");
    expect(received).toHaveAccessibleDescription("Ce n’est pas une date valide.");
    expect(received).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("keeps the answer through a reading anew of the version it answered, and gives way to a newer reading, which the form writes from (défaut n° 22)", async () => {
    const client = serve();
    const { rerender } = render(inFrench(<ProjectIdentity project={witness} />));
    await userEvent.click(screen.getByRole("button", { name: "Modifier le projet" }));
    await userEvent.click(
      within(dialog(`Modifier «\u00a0${witness.label}\u00a0»`)).getByRole("button", {
        name: "Enregistrer",
      }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    const answered = "Remplacement des automates et de la supervision du poste de commande.";
    // The page read anew serves the version 7 again — the fake back keeps nothing: the answer stays.
    rerender(inFrench(<ProjectIdentity project={witness} />));
    expect(screen.getByLabelText("Paramètres du projet")).toHaveTextContent(answered);
    // A reading newer than the answer prevails, and the form writes from it.
    const newer = { ...witness, lock_version: 9, description: "Supervision seule." };
    rerender(inFrench(<ProjectIdentity project={newer} />));
    const facts = screen.getByLabelText("Paramètres du projet");
    expect(facts).toHaveTextContent("Supervision seule.");
    expect(facts).not.toHaveTextContent(answered);
    await userEvent.click(screen.getByRole("button", { name: "Modifier le projet" }));
    await userEvent.click(
      within(dialog(`Modifier «\u00a0${witness.label}\u00a0»`)).getByRole("button", {
        name: "Enregistrer",
      }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({
      description: "Supervision seule.",
      lock_version: 9,
    });
  });

  it("writes from the version it opened on, not from a reading that came while it was open: the optimistic lock is not bypassed", async () => {
    // Opened on the version 7, the form keeps writing it even once the page, read anew behind the
    // dialog, shows the version 9: the draft was entered on the version 7, and the server must say
    // so (412), rather than take it for a modification of the version 9.
    const client = serve();
    const { rerender } = render(inFrench(<ProjectIdentity project={witness} />));
    await userEvent.click(screen.getByRole("button", { name: "Modifier le projet" }));
    const form = dialog(`Modifier «\u00a0${witness.label}\u00a0»`);
    await userEvent.type(within(form).getByRole("textbox", { name: "Description" }), "Brouillon.");
    rerender(
      inFrench(
        <ProjectIdentity
          project={{ ...witness, lock_version: 9, description: "Supervision seule." }}
        />,
      ),
    );
    expect(within(form).getByRole("textbox", { name: "Description" })).toHaveValue("Brouillon.");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({ description: "Brouillon.", lock_version: 7 });
  });

  it("freezes the probability of winning from the state in progress, saying why, and offers it before, entered as a percentage [WF-PRJ-0090-A]", async () => {
    // La modification de la probabilité est refusée à partir de l'état En cours.
    const client = serve();
    const progress = await openModification();
    expect(within(progress).queryByRole("textbox", { name: "Probabilité de gain (%)" })).toBeNull();
    expect(progress).toHaveAccessibleDescription(
      /La probabilité de gain ne se modifie plus une fois le projet en cours\./,
    );
    cleanup();

    const offer = await openModification(pricing);
    const probability = within(offer).getByRole("textbox", { name: "Probabilité de gain (%)" });
    expect(probability).toHaveValue("40");
    await userEvent.clear(probability);
    await userEvent.type(probability, "45");
    await userEvent.click(within(offer).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({ win_probability: "0.45", lock_version: 2 });
  });

  it("tells a code another project bears, the form open to correct it [WF-PRJ-0010-A]", async () => {
    // La saisie d'un code déjà porté par un autre projet est refusée.
    serve({
      [UPDATE]: {
        problem: {
          code: "ALREADY_EXISTS",
          status: 409,
          fields: [
            {
              pointer: "/code",
              code: "ALREADY_EXISTS",
              params: { conflicting_object_id: pricing.project_id },
            },
          ],
        },
      },
    });
    const form = await openModification();
    const code = within(form).getByRole("textbox", { name: "Code projet" });
    await userEvent.clear(code);
    await userEvent.type(code, "PRJ-002");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    // Said at its field (EP-02/L42g), which takes the focus — the holder named generically, the
    // screen not showing the other projects —; nothing is shown as written, and the code typed stays
    // to be corrected.
    await vi.waitFor(() => {
      expect(code).toHaveFocus();
    });
    expect(code).toHaveAttribute("aria-invalid", "true");
    expect(code).toHaveAccessibleDescription(
      "Cet élément existe déjà. Déjà porté par un autre projet.",
    );
    expect(code).toHaveValue("PRJ-002");
    // Said at its field, the refusal is not told again under the form.
    expect(within(form).queryByRole("alert")).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the version stale under the form, and offers to read the page anew", async () => {
    serve({
      [UPDATE]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 8 } },
      },
    });
    const form = await openModification();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("tells a failure of the service when the server answers the modification of another project", async () => {
    serve({ [UPDATE]: "project_updated" });
    const form = await openModification({ ...pricing, label: "Extension" });
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(/inattendue/);
    expect(screen.queryByText("Paramètres du projet enregistrés.")).toBeNull();
  });
});
