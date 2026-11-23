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

import { useEntryGuard } from "./entry-guard";
import { OwnEstimateEntry } from "./own-estimate-entry";
import { signals } from "./rebase-report";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));

type Report = components["schemas"]["StructureRebaseReport"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The own estimate in arrears of the structures of the witness (`structures`), and the one a marking pruned.
const LATE = "01926f3a-7c00-7000-8000-000000000206";
const PRUNED = "01926f3a-7c00-7000-8000-000000000209";
const STRUCTURE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REPORT = `GET ${STRUCTURE}/rebase` as const;
const REBASE = `POST ${STRUCTURE}/rebase` as const;
const RECOMPOSE = `POST ${STRUCTURE}/recompose` as const;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/**
 * Serve the report of an example with what it keeps lifted: a report that signals nothing, which the
 * contract gives no example of. Derived from the example the contract gives, never written by hand.
 */
function servedWithoutWhatItKeeps(name: "structure_rebase_report_risk"): FakeClient {
  const client = serve({ [REPORT]: name, [REBASE]: "structure_rebased_risk" });
  const report = example(name) as Report;
  const lifted = { ...report, differences: report.differences.filter((d) => d.change !== "kept") };
  // The call is made, and recorded, as any other: only the body it reads is the derived one.
  server.client = new Proxy(client, {
    get(target, property, receiver): unknown {
      if (property !== "GET") {
        return Reflect.get(target, property, receiver) as unknown;
      }
      return async (...args: unknown[]) => {
        const answer = (await Reflect.apply(target.GET, target, args)) as object;
        return String(args[0]).endsWith("/rebase") ? { ...answer, data: lifted } : answer;
      };
    },
  });
  return client;
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

/** The own estimate, mounted as the page mounts it. */
function entry(
  options: {
    readonly structureId?: string;
    readonly late?: boolean;
    readonly recompose?: boolean;
    readonly write?: () => Promise<Outcome<string>>;
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

  it("updates without asking, then enters, when the report signals nothing [US-3140] [WF-RIS-0070-A]", async () => {
    const client = servedWithoutWhatItKeeps("structure_rebase_report_risk");
    const write = entry();
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    await waitFor(() => {
      expect(write).toHaveBeenCalledTimes(1);
    });
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE]);
    const read = example("structure_rebase_report_risk") as Report;
    expect(client.calls[1]?.body).toEqual({
      confirmed: true,
      main_structure_lock_version: read.main_structure_lock_version,
      structure_lock_version: read.structure_lock_version,
    });
    expect(screen.queryByRole("region", { name: "Mise à jour du devis propre" })).toBeNull();
    // Updated once: the next entry reads nothing more until the screen says it late again.
    await userEvent.click(screen.getByRole("button", { name: "Saisir" }));
    expect(write).toHaveBeenCalledTimes(2);
    expect(client.calls).toHaveLength(2);
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
    const report = example("structure_rebase_report_risk") as Report;
    expect(signals(report)).toBe(true);
    expect(
      signals({ ...report, differences: report.differences.filter((d) => d.change !== "kept") }),
    ).toBe(false);
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
});
