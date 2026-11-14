// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of this segment shows while the server reads the API for it — from the
 * first request as on each navigation that leads to it: the skeleton of a screen, inside the
 * shell, which stays, at the density of the account, dense until its recomposition
 * (US-2130).
 */
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton density="dense" />;
}
