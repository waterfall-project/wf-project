// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { abandonFileImport, applyFileImport, openFileImport, requestFileExport } from "./exchanges";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const UPLOAD = "POST /file-uploads";
const OPEN = "POST /projects/{project_id}/imports";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A form that carries a file in its field `file`, as the browser sends it. */
function formWith(): FormData {
  const form = new FormData();
  form.set("file", new File(["devis"], "devis-poste-de-commande.xlsx"));
  return form;
}

beforeEach(() => {
  refresh.mockReset();
});

describe("the server actions of the exchanges", () => {
  it("deposit the file, then open its import as the kind chosen, on the file deposited", async () => {
    const client = serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: { example: "import_analysing", status: 202 },
    });
    expect(await openFileImport(PROJECT, { kind: "estimate" }, formWith())).toEqual({
      kind: "done",
      data: example("import_analysing"),
    });
    const [upload, open] = client.calls;
    expect(upload?.route).toBe(UPLOAD);
    const file = (upload?.body as FormData).get("file");
    expect(file).toBeInstanceOf(File);
    expect((file as File).name).toBe("devis-poste-de-commande.xlsx");
    expect(await (file as File).text()).toBe("devis");
    // The deposit says it is for an import, which the contract bounds at 10 MiB.
    expect((upload?.body as FormData).get("purpose")).toBe("import");
    expect(open?.path).toBe(`/projects/${PROJECT}/imports`);
    expect(open?.body).toEqual({
      kind: "estimate",
      upload_id: "01926f3a-7c00-7000-8000-000000000a01",
    });
  });

  it("open nothing when the deposit is refused, and send no form without a file", async () => {
    const tooLarge = { code: "FILE_TOO_LARGE", status: 413 } as const;
    const client = serve({ [UPLOAD]: { problem: tooLarge } });
    expect(await openFileImport(PROJECT, { kind: "actual_costs" }, formWith())).toMatchObject({
      kind: "refused",
      problem: tooLarge,
    });
    expect(client.calls.map((call) => call.route)).toEqual([UPLOAD]);
    await expect(openFileImport(PROJECT, { kind: "estimate" }, new FormData())).rejects.toThrow(
      TypeError,
    );
    expect(client.calls).toHaveLength(1);
  });

  it("apply an import confirmed, which gives a task back, and read the screen anew", async () => {
    const client = serve({
      "POST /projects/{project_id}/imports/{import_id}/apply": {
        example: "task_import_queued",
        status: 202,
      },
    });
    expect(await applyFileImport(PROJECT, IMPORT)).toEqual({
      kind: "done",
      data: example("task_import_queued"),
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/projects/${PROJECT}/imports/${IMPORT}/apply`, { confirmed: true }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();

    const expired = { code: "STATE_FORBIDS_OPERATION", status: 409 } as const;
    serve({ "POST /projects/{project_id}/imports/{import_id}/apply": { problem: expired } });
    expect(await applyFileImport(PROJECT, IMPORT)).toMatchObject({ kind: "conflict" });
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("abandon an import, and ask an export of the kind chosen", async () => {
    const client = serve({
      "DELETE /projects/{project_id}/imports/{import_id}": { status: 204 },
      "POST /projects/{project_id}/exports": { example: "task_export_queued", status: 202 },
    });
    expect(await abandonFileImport(PROJECT, IMPORT)).toEqual({ kind: "done", data: null });
    // The revision exported is always named: its command `export_estimate` judges the export (#359).
    const request = {
      kind: "estimate",
      revision_id: "01926f3a-7c00-7000-8000-000000000102",
    } as const;
    expect(await requestFileExport(PROJECT, request)).toEqual({
      kind: "done",
      data: example("task_export_queued"),
    });
    expect(client.calls.map(({ route, path, body }) => [route, path, body])).toEqual([
      [
        "DELETE /projects/{project_id}/imports/{import_id}",
        `/projects/${PROJECT}/imports/${IMPORT}`,
        undefined,
      ],
      ["POST /projects/{project_id}/exports", `/projects/${PROJECT}/exports`, request],
    ]);
  });
});
