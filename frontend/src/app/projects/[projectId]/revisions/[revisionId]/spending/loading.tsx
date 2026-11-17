// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of this segment shows while the server reads the API for it, from the first
 * request as on each navigation that leads to it: the skeleton of a screen, inside the shell,
 * which stays. Its density is that of the spending projection, a screen of consultation among
 * the screens of work of a revision.
 */
import { LEAF_DENSITY } from "@/components/shell/function-display";
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton density={LEAF_DENSITY["FBS-4.4.5"]} />;
}
