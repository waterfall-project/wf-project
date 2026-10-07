// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Every address no screen of its own answers: each function of the navigation and each leaf
 * with a screen has its page (`functions.json`), which wins over this one, and any other address
 * leads to the one screen « not found » (`not-found.tsx`) — the same screen an object the API
 * does not find, or does not let the user read, leads to (WF-ADM-0110), with the same status: its
 * skeleton (`loading.tsx`) makes the response stream, as there.
 */
import { notFound } from "next/navigation";

/** Answer an address that leads to no screen: not found. */
export default function NoScreen(): never {
  notFound();
}
