// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import {
  type DesignatedRevision,
  ReferenceDesignation,
} from "@/components/revisions/revision-history";
import { RateUpdate } from "@/components/revisions/revision-parts";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { RevisionCommands } from "./object-commands";

// The server of Next, as far as these commands need it: the fake back behind serverClient, the
// render of the page again once a write is answered, and the router that leads the screen.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), push: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

type Problem = components["schemas"]["Problem"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const DRAFT = "01926f3a-7c00-7000-8000-000000000102";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const CREATED = "01926f3a-7c00-7000-8000-000000000103";
const REVISIONS = `/projects/${PROJECT}/revisions`;
const CREATE = "POST /projects/{project_id}/revisions";
const ABANDON = "DELETE /projects/{project_id}/revisions/{revision_id}";
const DESIGNATE = "PUT /projects/{project_id}/reference-revision";
const RATES = "POST /projects/{project_id}/revisions/{revision_id}/rate-update";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Render, in French, what a screen of the revisions shows of the cycle. */
function show(children: ReactNode) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>{children}</main>
    </NextIntlClientProvider>,
  );
}

/** The commands of the screen: the project's opening, and the current revision's. */
function commands(project = "project") {
  return (
    <RevisionCommands
      revision={example("revision") as Revision}
      project={example(project) as Project}
    />
  );
}

/** The history of an example of the contract, each revision with the commands it lists. */
function history(name: string): DesignatedRevision[] {
  return (example(name) as { items: DesignatedRevision[] }).items;
}

/** The refusal (409) of an example of the contract, as the fake back answers it. */
function refused(name: string) {
  return { problem: { ...(example(name) as Problem), status: 409 as const } };
}

/** The calls the fake back received for an operation, their bodies. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  vi.mocked(refresh).mockClear();
  router.push.mockClear();
  router.refresh.mockClear();
  router.replace.mockClear();
  server.client = undefined;
});

describe("the opening of the current revision", () => {
  it("is offered as the project lists it, and leads to the revision created [WF-REV-0010-A]", async () => {
    const client = serve({ [CREATE]: { example: "revision_created", status: 201 } });
    show(
      <RevisionCommands
        revision={undefined}
        project={example("project_without_current_revision") as Project}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir une révision en cours" }));

    expect(bodies(client, CREATE)).toEqual([{ apply_rate_update: false }]);
    expect(router.push).toHaveBeenCalledWith(`${REVISIONS}?revision_id=${CREATED}`);
    expect(refresh).toHaveBeenCalled();
  });

  it("is refused while a revision is current: unavailable, naming its condition, and nothing is asked [WF-REV-0010-A]", async () => {
    const client = serve({});
    show(commands());
    const create = screen.getByRole("button", { name: "Ouvrir une révision en cours" });
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).toHaveAccessibleDescription(/^Condition non remplie\s: /);
    await userEvent.click(create);
    expect(client.calls).toHaveLength(0);
    expect(router.push).not.toHaveBeenCalled();
  });

  it("tells the refusal of a second current revision the server opposes anyway [WF-REV-0010-A]", async () => {
    serve({
      [CREATE]: {
        problem: {
          code: "STATE_FORBIDS_OPERATION",
          status: 409 as const,
          params: { missing_condition: "no_current_revision" },
        },
      },
    });
    show(
      <RevisionCommands
        revision={undefined}
        project={example("project_without_current_revision") as Project}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir une révision en cours" }));
    expect((await screen.findByRole("alert")).textContent).toContain("aucune révision en cours");
    expect(router.push).not.toHaveBeenCalled();
  });
});

describe("the abandon of the current revision", () => {
  it("asks for a confirmation that says the return to the last marked revision and that it is irreversible", async () => {
    const client = serve({ [ABANDON]: { status: 204 } });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    const form = screen.getByRole("form", { name: "Abandonner la révision en cours" });
    expect(form).toHaveTextContent("dernière révision marquée");
    expect(form).toHaveTextContent("irréversible");
    expect(client.calls).toHaveLength(0);
    await expectAccessible(form);

    // Cancelled, nothing is asked and the focus is back on the command.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form", { name: "Abandonner la révision en cours" })).toBeNull();
    expect(screen.getByRole("button", { name: "Abandonner la révision en cours" })).toHaveFocus();
    expect(client.calls).toHaveLength(0);
  });

  it("abandons the revision once confirmed, says so, and leaves its address for the revisions [WF-REV-0010-A]", async () => {
    const client = serve({ [ABANDON]: { status: 204 } });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));

    expect(client.calls.filter((call) => call.route === ABANDON).map((call) => call.path)).toEqual([
      `/projects/${PROJECT}/revisions/${DRAFT}`,
    ]);
    expect(await screen.findByRole("status")).toHaveTextContent("dernière révision marquée");
    expect(router.replace).toHaveBeenCalledWith(REVISIONS);
  });

  it("tells the refusal and stays on the revision", async () => {
    serve({
      [ABANDON]: {
        problem: {
          code: "STATE_FORBIDS_OPERATION",
          status: 409 as const,
          params: { missing_condition: "revision_draft" },
        },
      },
    });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(router.replace).not.toHaveBeenCalled();
    expect(screen.getByRole("form", { name: "Abandonner la révision en cours" })).toBeVisible();
  });
});

describe("the designation of the reference", () => {
  it("is proposed as long as the reference can be corrected: on the marked revision the server lists it for, and that one alone [WF-REV-0040-A]", () => {
    // The offer v1.0 is marked and lists it available, lacking nothing; the revision 101, current and
    // not marked, is left out.
    const listed = history("revisions_designation_open");
    expect(
      listed.find((revision) => revision.revision_id === OFFER)?.available_commands,
    ).toContainEqual({
      command: "designate_reference",
      is_available: true,
      missing_conditions: [],
    });
    show(<ReferenceDesignation revisions={listed} projectId={PROJECT} />);
    const offered = screen.getAllByRole("button", { name: "Désigner comme référence" });
    expect(offered).toHaveLength(1);
    expect(screen.queryByRole("listitem", { name: "Révision en cours" })).toBeNull();
    const offer = within(screen.getByRole("listitem", { name: "Offre v1.0" })).getByRole("button");
    expect(offer).toBe(offered[0]);
    expect(offer).not.toHaveAttribute("aria-disabled");
  });

  it("is refused once it no longer corrects: unavailable, naming the condition, and nothing is asked [WF-REV-0040-A]", async () => {
    for (const name of ["revisions", "revisions_marked"]) {
      const client = serve({});
      const { unmount } = show(
        <ReferenceDesignation revisions={history(name)} projectId={PROJECT} />,
      );
      // Every marked revision lists it, and none can take it.
      const offers = screen.getAllByRole("button", { name: "Désigner comme référence" });
      expect(offers).toHaveLength(2);
      for (const offer of offers) {
        expect(offer).toHaveAttribute("aria-disabled", "true");
        expect(offer).toHaveAccessibleDescription(
          /^Condition non remplie\s: référence encore corrigeable\.$/,
        );
        await userEvent.click(offer);
      }
      expect(client.calls).toHaveLength(0);
      expect(screen.queryByRole("form")).toBeNull();
      unmount();
    }
  });

  it("closes its confirmation once the server no longer lists it available, and does not reopen it with the command", async () => {
    const { rerender } = show(
      <ReferenceDesignation
        revisions={history("revisions_designation_open")}
        projectId={PROJECT}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Désigner comme référence" }));
    expect(screen.getByRole("form", { name: "Désigner comme référence" })).toBeVisible();

    const frame = (revisions: DesignatedRevision[]) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <main>
          <ReferenceDesignation revisions={revisions} projectId={PROJECT} />
        </main>
      </NextIntlClientProvider>
    );
    rerender(frame(history("revisions")));
    expect(screen.queryByRole("form")).toBeNull();
    rerender(frame(history("revisions_designation_open")));
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.getByRole("button", { name: "Désigner comme référence" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("says what it fixes and that the project goes in progress, then designates and says the new state [WF-REV-0040-A]", async () => {
    const client = serve({ [DESIGNATE]: { example: "reference_designated", status: 200 } });
    show(
      <ReferenceDesignation
        revisions={history("revisions_designation_open")}
        projectId={PROJECT}
      />,
    );
    await userEvent.click(
      within(screen.getByRole("listitem", { name: "Offre v1.0" })).getByRole("button"),
    );
    const form = screen.getByRole("form", { name: "Désigner comme référence" });
    expect(form).toHaveTextContent("budget de référence");
    expect(form).toHaveTextContent("valeur planifiée");
    expect(form).toHaveTextContent("« En cours »");
    expect(client.calls).toHaveLength(0);
    await expectAccessible(form);

    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    expect(bodies(client, DESIGNATE)).toEqual([{ revision_id: OFFER, confirmed: true }]);
    const row = screen.getByRole("listitem", { name: "Offre v1.0" });
    expect(await within(row).findByText(/est la révision de référence/)).toHaveTextContent(
      "« Offre v1.0 » est la révision de référence : le projet est à l’état « En cours ».",
    );
    // The page is read again: the banner, the commands and the read only of the estimate follow.
    expect(refresh).toHaveBeenCalled();
  });

  it("is refused by the server for a revision without task or line, naming the condition [WF-CYC-0030-A]", async () => {
    serve({ [DESIGNATE]: refused("reference_without_tasks") });
    show(
      <ReferenceDesignation
        revisions={history("revisions_designation_open")}
        projectId={PROJECT}
      />,
    );
    await userEvent.click(
      within(screen.getByRole("listitem", { name: "Offre v1.0" })).getByRole("button"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    const refusal = await screen.findByRole("alert");
    expect(refusal).toHaveTextContent("révision portant au moins une tâche et une ligne de devis");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("is refused by the server once the reference cannot be corrected [WF-REV-0040-A]", async () => {
    serve({ [DESIGNATE]: refused("reference_not_correctable") });
    show(
      <ReferenceDesignation
        revisions={history("revisions_designation_open")}
        projectId={PROJECT}
      />,
    );
    await userEvent.click(
      within(screen.getByRole("listitem", { name: "Offre v1.0" })).getByRole("button"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La révision de référence ne peut plus être corrigée.",
    );
  });

  it("offers nothing when no marked revision lists the command", () => {
    const listed = history("revisions_designation_open").map((revision) => ({
      ...revision,
      available_commands: revision.available_commands.filter(
        (offer) => offer.command !== "designate_reference",
      ),
    }));
    show(<ReferenceDesignation revisions={listed} projectId={PROJECT} />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("the application of the rate update", () => {
  const apply = { projectId: PROJECT, revisionId: DRAFT, lockVersion: 4 } as const;

  it("presents what changes, category by category, then applies the categories retained [WF-REV-0060-A]", async () => {
    const client = serve({ [RATES]: { example: "rate_update_applied", status: 200 } });
    show(<RateUpdate proposal={example("rate_update") as never} apply={apply} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    const form = screen.getByRole("form", { name: "Appliquer la mise à jour des taux" });
    expect(within(form).getAllByRole("checkbox")).toHaveLength(2);
    expect(form).toHaveTextContent("Ingénierie électrique");
    expect(form).toHaveTextContent("→");
    expect(client.calls).toHaveLength(0);
    await expectAccessible(form);

    // A category refused is left out of the update.
    await userEvent.click(within(form).getByRole("checkbox", { name: /Mise en service/ }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(bodies(client, RATES)).toEqual([
      { cost_category_ids: ["01926f3a-7c00-7000-8000-000000000402"], lock_version: 4 },
    ]);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Les taux d’1 catégorie sont mis à jour.",
    );
    expect(refresh).toHaveBeenCalled();
  });

  // No Vérif of WF-REV-0060-A says a category retained, nor the absence of an update: these two
  // tests carry the command itself, and cite none.
  it("asks nothing while no category is retained", async () => {
    const client = serve({});
    show(<RateUpdate proposal={example("rate_update") as never} apply={apply} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    for (const box of screen.getAllByRole("checkbox")) {
      await userEvent.click(box);
    }
    expect(screen.getByRole("alert")).toHaveTextContent("Retenez au moins une catégorie.");
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(client.calls).toHaveLength(0);
  });

  it("tells the refusal of a revision marked, naming the condition [WF-REV-0060-A]", async () => {
    serve({ [RATES]: refused("rate_update_revision_marked") });
    show(<RateUpdate proposal={example("rate_update") as never} apply={apply} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("L’état actuel ne permet pas");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the version read is stale, offers to read the page anew, and reads it [WF-REV-0060-A]", async () => {
    const client = serve({
      [RATES]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 5 } },
      },
    });
    show(<RateUpdate proposal={example("rate_update") as never} apply={apply} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(bodies(client, RATES)).toHaveLength(1);
    await userEvent.click(await screen.findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps what it told once the page read again proposes nothing more [WF-REV-0060-A]", async () => {
    serve({ [RATES]: { example: "rate_update_applied", status: 200 } });
    const frame = (proposal: string) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <main>
          <RateUpdate proposal={example(proposal) as never} apply={apply} />
        </main>
      </NextIntlClientProvider>
    );
    const { rerender } = render(frame("rate_update"));
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Les taux de 2 catégories sont mis à jour.",
    );

    rerender(frame("rate_update_none"));
    // The proposal is gone, and so is the command, but not what was told of it, nor its count.
    expect(screen.queryByRole("button", { name: "Appliquer la mise à jour des taux" })).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Les taux de 2 catégories sont mis à jour.",
    );
  });

  it("starts anew on another revision: no status told, every category retained again", async () => {
    serve({ [RATES]: { example: "rate_update_applied", status: 200 } });
    const frame = (revisionId: string) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <main>
          <RateUpdate proposal={example("rate_update") as never} apply={{ ...apply, revisionId }} />
        </main>
      </NextIntlClientProvider>
    );
    const { rerender } = render(frame(DRAFT));
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    await userEvent.click(screen.getByRole("checkbox", { name: /Ingénierie électrique/ }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(await screen.findByRole("status")).toHaveTextContent("mis à jour");

    rerender(frame(CREATED));
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    await userEvent.click(
      screen.getByRole("button", { name: "Appliquer la mise à jour des taux" }),
    );
    for (const box of screen.getAllByRole("checkbox")) {
      expect(box).toBeChecked();
    }
  });

  it("offers nothing when no update is proposed or the revision is not the current one", () => {
    const { unmount } = show(
      <RateUpdate proposal={example("rate_update_none") as never} apply={apply} />,
    );
    expect(screen.queryByRole("button", { name: "Appliquer la mise à jour des taux" })).toBeNull();
    unmount();
    show(<RateUpdate proposal={example("rate_update") as never} />);
    expect(screen.queryByRole("button", { name: "Appliquer la mise à jour des taux" })).toBeNull();
  });
});
