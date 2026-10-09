// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The frame of the way in — the sign-in page, the password forgotten —, which stands outside the
 * shell (`ShellFrame`): the logo of the product above one card, in the middle of the page.
 */
import type { ReactNode } from "react";

import { Logo } from "@/components/shell/logo";
import type { ThemePreference } from "@/theme/theme";

/** The mode the logo is drawn in — the account's, when a session is open —, and the card. */
export interface WayInProps {
  readonly theme: ThemePreference | undefined;
  readonly children: ReactNode;
}

/** Render a page of the way in. */
export function WayIn({ theme, children }: WayInProps) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-5 py-10">
      <Logo theme={theme} />
      <div className="w-full max-w-sm">{children}</div>
    </main>
  );
}
