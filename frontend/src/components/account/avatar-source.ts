// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The image of the avatar of an account, as the browser shows it without calling the API (§4.3.1)
 * and without a relay (WF-ARC-0020): the server of Next reads it (`getUserAvatar`) while it
 * renders the page, and writes it into the page itself, as a `data:` address. Only the screen of
 * the avatar shows it: written into every page, the bytes of an image would weigh on each
 * document the shell renders — the menu of the account shows the initials.
 */
import "server-only";

import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";

import { isAvatarType } from "./avatar-types";

/**
 * The image of the avatar of an account, as an address of the page — or `undefined`, when the API
 * gives no PNG or JPEG image for it: the page then shows the initials, as for an account without
 * one (WF-ADM-0080).
 */
export async function avatarSource(userId: string): Promise<string | undefined> {
  const answer = await reach(() =>
    serverClient().GET("/users/{user_id}/avatar", {
      params: { path: { user_id: userId } },
      parseAs: "blob",
    }),
  );
  const image: unknown = answer?.data;
  if (!(image instanceof Blob) || !isAvatarType(image.type)) {
    return undefined;
  }
  const bytes = Buffer.from(await image.arrayBuffer()).toString("base64");
  return `data:${image.type};base64,${bytes}`;
}
