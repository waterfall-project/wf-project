// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the backups of the platform (US-0440): a backup asked (`startBackup`), which
 * the worker takes (WF-ADM-0150).
 */
"use server";

import { type BackgroundTask, decodeTask, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** Ask a backup of the whole platform: the worker takes it, and the hand comes back at once. */
export async function startPlatformBackup(): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() => serverClient().POST("/backups"));
}
