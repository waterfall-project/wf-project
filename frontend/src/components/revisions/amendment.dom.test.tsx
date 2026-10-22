// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient } from "@/api/client";
import { RevisionCommands } from "@/components/commands/object-commands";
import type { Revision } from "@/components/context/read-only";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

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

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000213";
const CREATE = "POST /projects/{project_id}/revisions/{revision_id}/structures";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The revision of the contract, with what is beside it. */
function open(children: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>{children}</main>
    </NextIntlClientProvider>,
  );
}

/** The calls of a route, their bodies. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  router.refresh.mockClear();
  router.push.mockClear();
});

describe("the preparation of an amendment", () => {
  it("is offered as the revision lists it, asks a label, creates the differential and opens it in the grid of the planning", async () => {
    const client = serve({ [CREATE]: { example: "amendment_created", status: 201 } });
    open(<RevisionCommands revision={example("revision") as Revision} />);
    await userEvent.click(screen.getByRole("button", { name: "Préparer un avenant" }));
    const form = screen.getByRole("form", { name: "Préparer un avenant" });
    // The label is asked: nothing is sent without one.
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(bodies(client, CREATE)).toEqual([]);

    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé de l’avenant" }),
      "Avenant 3",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(bodies(client, CREATE)).toEqual([{ kind: "amendment", label: "Avenant 3" }]);
    expect(router.push).toHaveBeenCalledWith(
      `/projects/${PROJECT}/revisions/${REVISION}/planning?structure=${AMENDMENT}`,
    );
  });

  it("is unavailable on a revision marked, naming its condition, and sends nothing", async () => {
    const client = serve({});
    open(<RevisionCommands revision={example("revision_marked") as Revision} />);
    const command = screen.getByRole("button", { name: "Préparer un avenant" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(screen.queryByRole("form")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("tells the refusal of a revision no longer the current one, keeps the form and its label, and leads nowhere", async () => {
    const client = serve({
      [CREATE]: {
        problem: {
          code: "STATE_FORBIDS_OPERATION",
          status: 409 as const,
          params: { missing_condition: "revision_current" },
        },
      },
    });
    open(<RevisionCommands revision={example("revision") as Revision} />);
    await userEvent.click(screen.getByRole("button", { name: "Préparer un avenant" }));
    const form = screen.getByRole("form", { name: "Préparer un avenant" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé de l’avenant" }),
      "Avenant 3",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(bodies(client, CREATE)).toHaveLength(1);
    expect(screen.getByRole("form", { name: "Préparer un avenant" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Libellé de l’avenant" })).toHaveValue("Avenant 3");
    expect(router.push).not.toHaveBeenCalled();
  });
});
