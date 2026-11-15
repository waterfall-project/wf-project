// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of this segment shows while the server reads the API for it — from the
 * first request as on each navigation that leads to it: the skeleton of a screen, inside the
 * shell, which stays, at the density of the screens of a project out of a
 * revision — its revisions, where its address leads, its settings, its life cycle —; a revision
 * has its own skeleton.
 */
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton density={FUNCTION_DENSITY.revisions} />;
}
