// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of a row of the reference data while a write of the row is under way (US-2180, #2260):
 * apart from `resource-commands.dom.test.tsx`, which the bound of a source file leaves no room for.
 */
import { act, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
  type Problem,
} from "@/test/fixtures";
import { browserOffline } from "@/test/offline";

import { CommandedList, useAnswered, useRowCommand } from "./commands";
import { type Calendar, type OrgNode } from "./resource-grids";
import { CalendarList, type NodeOffered, OrgNodeList } from "./resource-lists";

// The server of Next, as far as the lists need it: the fake back, the page rendered again once an
// object is written, the address they read and the navigations they ask.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// A modification whose server action rejects once `until` settles — the API out of reach, as
// `fetch` rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));
vi.mock("@/api/actions/reference", async (original) => {
  const actual = await original<typeof import("@/api/actions/reference")>();
  return {
    ...actual,
    updateReferenceObject: async (...asked: Parameters<typeof actual.updateReferenceObject>) => {
      if (failing.until === undefined) {
        return actual.updateReferenceObject(...asked);
      }
      await failing.until;
      throw new TypeError("Failed to fetch");
    },
  };
});
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));

const NODE = "PATCH /reference/org-nodes/{org_node_id}";
const NODE_ACTIVATION = "PUT /reference/org-nodes/{org_node_id}/activation";
const CALENDAR = "PATCH /reference/calendars/{calendar_id}";
const DEFAULT = "PUT /reference/calendars/{calendar_id}/default";

const NO_QUERY = { sort: undefined, search: undefined, size: undefined };
const NO_BOUNDS = { min: undefined, max: undefined };
const tree = example("org_nodes_with_inactive") as OrgNode[];
const calendars = example("calendars_with_inactive") as { items: Calendar[]; meta: ListPage };

const WRITING = "Enregistrement en cours…";
const WORKSHOP = "«\u00A0Atelier de câblage\u00A0»";
const OFFICE = "«\u00A0Bureau d'études électricité\u00A0»";

/** Serve the fake back, every answer held as `timing` says, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing: FakeTiming): FakeClient {
  const client = fakeClient(
    {
      [NODE]: "org_node_updated",
      [NODE_ACTIVATION]: { example: "org_node_deactivated", status: 200 },
      [CALENDAR]: "calendar_updated",
      [DEFAULT]: "calendar_default",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The active nodes of the tree, for who may write them. */
function organisation() {
  const nodes: NodeOffered[] = tree.map((node) => ({
    id: node.org_node_id,
    code: node.code,
    label: node.label,
    level: node.level,
    active: node.is_active,
  }));
  return inFrench(
    <OrgNodeList
      rows={tree.filter((node) => node.is_active)}
      query={NO_QUERY}
      preferences={undefined}
      editable
      filters={{ code: undefined, level: undefined, state: undefined, levels: NO_BOUNDS }}
      levels={[1, 2, 3]}
      nodes={nodes}
    />,
  );
}

/** The active calendars, for who may write them. */
function calendarList() {
  return inFrench(
    <CalendarList
      rows={calendars.items.filter((calendar) => calendar.is_active)}
      page={calendars.meta}
      query={NO_QUERY}
      preferences={undefined}
      editable
      state={undefined}
    />,
  );
}

/** A command of a row, by its name. */
function command(name: string): HTMLElement {
  return screen.getByRole("button", { name });
}

/** Expect a command waiting for the write of its row: inactive, busy, and saying why. */
function expectWaiting(name: string) {
  const waiting = command(name);
  expect(waiting).toHaveAttribute("aria-disabled", "true");
  expect(waiting).toHaveAttribute("aria-busy", "true");
  expect(waiting).toHaveAccessibleDescription(WRITING);
}

/** Expect a command offered: neither inactive nor busy. */
function expectOffered(name: string) {
  const offered = command(name);
  expect(offered).not.toHaveAttribute("aria-disabled");
  expect(offered).toHaveAttribute("aria-busy", "false");
}

/** The lock version each call of a route sent. */
function versions(client: FakeClient, route: string): unknown[] {
  return client.calls
    .filter((call) => call.route === route)
    .map((call) => (call.body as { lock_version?: unknown }).lock_version);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  failing.until = undefined;
  refresh.mockClear();
});

beforeEach(browserOffline);

describe("a row of the reference data being written", () => {
  it.each([
    // The answer, at its second version, takes the place of the row: the form opens on it.
    ["answered", {}, "status", "«\u00A0Atelier de câblage\u00A0» enregistré.", 2],
    [
      "refused",
      { [NODE]: { problem: example("org_node_update_stale") as Problem & { status: 412 } } },
      "alert",
      "Quelqu’un a modifié cette donnée entre-temps",
      1,
    ],
    ["rejected, the API out of reach", {}, "alert", "Le service est injoignable", 1],
  ] satisfies [string, FakeAnswers, "status" | "alert", string, number][])(
    "keeps the commands of a node waiting while its modification of the dialog closed is %s, offers those of another, then opens its form on the version of the answer (#2260)",
    async (outcome, answers, role, said, version) => {
      const { timing, until, release } = held();
      const rejected = outcome.startsWith("rejected");
      failing.until = rejected ? until : undefined;
      const client = serve(answers, timing);
      render(organisation());
      const modify = `Modifier ${WORKSHOP}`;
      await userEvent.click(command(modify));
      await userEvent.click(command("Enregistrer"));
      await userEvent.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).toBeNull();
      // The commands of the node wait; a press opens and sends nothing.
      expectWaiting(modify);
      expectWaiting(`Désactiver ${WORKSHOP}`);
      await userEvent.click(command(modify));
      await userEvent.click(command(`Désactiver ${WORKSHOP}`));
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(client.calls).toHaveLength(rejected ? 0 : 1);
      // Those of another node stay offered.
      expectOffered(`Modifier ${OFFICE}`);
      expectOffered(`Désactiver ${OFFICE}`);
      release();
      await vi.waitFor(() => {
        expect(screen.getAllByRole(role).map((region) => region.textContent)).toContainEqual(
          expect.stringContaining(said),
        );
      });
      await vi.waitFor(() => {
        expectOffered(modify);
      });
      expectOffered(`Désactiver ${WORKSHOP}`);
      // The form opened anew writes from the version the answer left.
      failing.until = undefined;
      await userEvent.click(command(modify));
      await userEvent.click(command("Enregistrer"));
      await vi.waitFor(() => {
        expect(versions(client, NODE).at(-1)).toBe(version);
      });
    },
  );

  it("keeps the modification of a node waiting while its deactivation is under way, then opens it on the version answered (#2260)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    render(organisation());
    await userEvent.click(command(`Désactiver ${WORKSHOP}`));
    expectWaiting(`Désactiver ${WORKSHOP}`);
    expectWaiting(`Modifier ${WORKSHOP}`);
    await userEvent.click(command(`Modifier ${WORKSHOP}`));
    expect(screen.queryByRole("dialog")).toBeNull();
    expectOffered(`Modifier ${OFFICE}`);
    release();
    await vi.waitFor(() => {
      expectOffered(`Modifier ${WORKSHOP}`);
    });
    expect(versions(client, NODE_ACTIVATION)).toEqual([1]);
    await userEvent.click(command(`Modifier ${WORKSHOP}`));
    await userEvent.click(command("Enregistrer"));
    await vi.waitFor(() => {
      expect(versions(client, NODE)).toEqual([2]);
    });
  });

  it("keeps the designation of a calendar waiting while its modification is under way, that of another offered (#2260)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    render(calendarList());
    const four = "«\u00A0Semaine de quatre jours\u00A0»";
    await userEvent.click(command(`Modifier ${four}`));
    await userEvent.click(command("Enregistrer"));
    await userEvent.keyboard("{Escape}");
    expectWaiting(`Désigner ${four} par défaut`);
    await userEvent.click(command(`Désigner ${four} par défaut`));
    expect(client.calls.map((call) => call.route)).toEqual([CALENDAR]);
    expectOffered(`Modifier «\u00A0Semaine standard\u00A0»`);
    release();
    // The calendar as the server answers it, renamed.
    await vi.waitFor(() => {
      expectOffered("Désigner «\u00A0Semaine de quatre jours de dix heures\u00A0» par défaut");
    });
  });

  it("keeps in a row the first of two answers at one version (#2260)", async () => {
    const [node] = tree as [OrgNode];
    const modified = { ...node, label: "Renommé", lock_version: 2 };
    const deactivated = { ...node, is_active: false, lock_version: 2 };
    const answers: ((row: OrgNode) => void)[] = [];
    const answering = () =>
      new Promise<{ kind: "done"; data: OrgNode[] }>((resolve) => {
        answers.push((row) => {
          resolve({ kind: "done", data: [row] });
        });
      });
    function Row() {
      const [shown] = useAnswered([node]);
      const [, run] = useRowCommand(node.org_node_id, "target", {}, node.label);
      return (
        <>
          <button
            onClick={() => {
              // Two writes of the row, started in one press: both are free to run.
              run(answering, () => "modified");
              run(answering, () => "deactivated");
            }}
          >
            Écrire
          </button>
          <output>{`${shown?.label ?? ""} ${shown?.is_active === false ? "Désactivé" : "Actif"}`}</output>
        </>
      );
    }
    render(
      inFrench(
        <CommandedList kind="org_node">
          <Row />
        </CommandedList>,
      ),
    );
    await userEvent.click(command("Écrire"));
    // The second write answered first, at the version 2: the row shows it.
    await act(async () => {
      answers[1]?.(deactivated);
      await Promise.resolve();
    });
    await vi.waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(`${node.label} Désactivé`);
    });
    // The first answered after, at the same version 2: the row keeps the answer it shows.
    await act(async () => {
      answers[0]?.(modified);
      await Promise.resolve();
    });
    await vi.waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(`${node.label} Désactivé`);
    });
  });
});
