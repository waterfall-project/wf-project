// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of this segment shows while the server reads the API for it — from the
 * first request as on each navigation that leads to it: the skeleton of a screen, inside the
 * shell, which stays, at the density of the screens of the administration but
 * the audit log, which has its own skeleton.
 */
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton density={FUNCTION_DENSITY.users} />;
}
