// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { changePassword, removeAvatar, replaceAvatar } from "./account";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A form that carries a file in its field `avatar`, as the browser sends it. */
function formWith(file: File): FormData {
  const form = new FormData();
  form.set("avatar", file);
  return form;
}

// The eight bytes that open every PNG file, standing for an image.
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

beforeEach(() => {
  refresh.mockReset();
});

describe("the server actions of the account", () => {
  it("change the password with what was typed, which the API judges", async () => {
    const client = serve({ "PUT /me/password": { status: 204 } });
    const change = { current_password: "ancien mot de passe", new_password: "court" };
    expect(await changePassword(change)).toEqual({ kind: "done", data: null });
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["PUT /me/password", change],
    ]);

    const refused = { code: "VALIDATION_FAILED", status: 422 } as const;
    serve({ "PUT /me/password": { problem: refused } });
    expect(await changePassword(change)).toMatchObject({ kind: "refused", problem: refused });
    serve({ "PUT /me/password": { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    expect(await changePassword(change)).toMatchObject({ kind: "signed_out" });
  });

  it("send the image of the avatar itself, with its media type, and render the page again", async () => {
    const client = serve({ "PUT /me/avatar": { status: 204 } });
    const image = new File([PNG], "camille.png", { type: "image/png" });

    expect(await replaceAvatar(formWith(image))).toEqual({ kind: "done", data: null });

    const [call] = client.calls;
    expect(call?.route).toBe("PUT /me/avatar");
    expect(call?.body).toBeInstanceOf(Blob);
    const body = call?.body as Blob;
    expect(body.type).toBe("image/png");
    expect(new Uint8Array(await body.arrayBuffer())).toEqual(PNG);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("tell an image the API finds too large, and render nothing again", async () => {
    const tooLarge = { code: "FILE_TOO_LARGE", status: 413 } as const;
    serve({ "PUT /me/avatar": { problem: tooLarge } });
    const image = new File([PNG], "camille.jpg", { type: "image/jpeg" });
    expect(await replaceAvatar(formWith(image))).toMatchObject({
      kind: "refused",
      problem: tooLarge,
    });
    expect(refresh).not.toHaveBeenCalled();
  });

  it("send no image but a PNG or a JPEG, nor a form without one", async () => {
    const client = serve({ "PUT /me/avatar": { status: 204 } });
    const gif = new File([PNG], "camille.gif", { type: "image/gif" });
    await expect(replaceAvatar(formWith(gif))).rejects.toThrow("an avatar is a PNG or JPEG image");
    await expect(replaceAvatar(new FormData())).rejects.toThrow(TypeError);
    expect(client.calls).toEqual([]);
  });

  it("withdraw the avatar, and render the page again", async () => {
    const client = serve({ "DELETE /me/avatar": { status: 204 } });
    expect(await removeAvatar()).toEqual({ kind: "done", data: null });
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /me/avatar"]);
    expect(refresh).toHaveBeenCalledOnce();
  });
});
