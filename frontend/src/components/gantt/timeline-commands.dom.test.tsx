// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
  unreachable,
} from "@/test/fixtures";

import { TimelineBody, TimelineChoice, TimelineDeletions } from "./timeline-commands";

// The server of Next, as far as the timelines need it: the fake back, the page read anew once a
// timeline is written, the address it reads and the one it leads to.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams(),
}));

type Timeline = components["schemas"]["Timeline"];
type Problem = components["schemas"]["Problem"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const SCREEN = `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102/timelines`;
const TIMELINES = example("timelines") as Timeline[];
const STEERING = "01926f3a-7c00-7000-8000-000000001000";
const CUSTOMER = "01926f3a-7c00-7000-8000-000000001001";
/** The timeline a creation answers, a third one beside those of the witness. */
const CREATED = example("timeline_created") as Timeline;
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };

/** A label between French quotes, as the catalogue writes it. */
const quoted = (label: string) => `«\u00a0${label}\u00a0»`;

/** The same, as a matcher of text reads it, its spaces normalised. */
const read = (label: string) => `« ${label} »`;

/** Serve the fake back, answering when the timing says, and give it back to read its calls. */
function serve(timing?: FakeTiming, answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient(
    {
      "POST /projects/{project_id}/timelines": { example: "timeline_created", status: 201 },
      "DELETE /projects/{project_id}/timelines/{timeline_id}": { status: 204 },
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** The address of a timeline on the screen. */
const addressOf = (timeline: string) => `${SCREEN}?timeline=${timeline}`;

/**
 * The timelines given — those of the witness by default —, in French, the one shown with the body the
 * server draws for it — a table named after it —, as the project lists the command.
 */
function choice(
  offer: CommandOffer | undefined,
  { timelines = TIMELINES, shown = STEERING }: { timelines?: Timeline[]; shown?: string } = {},
) {
  const label = timelines.find((timeline) => timeline.timeline_id === shown)?.label;
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TimelineDeletions>
        <TimelineChoice
          project={PROJECT}
          offer={offer}
          timelines={timelines}
          shown={shown}
          hrefs={Object.fromEntries(
            timelines.map((timeline) => [timeline.timeline_id, addressOf(timeline.timeline_id)]),
          )}
        />
        <TimelineBody timelines={timelines} shown={shown}>
          <table aria-label={label}>
            <tbody>
              <tr>
                <td>{label}</td>
              </tr>
            </tbody>
          </table>
        </TimelineBody>
      </TimelineDeletions>
    </NextIntlClientProvider>
  );
}

/** The names of the timelines offered. */
function offered(): string[] {
  return within(screen.getByRole("navigation", { name: "Chronologie affichée" }))
    .getAllByRole("link")
    .map((link) => link.textContent);
}

/** Open the deletion of the timeline shown — the steering committee by default —, and confirm it. */
async function deleteShown(label = "Comité de pilotage"): Promise<void> {
  await userEvent.click(
    screen.getByRole("button", { name: `Supprimer la chronologie ${quoted(label)}` }),
  );
  const confirmation = screen.getByRole("dialog", {
    name: `Supprimer la chronologie ${quoted(label)}\u00a0?`,
  });
  expect(confirmation).toHaveAccessibleDescription(
    "La chronologie et ses inscriptions seront supprimées\u00a0; les tâches et les jalons gardent leurs dates.",
  );
  await userEvent.click(within(confirmation).getByRole("button", { name: "Supprimer" }));
}

beforeEach(() => {
  router.replace.mockClear();
  forgetMessages();
});

afterEach(() => {
  refresh.mockClear();
});

describe("the commands of the timelines of a project", () => {
  it("creates a timeline by its name in a dialog, says it, and reads the page anew, which lists it", async () => {
    const client = serve();
    const { container } = render(choice(AVAILABLE));
    const create = screen.getByRole("button", { name: "Nouvelle chronologie" });
    await userEvent.click(create);
    const dialog = screen.getByRole("dialog", { name: "Nouvelle chronologie" });
    await userEvent.type(
      within(dialog).getByRole("textbox", { name: "Nom" }),
      "Réunion de chantier",
    );
    await expectAccessible(container);
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(
      await screen.findByText(`Chronologie ${read("Réunion de chantier")} créée.`),
    ).toBeInTheDocument();
    expect(client.calls.map((call) => [call.route, call.body])).toEqual([
      ["POST /projects/{project_id}/timelines", { label: "Réunion de chantier" }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(create).toHaveFocus();
    // Noted once in the history of the messages, about the timeline created.
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "success",
        sentence: `Chronologie ${quoted("Réunion de chantier")} créée.`,
        object: "Réunion de chantier",
      }),
    ]);
    // A creation adds no link: the page read anew lists the timeline where the server keeps it.
    expect(offered()).toEqual(["Comité de pilotage", "Revue client"]);
  });

  it("refuses an empty name before asking, at its field", async () => {
    const client = serve();
    render(choice(AVAILABLE));
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle chronologie" }));
    const dialog = screen.getByRole("dialog", { name: "Nouvelle chronologie" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    const name = within(dialog).getByRole("textbox", { name: "Nom" });
    expect(name).toHaveAccessibleDescription("Une valeur est requise.");
    expect(name).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("says at its field the empty name the server refuses, and keeps the dialog open [WF-PLA-0140-A]", async () => {
    // A name of blanks passes the form and is refused by the server (`timeline_label_required`).
    serve(undefined, {
      "POST /projects/{project_id}/timelines": {
        problem: example("timeline_label_required") as Problem & { status: 422 },
      },
    });
    render(choice(AVAILABLE));
    await userEvent.click(screen.getByRole("button", { name: "Nouvelle chronologie" }));
    const dialog = screen.getByRole("dialog", { name: "Nouvelle chronologie" });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Nom" }), " ");
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(within(dialog).getByRole("textbox", { name: "Nom" })).toHaveAccessibleDescription(
        "Une valeur est requise.",
      );
    });
    expect(screen.getByRole("dialog", { name: "Nouvelle chronologie" })).toBe(dialog);
  });

  it("tells a deletion refused for a terminal project, and keeps the link [WF-CYC-0100-A]", async () => {
    serve(undefined, {
      "DELETE /projects/{project_id}/timelines/{timeline_id}": {
        problem: example("timeline_delete_terminal") as Problem & { status: 403 },
      },
    });
    render(choice(AVAILABLE));
    await deleteShown();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le projet est clos : il ne se modifie plus.",
    );
    expect(offered()).toEqual(["Comité de pilotage", "Revue client"]);
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("deletes the timeline shown once confirmed, takes its link away and its tasks, and leads to the one left", async () => {
    const client = serve();
    render(choice(AVAILABLE));
    await deleteShown();
    expect(
      await screen.findByText(`Chronologie ${read("Comité de pilotage")} supprimée.`),
    ).toBeInTheDocument();
    expect(client.calls.map((call) => [call.route, call.path])).toEqual([
      [
        "DELETE /projects/{project_id}/timelines/{timeline_id}",
        `/projects/${PROJECT}/timelines/${STEERING}`,
      ],
    ]);
    expect(offered()).toEqual(["Revue client"]);
    expect(router.replace).toHaveBeenCalledWith(addressOf(CUSTOMER));
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "success",
        sentence: `Chronologie ${quoted("Comité de pilotage")} supprimée.`,
        object: "Comité de pilotage",
      }),
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    // The tasks of the timeline deleted give way while the page leads to the next one.
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("shows, the timeline shown deleted, the first one the project keeps, as the page does when its address names none it has", async () => {
    serve();
    render(choice(AVAILABLE, { timelines: [...TIMELINES, CREATED], shown: CUSTOMER }));
    await deleteShown("Revue client");
    expect(
      await screen.findByText(`Chronologie ${read("Revue client")} supprimée.`),
    ).toBeInTheDocument();
    expect(offered()).toEqual(["Comité de pilotage", "Réunion de chantier"]);
    expect(router.replace).toHaveBeenCalledExactlyOnceWith(addressOf(STEERING));
  });

  it("says the project has no timeline once the last is deleted, and leads nowhere", async () => {
    serve();
    const { rerender } = render(choice(AVAILABLE));
    await deleteShown();
    expect(
      await screen.findByText(`Chronologie ${read("Comité de pilotage")} supprimée.`),
    ).toBeInTheDocument();
    expect(router.replace).toHaveBeenCalledExactlyOnceWith(addressOf(CUSTOMER));
    // The page read anew at the address of the review, which the server lists still.
    rerender(choice(AVAILABLE, { shown: CUSTOMER }));
    expect(screen.getByRole("table", { name: "Revue client" })).toBeInTheDocument();
    router.replace.mockClear();
    await deleteShown("Revue client");
    expect(
      await screen.findByText(`Chronologie ${read("Revue client")} supprimée.`),
    ).toBeInTheDocument();
    expect(screen.getByText("Ce projet n\u2019a aucune chronologie.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Chronologie affichée" })).toBeNull();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("moves nothing on a deletion answered once another timeline is shown, and takes its link away", async () => {
    const { timing, release } = held();
    const client = serve(timing);
    const { rerender } = render(choice(AVAILABLE));
    await deleteShown();
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    // The review followed by its link while the deletion is under way.
    rerender(choice(AVAILABLE, { shown: CUSTOMER }));
    release();
    expect(
      await screen.findByText(`Chronologie ${read("Comité de pilotage")} supprimée.`),
    ).toBeInTheDocument();
    expect(offered()).toEqual(["Revue client"]);
    expect(screen.getByRole("table", { name: "Revue client" })).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("moves nothing on a deletion answered once the screen is left", async () => {
    const { timing, release } = held();
    const client = serve(timing);
    const { unmount } = render(choice(AVAILABLE));
    await deleteShown();
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.keyboard("{Escape}");
    unmount();
    release();
    // Answered — the page read anew —, then given a turn to go on from the answer.
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    await new Promise((settle) => setTimeout(settle, 0));
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("tells above the timelines a deletion the server does not answer, and keeps the link", async () => {
    server.client = unreachable();
    render(choice(AVAILABLE));
    await deleteShown();
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(offered()).toEqual(["Comité de pilotage", "Revue client"]);
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("presents its commands unavailable with the conditions they lack, and opens nothing", async () => {
    serve();
    render(choice({ is_available: false, missing_conditions: ["project_not_terminal"] }));
    for (const name of [
      "Nouvelle chronologie",
      `Supprimer la chronologie ${quoted("Comité de pilotage")}`,
    ]) {
      const command = screen.getByRole("button", { name });
      expect(command).toHaveAttribute("aria-disabled", "true");
      expect(command).toHaveAccessibleDescription("Condition non remplie\u00a0: projet non clos.");
      await userEvent.click(command);
      expect(screen.queryByRole("dialog")).toBeNull();
    }
    // Nothing was sent: the history notes nothing of the conditions said.
    expect(readMessages().messages).toEqual([]);
  });

  it("offers nothing to a session the project lists no command to", () => {
    render(choice(undefined));
    expect(screen.queryByRole("button")).toBeNull();
    expect(offered()).toEqual(["Comité de pilotage", "Revue client"]);
  });
});
