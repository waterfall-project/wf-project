// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { type Entry, type Fresh, useEntryGuard, withheld } from "./entry-guard";
import { OwnEstimateEntry } from "./own-estimate-entry";
import { signals } from "./rebase-report";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));

type Report = components["schemas"]["StructureRebaseReport"];
type Problem = components["schemas"]["Problem"];
type NodesWritten = components["schemas"]["NodesWritten"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The own estimate in arrears of the structures of the witness (`structures`), and the one a marking pruned.
const LATE = "01926f3a-7c00-7000-8000-000000000206";
const PRUNED = "01926f3a-7c00-7000-8000-000000000209";
const STRUCTURE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REPORT = `GET ${STRUCTURE}/rebase` as const;
const REBASE = `POST ${STRUCTURE}/rebase` as const;
const RECOMPOSE = `POST ${STRUCTURE}/recompose` as const;
const NODES = `GET ${STRUCTURE}/nodes` as const;
// A line of the own estimate of the witness, which accepts its quantity, and a node it does not have.
const LINE = "01926f3a-7c00-7000-8000-000000002053";
const ABSENT = "01926f3a-7c00-7000-8000-000000009999";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Two entries made one after the other, with no wait between them: the guard is asked twice. */
function Twice({ write }: { readonly write: () => Promise<Outcome<string>> }) {
  const guard = useEntryGuard();
  const [told, setTold] = useState<string[]>([]);
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          for (const entry of [guard(write), guard(write)]) {
            void entry.then((outcome) => {
              setTold((before) => [...before, outcome.kind]);
            });
          }
        }}
      >
        Saisir deux fois
      </button>
      <output aria-label="Réponses">{told.join(",")}</output>
    </div>
  );
}

/** A grid's cell: one write, which goes through the guard of the own estimate. */
function Cell({ write }: { readonly write: () => Promise<Outcome<string>> }) {
  const guard = useEntryGuard();
  const [told, setTold] = useState<string>();
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          void guard(write).then((outcome) => {
            setTold(outcome.kind);
          });
        }}
      >
        Saisir
      </button>
      <output aria-label="Réponse">{told}</output>
    </div>
  );
}

/** What a write of a line answers, with the counters it moved the line and the structure on to. */
function written(lockVersion: number, structureLockVersion: number): NodesWritten {
  const answer = example("estimate_line_updated") as NodesWritten;
  return {
    ...answer,
    nodes: answer.nodes.map((node) => ({ ...node, node_id: LINE, lock_version: lockVersion })),
    structure_lock_version: structureLockVersion,
  };
}

/** An entry into the quantity of the line, which notes the counters it is sent with. */
function quantity(
  sent: (Fresh | undefined)[],
  options: { readonly node?: string; readonly field?: string; readonly moved?: number } = {},
): Entry<NodesWritten> {
  const node = options.node ?? LINE;
  return {
    nodes: [node],
    fields: [options.field ?? "estimate_line.quantity"],
    send: (fresh) => {
      // A copy: the guard moves the counters on as the answers come.
      sent.push(fresh === undefined ? undefined : { ...fresh, nodes: new Map(fresh.nodes) });
      return Promise.resolve({
        kind: "done" as const,
        data: written(options.moved ?? 9, 7),
      });
    },
  };
}

/** What an entry was answered: done, or the code of the refusal and those of its fields. */
function toldOf(outcome: Outcome<NodesWritten>): string {
  if (outcome.kind === "done" || outcome.kind === "unreachable") {
    return outcome.kind;
  }
  const fields = (outcome.problem.fields ?? []).map((field) => `:${field.pointer}:${field.code}`);
  return [outcome.problem.code, ...fields].join("");
}

/** Entries made one after the other, with no wait between them, each through the guard. */
function Entered({ entries }: { readonly entries: readonly Entry<NodesWritten>[] }) {
  const guard = useEntryGuard();
  const [told, setTold] = useState<string[]>([]);
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          for (const entry of entries) {
            void guard(entry).then((outcome) => {
              setTold((before) => [...before, toldOf(outcome)]);
            });
          }
        }}
      >
        Saisir la quantité
      </button>
      <output aria-label="Saisies">{told.join(",")}</output>
    </div>
  );
}

/** The own estimate, mounted as the page mounts it. */
function entry(
  options: {
    readonly structureId?: string;
    readonly late?: boolean;
    readonly recompose?: boolean;
    readonly write?: () => Promise<Outcome<string>>;
    readonly entries?: readonly Entry<NodesWritten>[];
  } = {},
) {
  const write =
    options.write ?? vi.fn(() => Promise.resolve({ kind: "done" as const, data: "ok" }));
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>
        <OwnEstimateEntry
          estimate={{
            projectId: PROJECT,
            revisionId: REVISION,
            structureId: options.structureId ?? LATE,
            label: "Indisponibilité de l’automaticien",
          }}
          late={options.late ?? true}
          recompose={options.recompose ?? false}
        >
          <Cell write={write} />
          <Twice write={write} />
          <Entered entries={options.entries ?? []} />
        </OwnEstimateEntry>
      </main>
    </NextIntlClientProvider>,
  );
  return write;
}

beforeEach(() => {
  server.client = undefined;
});

describe("the first entry into an own estimate in arrears", () => {
  it("lets the entry go, and reads nothing, on an own estimate up to date [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({});
    const write = entry({ late: false });
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    expect(write).toHaveBeenCalledTimes(1);
    expect(client.calls).toEqual([]);
  });

  it("updates without asking when the report signals nothing, reads the nodes again and writes the entry from the counters read [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
    });
    const sent: (Fresh | undefined)[] = [];
    entry({ entries: [quantity(sent)] });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Saisies" })).toHaveTextContent("done");
    });
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES]);
    const read = example("structure_rebase_report_risk_clean") as Report;
    expect(client.calls[1]?.body).toEqual({
      confirmed: true,
      main_structure_lock_version: read.main_structure_lock_version,
      structure_lock_version: read.structure_lock_version,
    });
    // Sent once, from the counters of the nodes read after the update and the structure's answered.
    expect(sent).toHaveLength(1);
    const nodes = example("nodes_risk_estimate") as {
      items: { node_id: string; lock_version: number }[];
    };
    const line = nodes.items.find((node) => node.node_id === LINE);
    expect(sent[0]?.nodes.get(LINE)?.lock_version).toBe(line?.lock_version);
    expect(sent[0]?.structureLockVersion).toBe(
      (example("structure_rebased_risk") as { lock_version: number }).lock_version,
    );
    // Said updated, not withheld: no refusal reached the grid, and no entering again is asked.
    expect(screen.getByText(/a été mis à jour\./)).toBeVisible();
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
    expect(screen.queryByRole("region", { name: "Mise à jour du devis propre" })).toBeNull();
    // Updated once: the next entry goes as it is, and reads nothing more.
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(sent).toHaveLength(2);
    });
    expect(sent[1]).toBeUndefined();
    expect(client.calls).toHaveLength(3);
  });

  it("writes nothing and refuses the entry as the service would when the node is gone after the update, or no longer accepts the field, and says it once [US-3140] [WF-RIS-0070-A]", async () => {
    serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
    });
    const sent: (Fresh | undefined)[] = [];
    entry({
      entries: [
        quantity(sent, { node: ABSENT }),
        quantity(sent, { field: "estimate_line.unit_disbursement" }),
      ],
    });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Saisies" })).toHaveTextContent(
        "NOT_FOUND,VALIDATION_FAILED:/unit_disbursement:FIELD_NOT_ACCEPTED",
      );
    });
    expect(sent).toEqual([]);
    // The refusal is the grid's to tell, where the entry was made: the guard says only the update.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText(/a été mis à jour\./)).toBeVisible();
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("writes an entry made while those held back are still being written after them, from the counters they answered, not from the grid's [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
    });
    const sent: (Fresh | undefined)[] = [];
    const answered = quantity(sent, { moved: 4 });
    // The first write held back for the update is held on its way: the second entry is made meanwhile.
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const first: Entry<NodesWritten> = {
      ...answered,
      send: async (fresh) => {
        const outcome = answered.send(fresh);
        if (sent.length === 1) {
          await held;
        }
        return outcome;
      },
    };
    entry({ entries: [first] });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(sent).toHaveLength(1);
    });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    // Not sent while the one before is not answered, and not from the counters of the grid.
    expect(sent).toHaveLength(1);
    release();
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Saisies" })).toHaveTextContent("done,done");
    });
    expect(sent).toHaveLength(2);
    expect(sent[1]?.nodes.get(LINE)?.lock_version).toBe(4);
    expect(sent[1]?.structureLockVersion).toBe(7);
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES]);
  });

  it("sends a gesture made while an entry is still being written from the counters read, not from the grid's: no stale counter, no 409 [US-3140] [WF-RIS-0070-A]", async () => {
    serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
    });
    const sent: (Fresh | undefined)[] = [];
    const answered = quantity(sent, { moved: 4 });
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const first: Entry<NodesWritten> = {
      ...answered,
      send: async (fresh) => {
        const outcome = answered.send(fresh);
        await held;
        return outcome;
      },
    };
    // A gesture of structure: it touches no field, and carries the counter of the structure.
    const gesture: Entry<NodesWritten> = { nodes: [LINE], fields: [], send: answered.send };
    entry({ entries: [first, gesture] });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(sent).toHaveLength(1);
    });
    release();
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Saisies" })).toHaveTextContent("done,done");
    });
    expect(sent[1]?.nodes.get(LINE)?.lock_version).toBe(4);
    expect(sent[1]?.structureLockVersion).toBe(7);
  });

  it("writes the entries made while the update is under way one after the other, each from the counters the one before answered [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
    });
    const sent: (Fresh | undefined)[] = [];
    // The counters the second entry saw when it was sent: the first answered them.
    const seen: number[] = [];
    const first = quantity(sent, { moved: 4 });
    const second: Entry<NodesWritten> = {
      ...first,
      send: (fresh) => {
        seen.push(fresh?.nodes.get(LINE)?.lock_version ?? -1, fresh?.structureLockVersion ?? -1);
        return first.send(fresh);
      },
    };
    entry({ entries: [first, second] });
    await userEvent.click(screen.getByRole("button", { name: "Saisir la quantité" }));
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Saisies" })).toHaveTextContent("done,done");
    });
    // One reading, one update, one reading of the nodes, and two writes in the order of the entries.
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES]);
    expect(sent).toHaveLength(2);
    expect(seen).toEqual([4, 7]);
  });

  it("starts one reading and one update for the entries made while it is under way [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
    });
    const write = entry();
    await userEvent.click(screen.getByRole("button", { name: "Saisir deux fois" }));
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Réponses" })).toHaveTextContent(
        "conflict,conflict",
      );
    });
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE]);
    expect(write).not.toHaveBeenCalled();
  });

  it("reads the report again at the next entry when the service refuses an entry for the own estimate being out of date [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
    });
    entry({ write: () => Promise.resolve(withheld<string>()) });
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    // Updated: this entry goes, and the service says it late again.
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Réponse" })).toHaveTextContent("conflict");
    });
    expect(client.calls).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, REPORT, REBASE]);
    });
  });

  it("presents a value kept against the project, with the severity and the provision recomputed, and withholds the entry [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({ [REPORT]: "structure_rebase_report_risk" });
    const write = entry();
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    const prompt = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(prompt).toHaveTextContent("garde une valeur contre le projet");
    const recomputed = within(prompt).getByRole("list", {
      name: "Gravité et provision recalculées",
    });
    expect(recomputed).toHaveTextContent("1 249 880,00");
    expect(recomputed).toHaveTextContent("499 952,00");
    expect(within(prompt).getByRole("list", { name: "Écarts par changement" })).toHaveTextContent(
      "gardée par le devis propre",
    );
    expect(write).not.toHaveBeenCalled();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    expect(screen.getByRole("status", { name: "Réponse" })).toHaveTextContent("conflict");
    // Withheld for a confirmation, and nowhere said up to date: nothing was updated.
    expect(prompt).toHaveTextContent("confirmez-la, puis saisissez de nouveau");
    expect(screen.queryByText(/est à jour/)).toBeNull();
    expect(screen.queryByText(/a été mis à jour/)).toBeNull();
    await expectAccessible(prompt);
  });

  it("applies the update once confirmed, with the two counters read, and says it done [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [REPORT]: "structure_rebase_report_risk",
      [REBASE]: "structure_rebased_risk",
    });
    entry();
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    const prompt = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    await userEvent.click(
      within(prompt).getByRole("button", { name: "Confirmer la mise à jour du devis propre" }),
    );
    const read = example("structure_rebase_report_risk") as Report;
    await waitFor(() => {
      expect(client.calls.find((call) => call.route === REBASE)?.body).toEqual({
        confirmed: true,
        main_structure_lock_version: read.main_structure_lock_version,
        structure_lock_version: read.structure_lock_version,
      });
    });
    expect(await screen.findByText(/est à jour\. Saisissez de nouveau/)).toBeVisible();
    expect(screen.queryByRole("region", { name: "Mise à jour du devis propre" })).toBeNull();
  });

  it("says what is to correct in the own estimate when the report refuses, offers no confirmation and withholds the entry [US-3140] [WF-RIS-0070-A]", async () => {
    const client = serve({ [REPORT]: "structure_rebase_report_risk_refused" });
    const write = entry();
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    const prompt = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(prompt).toHaveTextContent("est refusée : corrigez le devis propre");
    expect(within(prompt).getByRole("alert")).toHaveTextContent("motif refuse la mise à jour");
    expect(
      within(prompt).queryByRole("button", { name: "Confirmer la mise à jour du devis propre" }),
    ).toBeNull();
    expect(write).not.toHaveBeenCalled();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    await expectAccessible(prompt);
  });

  it("signals nothing when a report keeps nothing and refuses nothing, whatever the severity it recomputes [US-3140] [WF-RIS-0070-A]", () => {
    expect(signals(example("structure_rebase_report_risk") as Report)).toBe(true);
    expect(signals(example("structure_rebase_report_risk_clean") as Report)).toBe(false);
    expect(signals(example("structure_rebase_report_risk_refused") as Report)).toBe(true);
  });
});

describe("the opening of an own estimate a marking pruned", () => {
  it("recomposes it at once, without a body or a question, and reads no report when it is up to date [US-3140] [WF-RIS-0030]", async () => {
    const client = serve({ [RECOMPOSE]: "structure_recomposed" });
    entry({ structureId: PRUNED, late: false, recompose: true });
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([RECOMPOSE]);
    });
    expect(client.calls[0]?.path).toBe(
      `/projects/${PROJECT}/revisions/${REVISION}/structures/${PRUNED}/recompose`,
    );
    expect(screen.queryByRole("region", { name: "Mise à jour du devis propre" })).toBeNull();
    // Once, though the effect may run twice.
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(client.calls).toHaveLength(1);
  });

  it("does not recompose an own estimate that lists no `recompose` available [US-3140] [WF-RIS-0030]", async () => {
    const client = serve({});
    entry({ structureId: PRUNED, late: false, recompose: false });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(client.calls).toEqual([]);
  });

  it("recomposes an own estimate that stays in arrears, then updates it without a question, and the entry that follows goes [US-3140] [WF-RIS-0030] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [RECOMPOSE]: "structure_recomposed_late",
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
    });
    const write = entry({ structureId: PRUNED, late: false, recompose: true });
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([RECOMPOSE, REPORT, REBASE]);
    });
    await waitFor(() => {
      expect(screen.queryByText(/Mise à jour du devis propre « /)).toBeNull();
    });
    expect(screen.queryByRole("region", { name: "Mise à jour du devis propre" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    expect(write).toHaveBeenCalledTimes(1);
    expect(client.calls).toHaveLength(3);
  });

  it("tells the refusal of the recomposition, and reads and updates nothing [US-3140] [WF-RIS-0030]", async () => {
    const client = serve({
      [RECOMPOSE]: {
        problem: {
          ...(example("structure_recompose_revision_marked") as Problem),
          status: 409 as const,
        },
      },
    });
    entry({ structureId: PRUNED, late: false, recompose: true });
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(client.calls.map((call) => call.route)).toEqual([RECOMPOSE]);
    expect(screen.queryByText(/Recomposition du devis propre/)).toBeNull();
  });

  it("presents at the opening what the update keeps after a recomposition that leaves the own estimate in arrears [US-3140] [WF-RIS-0030] [WF-RIS-0070-A]", async () => {
    const client = serve({
      [RECOMPOSE]: "structure_recomposed_late",
      [REPORT]: "structure_rebase_report_risk",
    });
    const write = entry({ structureId: PRUNED, late: false, recompose: true });
    const prompt = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(prompt).toHaveTextContent("garde une valeur contre le projet");
    expect(client.calls.map((call) => call.route)).toEqual([RECOMPOSE, REPORT]);
    expect(write).not.toHaveBeenCalled();
  });
});
