// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { Project } from "@/components/context/reading";
import { TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { ImportCommands } from "./import-commands";
import { importOffers } from "./offers";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;
const UPLOAD = "POST /file-uploads";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Fill the form of the actual costs with a file of a given name, send it, and give the form back. */
async function deposit(name: string, locale: "fr" | "en" = "fr") {
  const offers = importOffers(example("project") as Project);
  render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <TaskTracker>
        <main>
          <ImportCommands projectId={PROJECT} offers={offers} start={START} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
  const fr = locale === "fr";
  const title = fr ? "Importer des coûts réels" : "Import actual costs";
  await userEvent.click(screen.getByRole("button", { name: title }));
  const form = screen.getByRole("form", { name: title });
  await userEvent.upload(
    within(form).getByLabelText(fr ? "Fichier à importer" : "File to import"),
    new File(["x"], name),
  );
  await userEvent.click(
    within(form).getByRole("button", { name: fr ? "Analyser le fichier" : "Analyse the file" }),
  );
  await waitFor(() => {
    expect(form).toHaveAttribute("aria-busy", "false");
  });
  return form;
}

beforeEach(() => {
  router.push.mockClear();
});

describe("the refusals of the deposit of a file [US-3240]", () => {
  it("tells the twenty pending deposits in the words of the catalogue, under the form [WF-DAT-0120-A]", async () => {
    const client = serve({
      [UPLOAD]: { problem: example("file_upload_pending_limit") as Problem & { status: 409 } },
    });
    const form = await deposit("couts.xlsx");
    const told = within(form).getByRole("alert");
    expect(told).toHaveTextContent(CATALOGUES.fr.errors.STATE_FORBIDS_OPERATION);
    expect(told).toHaveTextContent("moins de vingt imports en attente pour le compte");
    expect(told).toHaveTextContent("Nombre maximal d’imports en attente : 20.");
    expect(client.calls.map((call) => call.route)).toEqual([UPLOAD]);
    expect(router.push).not.toHaveBeenCalled();
  });

  it("tells the twenty pending deposits in English [WF-DAT-0120-A]", async () => {
    serve({
      [UPLOAD]: { problem: example("file_upload_pending_limit") as Problem & { status: 409 } },
    });
    const form = await deposit("costs.xlsx", "en");
    const told = within(form).getByRole("alert");
    expect(told).toHaveTextContent("fewer than twenty pending imports for the account");
    expect(told).toHaveTextContent("Maximum number of pending imports: 20.");
  });

  it("tells a name that holds the NUL character as an invalid datum, under the form [US-3240]", async () => {
    const client = serve({
      [UPLOAD]: { problem: example("file_upload_filename_nul") as Problem & { status: 422 } },
    });
    const form = await deposit("couts.xlsx");
    expect(within(form).getByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.VALIDATION_FAILED,
    );
    expect(client.calls.map((call) => call.route)).toEqual([UPLOAD]);
  });

  it("tells a deposit refused for the lack of the permission, and names it [WF-ADM-0020-A]", async () => {
    serve({
      [UPLOAD]: { problem: example("file_upload_permission_missing") as Problem & { status: 403 } },
    });
    const form = await deposit("couts.xlsx");
    const told = within(form).getByRole("alert");
    expect(told).toHaveTextContent(CATALOGUES.fr.errors.PERMISSION_MISSING);
    expect(told).toHaveTextContent("Permission requise : Modifier la planification.");
  });
});
