// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The boundary of the pages: an error a page throws — the API out of reach, an unexpected
 * answer of it, a defect — shows the screen of failure inside the shell, whose navigation
 * stays, rather than the page of Next. An error of the root layout itself is left to
 * `global-error.tsx`.
 */
"use client";

import type { BoundaryError } from "@/components/system/failure";
import { SystemFailure } from "@/components/system/system-failure";

/** Render the screen of failure in place of the page. */
export default function PageError({
  error,
  retry,
}: {
  readonly error: BoundaryError;
  readonly retry: () => void;
}) {
  return <SystemFailure error={error} retry={retry} />;
}
