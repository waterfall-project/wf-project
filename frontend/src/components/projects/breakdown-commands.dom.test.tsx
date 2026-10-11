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
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
} from "@/test/fixtures";

import type { BreakdownKind, WorkBreakdown } from "./settings-grids";
import { WorkBreakdownList } from "./settings-lists";

// The server of Next, as far as the grid needs it: the fake back, the page read anew once the work
// breakdown is written, the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// A write whose server action rejects once `until` settles — the API out of reach, as `fetch`
// rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));
vi.mock("@/api/actions/projects", async (original) => {
  const actual = await original<typeof import("@/api/actions/projects")>();
  return {
    ...actual,
    setWorkBreakdown: async (...asked: Parameters<typeof actual.setWorkBreakdown>) => {
      if (failing.until === undefined) {
        return actual.setWorkBreakdown(...asked);
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
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/settings",
  useSearchParams: () => new URLSearchParams(),
}));

type Problem = components["schemas"]["Problem"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const SET = "PUT /projects/{project_id}/work-breakdown";
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };
const WHOLE = example("work_breakdown") as WorkBreakdown;
const ITEM = "Fourniture et montage des armoires";
const PACKAGE = "Armoires";
const DELIVERABLE = "Procès-verbal de réception usine des armoires";
const ADDED = "Mise en service sur site";

/** An element of the witness, by the end of its identifier. */
const id = (number: number) => `01926f3a-7c00-7000-8000-000000000${String(number)}`;

/** A label between French quotes, as the catalogue writes it. */
const quoted = (label: string) => `«\u00a0${label}\u00a0»`;

/** The same, as a matcher of text reads it, its spaces normalised. */
const read = (label: string) => `« ${label} »`;

/** The work breakdown of the witness as `setWorkBreakdown` writes it, an element changed or not. */
function witness(packages: unknown[] = [writtenPackage()]) {
  return { order_items: [{ order_item_id: id(711), label: ITEM, work_packages: packages }] };
}

/** The work package of the witness as `setWorkBreakdown` writes it. */
function writtenPackage(label = PACKAGE, deliverables: unknown[] = [writtenDeliverable()]) {
  return { work_package_id: id(712), label, deliverables };
}

/** The deliverable of the witness as `setWorkBreakdown` writes it. */
function writtenDeliverable() {
  return { deliverable_id: id(713), label: DELIVERABLE };
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient({ [SET]: "work_breakdown_saved", ...answers }, timing);
  server.client = client;
  return client;
}

/**
 * The work breakdown of the witness, in French, read whole unless another reading is shown; `whole`
 * is the one the page read whole besides, which a gesture starts from.
 */
function list(
  offer: CommandOffer = AVAILABLE,
  shown: WorkBreakdown = WHOLE,
  kinds: readonly BreakdownKind[] = [],
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <WorkBreakdownList
          breakdown={shown}
          project={PROJECT}
          kinds={kinds}
          editing={{ project: PROJECT, offer, counter: shown.lock_version, whole: WHOLE }}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the work breakdown. */
function grid(): HTMLElement {
  return screen.getByRole("treegrid", { name: "Lotissement" });
}

/** The labels of the rows of the grid, and its totals. */
function shown(): string[] {
  const rows = within(grid()).getAllByRole("row");
  return [
    ...rows
      .slice(1, -1)
      .map((row) => row.querySelector('[data-column="label"]')?.textContent ?? ""),
    rows.at(-1)?.textContent ?? "",
  ];
}

/** The bodies of the work breakdowns written. */
function written(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === SET).map((call) => call.body);
}

/** The cell of the label of a row, made the active one. */
async function activate(label: string): Promise<HTMLElement> {
  const cell = within(grid()).getByText(label).closest("td");
  if (cell === null) {
    throw new Error(`no cell holds ${label}`);
  }
  await userEvent.click(cell);
  return cell;
}

/** Open the menu of the cell of a row from the keyboard, and press one of its commands. */
async function fromMenu(label: string, command: string): Promise<void> {
  await activate(label);
  await userEvent.keyboard("{Shift>}{F10}{/Shift}");
  const menu = screen.getByRole("menu", { name: "Menu de la cellule" });
  await userEvent.click(within(menu).getByRole("menuitem", { name: command }));
}

/** Type a label in the dialog open, and send it. */
async function enter(label: string): Promise<HTMLElement> {
  const dialog = screen.getByRole("dialog");
  const field = within(dialog).getByRole("textbox", { name: "Libellé" });
  await userEvent.clear(field);
  await userEvent.type(field, label);
  await userEvent.click(within(dialog).getByRole("button", { name: /^(Créer|Enregistrer)$/ }));
  return dialog;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  failing.until = undefined;
  vi.restoreAllMocks();
  refresh.mockClear();
});

describe("the work breakdown edited in its grid", () => {
  it("adds a work package without a deliverable from the menu of a cell, sends the work breakdown whole with it and no identifier, and shows the reading answered [WF-PRJ-0020-A]", async () => {
    // Un lot peut être créé sans livrable.
    const client = serve();
    render(list());
    await fromMenu(ITEM, `Ajouter un lot au poste ${quoted(ITEM)}`);
    expect(screen.getByRole("dialog")).toHaveAccessibleName(`Nouveau lot du poste ${quoted(ITEM)}`);
    await expectAccessible(screen.getByRole("dialog"));
    await enter(ADDED);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // The marks of the reading are not written; the element added has no identifier.
    expect(written(client)).toEqual([
      {
        ...witness([writtenPackage(), { label: ADDED, deliverables: [] }]),
        lock_version: 1,
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    // The reading answered, as the server gives it: the work package with its identifier and the
    // deliverable it holds there.
    expect(shown()).toEqual([
      ITEM,
      PACKAGE,
      DELIVERABLE,
      ADDED,
      "Procès-verbal de mise en service",
      "1 poste, 2 lots et 2 livrables",
    ]);
    expect(screen.getByRole("status")).toHaveTextContent(`Lot ${read(ADDED)} ajouté.`);
    expect(within(grid()).getByText(ITEM).closest("td")).toHaveFocus();
  });

  it("adds an order item and renames an element from the bar of the grid, on the row of the active cell", async () => {
    const client = serve({ [SET]: ["work_breakdown_saved", "work_breakdown_saved"] });
    render(list());
    const create = screen.getByRole("button", { name: "Nouveau poste" });
    await userEvent.click(create);
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Nouveau poste");
    await enter("Études");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(create).toHaveFocus();
    await activate(PACKAGE);
    await userEvent.click(
      screen.getByRole("button", { name: `Renommer le lot ${quoted(PACKAGE)}` }),
    );
    expect(screen.getByRole("textbox", { name: "Libellé" })).toHaveValue(PACKAGE);
    await enter("Armoires de commande");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)).toEqual([
      {
        order_items: [...witness().order_items, { label: "Études", work_packages: [] }],
        lock_version: 1,
      },
      // The second gesture starts from the reading the first one answered, and its counter.
      {
        order_items: [
          {
            ...witness([
              writtenPackage("Armoires de commande"),
              {
                work_package_id: id(716),
                label: ADDED,
                deliverables: [
                  { deliverable_id: id(717), label: "Procès-verbal de mise en service" },
                ],
              },
            ]).order_items[0],
          },
        ],
        lock_version: 2,
      },
    ]);
    expect(screen.getByRole("status")).toHaveTextContent(
      `Lot renommé ${read("Armoires de commande")}.`,
    );
  });

  it.each([
    [
      ITEM,
      `le poste ${quoted(ITEM)}`,
      "Le poste, ses lots et leurs livrables seront supprimés. Les tâches de la révision en cours qui portent le poste ou l’un de ses lots restent et perdent leur rattachement\u00a0; les révisions marquées le gardent.",
      { order_items: [] },
      `Poste ${read(ITEM)} supprimé.`,
    ],
    [
      PACKAGE,
      `le lot ${quoted(PACKAGE)}`,
      "Le lot et ses livrables seront supprimés. Les tâches de la révision en cours qui portent le lot restent et perdent leur rattachement\u00a0; les révisions marquées le gardent.",
      witness([]),
      `Lot ${read(PACKAGE)} supprimé.`,
    ],
    [
      DELIVERABLE,
      `le livrable ${quoted(DELIVERABLE)}`,
      "Le livrable sera supprimé.",
      witness([writtenPackage(PACKAGE, [])]),
      `Livrable ${read(DELIVERABLE)} supprimé.`,
    ],
  ])(
    "confirms the deletion of « %s », saying what goes with it, then sends the work breakdown without it",
    async (label, element, hint, sent, said) => {
      const client = serve();
      render(list());
      await fromMenu(label, `Supprimer ${element}`);
      const confirmation = screen.getByRole("dialog", { name: `Supprimer ${element}\u00a0?` });
      expect(confirmation).toHaveAccessibleDescription(hint);
      expect(client.calls).toEqual([]);
      await userEvent.click(within(confirmation).getByRole("button", { name: "Supprimer" }));
      await vi.waitFor(() => {
        expect(screen.getByRole("status")).toHaveTextContent(said);
      });
      expect(written(client)).toEqual([{ ...sent, lock_version: 1 }]);
      expect(screen.queryByRole("dialog")).toBeNull();
    },
  );

  it("refuses an empty label before asking, at its field", async () => {
    const client = serve();
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Nouveau poste" }));
    await enter(" ");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription("Une valeur est requise.");
    expect(field).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it.each([
    ["work_breakdown_label_required", "Une valeur est requise."],
    [
      "work_breakdown_unknown_item",
      "Cet élément ne fait pas partie du lotissement lu\u00a0: inconnu, d’une autre nature ou supprimé.",
    ],
  ])(
    "says at the field of the dialog a refusal %s that points at the element it adds, the dialog kept",
    async (refusal, sentence) => {
      serve({ [SET]: { problem: example(refusal) as Problem & { status: 422 } } });
      render(list());
      await fromMenu(ITEM, `Ajouter un lot au poste ${quoted(ITEM)}`);
      const dialog = await enter(ADDED);
      const field = within(dialog).getByRole("textbox", { name: "Libellé" });
      await vi.waitFor(() => {
        expect(field).toHaveAttribute("aria-invalid", "true");
      });
      expect(field).toHaveAccessibleDescription(sentence);
      expect(field).toHaveFocus();
      expect(within(dialog).queryByRole("alert")).toBeNull();
      expect(refresh).not.toHaveBeenCalled();
    },
  );

  it("names the element a refusal points at when it is not the one the dialog writes", async () => {
    // The work package added first; then « Armoires » renamed, the server refusing the work package
    // added after it, sent with the identifier « Armoires » bears.
    serve({
      [SET]: [
        "work_breakdown_saved",
        { problem: example("work_breakdown_duplicate_item") as Problem & { status: 422 } },
      ],
    });
    render(list());
    await fromMenu(ITEM, `Ajouter un lot au poste ${quoted(ITEM)}`);
    await enter(ADDED);
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    await fromMenu(PACKAGE, `Renommer le lot ${quoted(PACKAGE)}`);
    const dialog = await enter("Armoires de commande");
    const alerts = await within(dialog).findAllByRole("alert");
    expect(alerts.map((alert) => alert.textContent)).toEqual([
      expect.stringContaining("Les données saisies ne sont pas valides."),
      `Lot ${quoted(ADDED)}\u00a0: Cet élément figure déjà plus haut dans le lotissement saisi\u00a0: chacun ne s’écrit qu’une fois.`,
    ]);
    expect(within(dialog).getByRole("textbox", { name: "Libellé" })).not.toHaveAttribute(
      "aria-invalid",
    );
  });

  it("says under the dialog a write the server refuses while a background task runs, naming the condition", async () => {
    serve({
      [SET]: { problem: example("work_breakdown_background_task") as Problem & { status: 409 } },
    });
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Nouveau poste" }));
    const dialog = await enter("Études");
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : aucun traitement de fond en cours sur l’objet.",
    );
    expect(screen.getByRole("dialog")).toBe(dialog);
  });

  it("says the version stale under the dialog, with the offer to read the page anew", async () => {
    serve({
      [SET]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 2 } },
      },
    });
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Nouveau poste" }));
    const dialog = await enter("Études");
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Quelqu’un a modifié cette donnée entre-temps",
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("writes from the work breakdown read whole while the grid shows a reading filtered, which keeps its rows and counts what it retains", async () => {
    const client = serve();
    render(
      list(AVAILABLE, example("work_breakdown_work_packages") as WorkBreakdown, ["work_package"]),
    );
    // The order item is there for the context of its work package: the totals count the work
    // package alone (#574).
    expect(shown()).toEqual([ITEM, PACKAGE, "1 lot"]);
    await activate(PACKAGE);
    await userEvent.click(
      screen.getByRole("button", { name: `Renommer le lot ${quoted(PACKAGE)}` }),
    );
    await enter("Armoires de commande");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)).toEqual([
      { ...witness([writtenPackage("Armoires de commande")]), lock_version: 1 },
    ]);
    expect(shown()).toEqual([ITEM, PACKAGE, "1 lot"]);
  });

  it("keeps its commands waiting while a write of the dialog closed is under way, then opens on the counter the answer brings (#661, #734)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    render(list());
    const create = screen.getByRole("button", { name: "Nouveau poste" });
    await userEvent.click(create);
    const dialog = await enter("Études");
    await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // Opened anew now, a dialog would write from the counter 1, which the answer replaces: the
    // command, which has the focus back, waits and says why.
    expect(create).toHaveFocus();
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).toHaveAttribute("aria-busy", "true");
    expect(create).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(create);
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    expect(await screen.findByText(`Poste ${read("Études")} ajouté.`)).toBeInTheDocument();
    expect(create).not.toHaveAttribute("aria-disabled");
    await userEvent.click(create);
    await enter("Essais");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)[1]).toMatchObject({ lock_version: 2 });
  });

  it.each([
    ["answered", {}, "status", `Lot ${quoted(ADDED)} ajouté.`],
    [
      "refused",
      { [SET]: { problem: example("work_breakdown_label_required") as Problem & { status: 422 } } },
      "alert",
      `Lot ${quoted(ADDED)}\u00a0: Une valeur est requise.`,
    ],
    ["rejected, the API out of reach", {}, "alert", "Le service est injoignable"],
  ] satisfies [string, FakeAnswers, "status" | "alert", string][])(
    "frees its commands once a write of the dialog closed is %s, says it above the grid, and opens a dialog again (#734)",
    async (outcome, answers, role, said) => {
      const { timing, until, release } = held();
      failing.until = outcome.startsWith("rejected") ? until : undefined;
      const client = serve(answers, timing);
      render(list());
      await fromMenu(ITEM, `Ajouter un lot au poste ${quoted(ITEM)}`);
      const dialog = await enter(ADDED);
      await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));
      const create = screen.getByRole("button", { name: "Nouveau poste" });
      expect(create).toHaveAttribute("aria-disabled", "true");
      release();
      await vi.waitFor(() => {
        expect(screen.getAllByRole(role).map((region) => region.textContent)).toContainEqual(
          expect.stringContaining(said),
        );
      });
      // A server action rejected asked nothing of the fake back.
      expect(written(client)).toHaveLength(outcome.startsWith("rejected") ? 0 : 1);
      await vi.waitFor(() => {
        expect(create).not.toHaveAttribute("aria-disabled");
      });
      await userEvent.click(create);
      expect(screen.getByRole("dialog", { name: "Nouveau poste" })).toBeVisible();
    },
  );

  it.each([
    // As `project_completed` lists it.
    ["project_not_terminal", "projet non clos"],
    // A declared variant: the offer of `project`, lacking the one condition a background task
    // takes away — no example of the contract lists it so.
    ["no_background_task_running", "aucun traitement de fond en cours sur l’objet"],
  ] as const)(
    "presents its commands unavailable without %s, in the bar and the menu, and opens nothing",
    async (condition, said) => {
      serve();
      render(list({ is_available: false, missing_conditions: [condition] }));
      const create = screen.getByRole("button", { name: "Nouveau poste" });
      expect(create).toHaveAttribute("aria-disabled", "true");
      expect(create).toHaveAccessibleDescription(`Condition non remplie\u00a0: ${said}.`);
      await userEvent.click(create);
      expect(screen.queryByRole("dialog")).toBeNull();
      await fromMenu(PACKAGE, `Supprimer le lot ${quoted(PACKAGE)}`);
      const item = screen.getByRole("menuitem", { name: `Supprimer le lot ${quoted(PACKAGE)}` });
      expect(item).toHaveAttribute("aria-disabled", "true");
      expect(item).toHaveAccessibleDescription(`Condition non remplie\u00a0: ${said}.`);
      expect(screen.queryByRole("dialog")).toBeNull();
    },
  );
});
