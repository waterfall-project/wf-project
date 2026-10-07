// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What an address no screen answers shows before it is found not to be one: the skeleton of a
 * screen, inside the shell, as every segment that reads the API shows it — so that its response
 * streams, and answers with the same status as an object the API does not find (`not-found.tsx`,
 * WF-ADM-0110).
 */
import { ScreenSkeleton } from "@/components/system/screen-skeleton";

/** Render the skeleton of the screen that loads. */
export default function Loading() {
  return <ScreenSkeleton />;
}
