// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import {
  type HistoryRevision,
  RevisionHistory,
  revisionCreation,
} from "@/components/revisions/revision-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { expectCommandRule } from "@/test/command-rule";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";
import { example, type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";

import { RevisionCommands } from "./object-commands";
import type { ProjectContext } from "@/navigation/context";

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
const LOCK = 3;
const DRAFT = "01926f3a-7c00-7000-8000-000000000102";
const CONTEXT: ProjectContext = {
  projectId: PROJECT,
  revisionId: DRAFT,
  revisionInPath: true,
  parameters: new URLSearchParams(),
};
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const CREATED = "01926f3a-7c00-7000-8000-000000000103";
const REVISIONS = `/projects/${PROJECT}/revisions`;
const CREATE = "POST /projects/{project_id}/revisions";
const ABANDON = "DELETE /projects/{project_id}/revisions/{revision_id}";
const DESIGNATE = "PUT /projects/{project_id}/reference-revision";

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

/** The commands of the current revision, at the right of the title of the screen. */
function commands(project = "project") {
  return (
    <RevisionCommands
      revision={example("revision") as Revision}
      context={CONTEXT}
      project={example(project) as Project}
    />
  );
}

/** The card of the history, whose principal command opens the current revision of the project. */
function opening(project = "project") {
  return (
    <RevisionHistory
      revisions={[]}
      context={CONTEXT}
      projectLockVersion={LOCK}
      permissions={[]}
      creation={revisionCreation(example(project) as Project)}
    />
  );
}

/** The history of an example of the contract, each revision with the commands it lists. */
function history(name: string): HistoryRevision[] {
  return (example(name) as { items: HistoryRevision[] }).items;
}

/** The refusal (409) of an example of the contract, as the fake back answers it. */
function refused(name: string) {
  return { problem: { ...(example(name) as Problem), status: 409 as const } };
}

/** The refusal of a write sent with a counter gone stale, as an example of the contract gives it. */
function stale(name: string) {
  return { problem: { ...(example(name) as Problem), status: 412 as const } };
}

/** The calls the fake back received for an operation, their bodies. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  vi.mocked(refresh).mockClear();
  router.push.mockClear();
  // Reset, not cleared: a test makes it read the page anew (US-2240).
  router.refresh.mockReset();
  router.replace.mockClear();
  server.client = undefined;
});

describe("the opening of the current revision", () => {
  it("is offered as the project lists it, and leads to the revision created [WF-REV-0010-A]", async () => {
    const client = serve({ [CREATE]: { example: "revision_created", status: 201 } });
    show(opening("project_without_current_revision"));
    // The principal command of the card of the history, filled; the others outlined (WF-IHM-0090-A).
    expectCommandRule(document.body);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir une révision en cours" }));

    expect(bodies(client, CREATE)).toEqual([{ apply_rate_update: false }]);
    expect(router.push).toHaveBeenCalledWith(`${REVISIONS}?revision_id=${CREATED}`);
    expect(refresh).toHaveBeenCalled();
  });

  it("says its slow write is under way, the same way as a command that starts a task, and opens no second revision on a second press [WF-IHM-0080-A] (#3103)", async () => {
    // The opening of a revision is written within its request — ten seconds on a large project
    // (#3102) —: its button waits for the answer as every command does.
    const answer = held();
    server.client = fakeClient(
      { [CREATE]: { example: "revision_created", status: 201 } },
      answer.timing,
    );
    const client = server.client as FakeClient;
    show(opening("project_without_current_revision"));
    const create = screen.getByRole("button", { name: "Ouvrir une révision en cours" });
    await userEvent.click(create);
    expect(create).toHaveAttribute("aria-busy", "true");
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create.querySelector("[data-waiting]")).not.toBeNull();
    await userEvent.click(create);
    expect(bodies(client, CREATE)).toHaveLength(1);
    await act(async () => {
      answer.release();
      await answer.until;
    });
    expect(router.push).toHaveBeenCalledWith(`${REVISIONS}?revision_id=${CREATED}`);
    expect(create).toHaveAttribute("aria-busy", "false");
    expect(create).not.toHaveAttribute("aria-disabled");
    expect(create.querySelector("[data-waiting]")).toBeNull();
  });

  it("gives its button back once the server refused the opening, to ask it again [WF-IHM-0080-A] (#3103)", async () => {
    // A refusal gives the button back at once.
    const client = serve({
      [CREATE]: [
        {
          problem: {
            code: "STATE_FORBIDS_OPERATION",
            status: 409 as const,
            params: { missing_condition: "no_current_revision" },
          },
        },
        { example: "revision_created", status: 201 },
      ],
    });
    show(opening("project_without_current_revision"));
    const create = screen.getByRole("button", { name: "Ouvrir une révision en cours" });
    await userEvent.click(create);
    await screen.findByRole("alert");
    expect(create).toHaveAttribute("aria-busy", "false");
    expect(create).not.toHaveAttribute("aria-disabled");
    await userEvent.click(create);
    expect(bodies(client, CREATE)).toHaveLength(2);
  });

  it("is refused while a revision is current: unavailable, naming its condition, and nothing is asked [WF-REV-0010-A]", async () => {
    const client = serve({});
    show(opening());
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
    show(opening("project_without_current_revision"));
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

  it("abandons the revision once confirmed, says so, and leaves its address for the revisions [WF-REV-0010-A] [WF-IHM-0110-A]", async () => {
    const client = serve({ [ABANDON]: { status: 204 } });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));

    expect(client.calls.filter((call) => call.route === ABANDON).map((call) => call.path)).toEqual([
      `/projects/${PROJECT}/revisions/${DRAFT}`,
    ]);
    // The counter of the revision as read, which a concurrent write would have moved (WF-IHM-0110).
    expect(client.calls.find((call) => call.route === ABANDON)?.query.get("lock_version")).toBe(
      String((example("revision") as Revision).lock_version),
    );
    // The other commands of the revision keep their own region of status, empty.
    await vi.waitFor(() => {
      expect(screen.getAllByRole("status").map((status) => status.textContent)).toContainEqual(
        expect.stringContaining("dernière révision marquée"),
      );
    });
    expect(router.replace).toHaveBeenCalledWith(REVISIONS);
  });

  it("tells the refusal of a revision marked meanwhile, as the fact it is, and stays on the revision", async () => {
    serve({ [ABANDON]: refused("revision_abandon_marked") });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La révision est marquée : elle ne se modifie plus.",
    );
    expect(router.replace).not.toHaveBeenCalled();
    expect(screen.getByRole("form", { name: "Abandonner la révision en cours" })).toBeVisible();
  });

  it("says the revision written since it was read, offers to read the page anew, and abandons nothing [WF-IHM-0110-A]", async () => {
    serve({ [ABANDON]: stale("revision_abandon_stale") });
    show(commands());
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));
    await userEvent.click(await screen.findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(router.replace).not.toHaveBeenCalled();
  });
  it("waits, confirmed again, until the page has been read anew after an abandonment whose connection was lost once sent (US-2240)", async () => {
    const lost = new TypeError("fetch failed", {
      cause: Object.assign(new Error("other side closed"), { code: "UND_ERR_SOCKET" }),
    });
    const send = vi.fn(() => Promise.reject(lost));
    server.client = createApiClient({ address: "http://localhost:4010", fetch: send });
    // The page as Next reads it anew: the refresh a transition that stays pending until the server
    // answers — here until the test lets it go (`held-reading.tsx`).
    holdReading(router.refresh);
    show(<Reading>{commands()}</Reading>);
    await userEvent.click(screen.getByRole("button", { name: "Abandonner la révision en cours" }));
    const confirm = screen.getByRole("button", { name: "Confirmer l’abandon" });
    await userEvent.click(confirm);

    expect(await screen.findByRole("alert")).toHaveTextContent("l’opération a pu aboutir");
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(confirm);
    expect(send).toHaveBeenCalledOnce();

    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(confirm).not.toHaveAttribute("aria-disabled");
    expect(router.replace).not.toHaveBeenCalled();
  });
  it("holds its command too, until the page has been read anew after an abandonment whose connection was lost once sent, so that the confirmation closed cannot open again before (US-2240)", async () => {
    const lost = new TypeError("fetch failed", {
      cause: Object.assign(new Error("other side closed"), { code: "UND_ERR_SOCKET" }),
    });
    const send = vi.fn(() => Promise.reject(lost));
    server.client = createApiClient({ address: "http://localhost:4010", fetch: send });
    holdReading(router.refresh);
    show(<Reading>{commands()}</Reading>);
    const command = screen.getByRole("button", { name: "Abandonner la révision en cours" });
    await userEvent.click(command);
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("l’opération a pu aboutir");

    // The command waits as the confirmation does: pressed, it neither closes nor opens anything.
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(command).toHaveAttribute("aria-expanded", "true");

    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(command).not.toHaveAttribute("aria-disabled");
    expect(send).toHaveBeenCalledOnce();
  });
});

/** The history of an example, each marked revision offering the designation as a command of its row. */
function designations(revisions: HistoryRevision[]) {
  return (
    <RevisionHistory
      revisions={revisions}
      context={CONTEXT}
      projectLockVersion={LOCK}
      permissions={[]}
    />
  );
}

/** The row of the history that bears a revision, by its version name. */
function rowOf(name: string): HTMLElement {
  const row = screen.getByRole("link", { name }).closest("tr");
  if (row === null) {
    throw new Error(`no row for ${name}`);
  }
  return row;
}

describe("the designation of the reference", () => {
  it("is a command of each marked revision of the history the server lists it for, and of that one alone [WF-REV-0040-A]", () => {
    // The offer v1.0 is marked and lists it available, lacking nothing; the revision 101, current
    // and not marked, is left out.
    const listed = history("revisions_designation_open");
    expect(
      listed.find((revision) => revision.revision_id === OFFER)?.available_commands,
    ).toContainEqual({
      command: "designate_reference",
      is_available: true,
      missing_conditions: [],
    });
    show(designations(listed));
    const offered = screen.getAllByRole("button", { name: "Désigner comme référence" });
    expect(offered).toHaveLength(1);
    const offer = within(rowOf("Offre v1.0")).getByRole("button", {
      name: "Désigner comme référence",
    });
    expect(offer).toBe(offered[0]);
    expect(offer).not.toHaveAttribute("aria-disabled");
    // No card of its own: the history is the one card of the commands of the reference.
    expect(screen.queryByRole("region", { name: "Désignation de la référence" })).toBeNull();
  });

  it("is refused once it no longer corrects: unavailable, naming the condition in its description, and nothing is asked [WF-REV-0040-A]", async () => {
    for (const name of ["revisions", "revisions_marked"]) {
      const client = serve({});
      const { unmount } = show(designations(history(name)));
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
    const { rerender } = show(designations(history("revisions_designation_open")));
    const command = screen.getByRole("button", { name: "Désigner comme référence" });
    await userEvent.click(command);
    expect(screen.getByRole("form", { name: "Désigner comme référence" })).toBeVisible();
    screen.getByRole("button", { name: "Confirmer la désignation" }).focus();

    const frame = (revisions: HistoryRevision[]) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <main>{designations(revisions)}</main>
      </NextIntlClientProvider>
    );
    rerender(frame(history("revisions")));
    expect(screen.queryByRole("form")).toBeNull();
    // The focus the form held does not fall on the page: it goes back to the command.
    expect(command).toHaveFocus();
    rerender(frame(history("revisions_designation_open")));
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.getByRole("button", { name: "Désigner comme référence" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("says what it fixes and that the project goes in progress, then designates and says the new state [WF-REV-0040-A] [WF-IHM-0110-A]", async () => {
    const client = serve({ [DESIGNATE]: { example: "reference_designated", status: 200 } });
    show(designations(history("revisions_designation_open")));
    await userEvent.click(
      within(rowOf("Offre v1.0")).getByRole("button", { name: "Désigner comme référence" }),
    );
    const form = screen.getByRole("form", { name: "Désigner comme référence" });
    expect(form).toHaveTextContent("budget de référence");
    expect(form).toHaveTextContent("valeur planifiée");
    expect(form).toHaveTextContent("« En cours »");
    expect(client.calls).toHaveLength(0);
    await expectAccessible(form);

    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    expect(bodies(client, DESIGNATE)).toEqual([
      { revision_id: OFFER, confirmed: true, lock_version: LOCK },
    ]);
    expect(
      await within(rowOf("Offre v1.0")).findByText(/est la révision de référence/),
    ).toHaveTextContent(
      "« Offre v1.0 » est la révision de référence : le projet est à l’état « En cours ».",
    );
    // The page is read again: the banner, the commands and the read only of the estimate follow.
    expect(refresh).toHaveBeenCalled();
  });

  it("is refused by the server for a revision without task or line, naming the condition [WF-CYC-0030-A]", async () => {
    serve({ [DESIGNATE]: refused("reference_without_tasks") });
    show(designations(history("revisions_designation_open")));
    await userEvent.click(
      within(rowOf("Offre v1.0")).getByRole("button", { name: "Désigner comme référence" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    const refusal = await screen.findByRole("alert");
    expect(refusal).toHaveTextContent("révision portant au moins une tâche et une ligne de devis");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("is refused by the server once the reference cannot be corrected, the condition it lacks named [WF-REV-0040-A]", async () => {
    serve({ [DESIGNATE]: refused("reference_not_correctable") });
    show(designations(history("revisions_designation_open")));
    await userEvent.click(
      within(rowOf("Offre v1.0")).getByRole("button", { name: "Désigner comme référence" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    // Every refusal of a state names the condition the command lacks (J-01).
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Condition non remplie\s: référence encore corrigeable\./,
    );
  });

  it("says the project written since it was read, offers to read the page anew, and designates nothing [WF-IHM-0110-A]", async () => {
    serve({ [DESIGNATE]: stale("reference_designate_stale") });
    show(designations(history("revisions_designation_open")));
    await userEvent.click(
      within(rowOf("Offre v1.0")).getByRole("button", { name: "Désigner comme référence" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la désignation" }));
    await userEvent.click(await screen.findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("offers nothing when no marked revision lists the command", () => {
    const listed = history("revisions_designation_open").map((revision) => ({
      ...revision,
      available_commands: revision.available_commands.filter(
        (offer) => offer.command !== "designate_reference",
      ),
    }));
    show(designations(listed));
    expect(screen.queryByRole("button", { name: "Désigner comme référence" })).toBeNull();
  });
});

describe("a command that opens a confirmation", () => {
  // The command that opens the confirmation is inactive while the write is under way, so that a
  // late answer cannot close a reopening (defect n° 24, #1364). No Vérif of an exigence says it.
  it("stays inactive while it is written, and is lifted with the answer", async () => {
    const wait = held();
    const client = fakeClient({ [ABANDON]: { status: 204 } }, wait.timing);
    server.client = client;
    show(commands());
    const opener = screen.getByRole("button", { name: "Abandonner la révision en cours" });
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("button", { name: "Confirmer l’abandon" }));

    expect(opener).toHaveAttribute("aria-disabled", "true");
    expect(opener).toHaveAttribute("aria-busy", "true");
    expect(opener).toHaveAccessibleDescription("Enregistrement en cours…");
    // Pressed, it neither closes the confirmation nor reopens another.
    await userEvent.click(opener);
    expect(opener).toHaveAttribute("aria-expanded", "true");
    expect(client.calls.filter((call) => call.route === ABANDON)).toHaveLength(1);

    await act(async () => {
      wait.release();
      await wait.until;
    });
    await vi.waitFor(() => {
      expect(opener).not.toHaveAttribute("aria-disabled");
    });
    expect(opener).toHaveAttribute("aria-busy", "false");
  });
});
