// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The deposit of a backup copied out of another installation (US-0440, #350): the archive sent in
 * the parts the server cuts it into, then the restoration of the platform from it, at the date its
 * manifest says, confirmed in the dialog of a backup of the list (`RestoreDialog`), by the
 * identifier of the deposit typed.
 */
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { BackupDeposit } from "./backup-commands";
import { Restoration } from "./restoration";

// The server of Next, as far as the deposit needs it: the fake back behind both clients.
const server = vi.hoisted((): { client: ApiClient | undefined; open: ApiClient | undefined } => ({
  client: undefined,
  open: undefined,
}));

vi.mock("@/api/server", () => ({
  serverClient: () => server.client,
  publicClient: () => server.open,
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(),
}));

const RESTORE = "POST /restores";
const PART = "PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}";
const COMPLETION = "POST /chunked-uploads/{chunked_upload_id}/completion";
/** The deposit the server opens (`chunked_upload`), and the upload it completes into. */
const DEPOSIT = "01926f3a-7c00-7000-8000-000000000a02";
const UPLOAD = "01926f3a-7c00-7000-8000-000000000a03";
/** The date the manifest of the archive says (`chunked_upload_completed`). */
const TAKEN_AT = "2026-06-02T01:00:00Z";

/** Serve the fake back, and the probe apart; give the back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  server.open = fakeClient({ "GET /health": "liveness" });
  return client;
}

/** The deposit, within the screen that follows a restoration. */
function deposit() {
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <main>
        <Restoration>
          <BackupDeposit />
        </Restoration>
      </main>
    </NextIntlClientProvider>,
  );
  return screen.getByRole("region", { name: "Restaurer une sauvegarde d’une autre installation" });
}

/** Deposit an archive, and wait for the server to say the date its manifest says. */
async function deposited(region: HTMLElement): Promise<HTMLElement> {
  const archive = new File(["0123456789AB"], "waterfall-2026-06-02.tar");
  await userEvent.upload(within(region).getByLabelText("Archive de la sauvegarde"), archive);
  await userEvent.click(within(region).getByRole("button", { name: "Déposer" }));
  return within(region).findByRole("button", { name: "Restaurer cette sauvegarde" });
}

/** A deposit the server cuts in three parts, then completes. */
const DEPOSITED: FakeAnswers = {
  "POST /chunked-uploads": { status: 201, example: "chunked_upload" },
  [PART]: { status: 200, example: "chunked_upload_part" },
  [COMPLETION]: { status: 201, example: "chunked_upload_completed" },
};

describe("the deposit of a backup of another installation", () => {
  it("sends the archive in the parts the server cuts it into, then restores it at the date its manifest says, its identifier typed [WF-ADM-0160-A]", async () => {
    const client = serve({
      ...DEPOSITED,
      [RESTORE]: { status: 202, example: "task_restore_queued" },
      "GET /tasks/{task_id}": "task_running",
    });
    const region = deposit();
    expect(within(region).getByRole("button", { name: "Déposer" })).toBeDisabled();
    const restore = await deposited(region);
    const date = formatTimestamp(TAKEN_AT, "fr");
    expect(region).toHaveTextContent(`Sauvegarde du ${date} déposée : waterfall-2026-06-02.tar.`);
    expect(client.calls.map(({ path }) => path)).toEqual([
      "/chunked-uploads",
      `/chunked-uploads/${DEPOSIT}/parts/1`,
      `/chunked-uploads/${DEPOSIT}/parts/2`,
      `/chunked-uploads/${DEPOSIT}/parts/3`,
      `/chunked-uploads/${DEPOSIT}/completion`,
    ]);
    expect(client.calls[0]?.body).toEqual({ filename: "waterfall-2026-06-02.tar", size_bytes: 12 });

    // La confirmation nomme la date de la sauvegarde: the one the manifest says, the verification
    // to come, by the restoration itself.
    await userEvent.click(restore);
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    expect(dialog).toHaveAccessibleDescription(
      `La plateforme entière sera remplacée par la sauvegarde du ${date}, dont la vérification est en attente\u00a0: tout ce qui a été saisi depuis sera perdu, sans retour possible. Les utilisateurs sont déconnectés pendant la restauration, qui sera inscrite au journal d’audit.`,
    );
    const confirm = within(dialog).getByRole("button", { name: "Restaurer" });
    expect(confirm).toBeDisabled();
    await userEvent.click(within(dialog).getByRole("textbox"));
    await userEvent.paste(UPLOAD);
    await userEvent.click(confirm);
    expect(
      await screen.findByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).toHaveTextContent("La restauration est en attente");
    expect(client.calls.find(({ route }) => route === RESTORE)?.body).toEqual({
      external_backup_upload_id: UPLOAD,
      acknowledged_backup_taken_at: TAKEN_AT,
      confirmed: true,
    });
  });

  it("says at its date a confirmation the API refuses, and keeps the deposit; closed, the focus back on its command [WF-ADM-0160-A]", async () => {
    serve({
      ...DEPOSITED,
      [RESTORE]: { problem: { code: "CONFIRMATION_REQUIRED", status: 400 } },
    });
    const region = deposit();
    const restore = await deposited(region);
    await userEvent.click(restore);
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    await userEvent.click(within(dialog).getByRole("textbox"));
    await userEvent.paste(UPLOAD);
    // Whether the dialog was still busy in the commit that told the refusal: the request over, never
    // while it holds Escape (#1474).
    const busyWhenTold: (string | null)[] = [];
    const observer = new MutationObserver(() => {
      if (busyWhenTold.length === 0 && within(dialog).queryByRole("alert") !== null) {
        busyWhenTold.push(dialog.getAttribute("aria-busy"));
      }
    });
    observer.observe(dialog, { subtree: true, childList: true, attributes: true });
    await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Cette opération demande une confirmation explicite.",
    );
    observer.disconnect();
    expect(busyWhenTold).toEqual(["false"]);
    expect(
      screen.queryByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(restore).toHaveFocus();
  });

  it("stops at the first refusal, and offers no confirmation of an archive whose date does not read [WF-ADM-0160-A]", async () => {
    serve({
      "POST /chunked-uploads": { status: 201, example: "chunked_upload" },
      [PART]: { status: 200, example: "chunked_upload_part" },
      [COMPLETION]: { problem: { code: "FILE_FORMAT_UNREADABLE", status: 422 } },
    });
    const region = deposit();
    await userEvent.upload(
      within(region).getByLabelText("Archive de la sauvegarde"),
      new File(["x"], "notes.txt"),
    );
    // Whether the choice of a file was still held in the commit that told the refusal: the deposit
    // over, never while another file cannot be chosen (#1484).
    const field = within(region).getByLabelText("Archive de la sauvegarde");
    const heldWhenTold = atCommit(
      region,
      () => within(region).queryByRole("alert") !== null,
      () => (field.hasAttribute("disabled") ? "held" : "free"),
    );
    await userEvent.click(within(region).getByRole("button", { name: "Déposer" }));
    expect(await within(region).findByRole("alert")).toHaveTextContent(
      "Le format du fichier est illisible.",
    );
    expect(heldWhenTold.stop()).toEqual(["free"]);
    expect(within(region).queryByRole("button", { name: "Restaurer cette sauvegarde" })).toBeNull();
  });

  it("notes the deposit once, at the date its manifest says, about the archive deposited", async () => {
    forgetMessages();
    serve(DEPOSITED);
    const region = deposit();
    await deposited(region);
    const date = formatTimestamp(TAKEN_AT, "fr");
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "success",
        sentence: `Sauvegarde du ${date} déposée : waterfall-2026-06-02.tar.`,
        object: "waterfall-2026-06-02.tar",
      }),
    ]);
  });

  it("breaks no rule of accessibility, deposited", async () => {
    serve(DEPOSITED);
    const region = deposit();
    await deposited(region);
    await expectAccessible(region);
  });
});
