// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the account of the user (`changeMyPassword`, `putMyAvatar`,
 * `deleteMyAvatar`): the screens of the account ask the server of Next, which calls the API
 * (§4.3.1), and get back the outcome the one decoder makes of its answer
 * (`src/api/problem.ts`). The API judges the new password — the front copies none of its rules
 * (WF-ADM-0140) — and the size of the image.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";
import { isAvatarType } from "@/components/account/avatar-types";

type PasswordChange = components["schemas"]["PasswordChange"];

/**
 * The outcome of a change of the avatar, and the page rendered again once it is done: the next
 * render reads the account anew, with or without its image.
 */
function applied<T>(outcome: Outcome<T>): Settled {
  if (outcome.kind === "done") {
    refresh();
  }
  return settled(outcome);
}

/**
 * Change the password of a local account, the current one given (WF-ADM-0140). An account of
 * the directory or of the identity provider has none in Waterfall: the API refuses it.
 */
export async function changePassword(change: PasswordChange): Promise<Settled> {
  return settled(await decode(() => serverClient().PUT("/me/password", { body: change })));
}

/**
 * Put an image as the avatar of the account, or replace it (WF-ADM-0080). The browser sends it
 * in a form, which a server action receives as multipart; the API receives the image itself,
 * with its media type, as the contract declares it. A form without a PNG or JPEG image is no
 * request of this front — its field accepts nothing else —, and is not sent.
 */
export async function replaceAvatar(form: FormData): Promise<Settled> {
  const image = form.get("avatar");
  if (!(image instanceof Blob) || !isAvatarType(image.type)) {
    throw new TypeError("an avatar is a PNG or JPEG image");
  }
  const type = image.type;
  return applied(
    await decode(() =>
      serverClient().PUT("/me/avatar", {
        // The contract types a binary body as a string: the bytes go as they are, untouched by
        // the JSON serialisation of the client.
        body: image as unknown as string,
        bodySerializer: (bytes) => bytes,
        headers: { "Content-Type": type },
      }),
    ),
  );
}

/** Withdraw the avatar: the account shows its default image again (WF-ADM-0080). */
export async function removeAvatar(): Promise<Settled> {
  return applied(await decode(() => serverClient().DELETE("/me/avatar")));
}
