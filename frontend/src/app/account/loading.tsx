// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the account show while the server reads the account for them: the
 * skeleton of a screen, inside the shell, which stays.
 */
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton />;
}
