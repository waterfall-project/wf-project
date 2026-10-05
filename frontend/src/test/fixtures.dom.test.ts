// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { fakeClient } from "./fixtures";

// In the document of the component tests: a client component uploads from there.
describe("fakeClient, under a document", () => {
  it("records a multipart body as a form, its file named", async () => {
    const client = fakeClient({
      "POST /file-uploads": { problem: { code: "FILE_TOO_LARGE", status: 413 } },
    });
    const form = new FormData();
    // A File, as an <input type="file"> gives it: happy-dom drops the name given with a Blob.
    form.append("file", new File(["a;b"], "costs.csv", { type: "text/csv" }));
    const { error } = await client.POST("/file-uploads", {
      body: { file: "costs.csv", purpose: "import" },
      bodySerializer: () => form,
    });
    expect(error).toEqual({ code: "FILE_TOO_LARGE", status: 413 });
    const body = client.calls[0]?.body;
    expect(body).toBeInstanceOf(FormData);
    const file = body instanceof FormData ? body.get("file") : null;
    expect(file instanceof File ? [file.name, await file.text()] : null).toEqual([
      "costs.csv",
      "a;b",
    ]);
  });

  it("records another body as a blob", async () => {
    const client = fakeClient({ "PUT /me/avatar": { status: 204 } });
    await client.PUT("/me/avatar", {
      body: "png",
      bodySerializer: (body: string) => new Blob([body], { type: "image/png" }),
      headers: { "content-type": "image/png" },
    });
    const body = client.calls[0]?.body;
    expect(body).toBeInstanceOf(Blob);
    expect(body instanceof Blob ? await body.text() : null).toBe("png");
  });
});
