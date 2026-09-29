// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The images an avatar may be: the media types the contract declares for `putMyAvatar`, and
 * none other. The form offers only those, and the server action sends only those: a picture of
 * another kind would be a request the API is bound to refuse.
 */
import type { paths } from "@/api/generated/schema";

/** A media type of an avatar, as the contract declares them. */
export type AvatarType = keyof paths["/me/avatar"]["put"]["requestBody"]["content"];

// Typed on the contract: a media type it adds or withdraws fails the type check until it is
// named here.
const TYPES: Readonly<Record<AvatarType, true>> = { "image/png": true, "image/jpeg": true };

/** The media types of an avatar, as the `accept` of a file field lists them. */
export const AVATAR_ACCEPT = Object.keys(TYPES).join(",");

/** Whether a file is an image an avatar may be, by its media type. */
export function isAvatarType(type: string): type is AvatarType {
  return Object.hasOwn(TYPES, type);
}
