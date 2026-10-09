// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the sign-in page shows while the server reads the providers of the installation: the
 * skeleton of a screen.
 */
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton />;
}
