// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Root layout of the application: the HTML document every page renders into, in the
 * language of the request (WF-INTF-0160) and in the mode the account asks for — none forced
 * when it follows the workstation —, inside the shell, its side bar as the user left it.
 */
import "@/theme/globals.css";

import { GeistSans } from "geist/font/sans";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { createTranslator } from "next-intl";
import type { ReactNode } from "react";

import { listRunningTasks } from "@/api/actions/tasks";
import type { BackgroundTask } from "@/api/problem";
import { Shell, type ShellProps } from "@/components/shell/shell";
import { SIDEBAR_COOKIE, sidebarOpen } from "@/components/ui/sidebar-state";
import { CATALOGUES } from "@/i18n/catalogues";
import { requestLanguage } from "@/i18n/request";
import { LAST_CONTEXT_COOKIE, rememberedAddress } from "@/navigation/context";
import { requestSessionState, type SessionState } from "@/session/request";
import { forcedTheme, themePreference } from "@/theme/theme";

/** Title the document, in the language of the request; a page names its screen. */
export async function generateMetadata(): Promise<Metadata> {
  const { locale } = await requestLanguage();
  const t = createTranslator({ locale, messages: CATALOGUES[locale] });
  return { title: t("app.name") };
}

/**
 * What the navigation offers for a session: its permissions when it is open; none when the
 * API says there is no session; the status screen alone when it cannot be read.
 */
function offered(state: SessionState): ShellProps["permissions"] {
  if (state.kind === "open") {
    return state.session.permissions;
  }
  return state.kind === "unreadable" ? "unreadable" : undefined;
}

/**
 * The tasks of the user that still run, read with the document for the tracker of the shell to
 * follow — a data of the page, read on the server, rather than a server action as the shell
 * mounts: none without a session, nor when the API does not give them. Asked alongside the
 * session, which it does not wait for: the page opens no later for it.
 */
async function running(state: Promise<SessionState>): Promise<readonly BackgroundTask[]> {
  // What the tracker may do without never takes a page down: a read that fails is none.
  const [read, outcome] = await Promise.all([
    state,
    listRunningTasks().catch(() => ({ kind: "unreachable" }) as const),
  ]);
  return read.kind === "open" && outcome.kind === "done" ? outcome.data : [];
}

/** Render the document around a page. */
export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  // One read of the session for the request, whose account decides the language and the
  // mode, and whose permissions the navigation offers; the language is the request's, read
  // once, whatever else asks for it.
  const session = requestSessionState();
  const [state, { locale, preference }, jar, tasks] = await Promise.all([
    session,
    requestLanguage(),
    cookies(),
    running(session),
  ]);
  const account = state.kind === "open" ? state.session.user : undefined;
  const theme = themePreference(account);
  return (
    <html lang={locale} data-theme={forcedTheme(theme)} className={GeistSans.variable}>
      <body>
        <Shell
          locale={locale}
          account={account}
          preference={preference}
          theme={theme}
          permissions={offered(state)}
          remembered={rememberedAddress(jar.get(LAST_CONTEXT_COOKIE)?.value)}
          sidebarOpen={sidebarOpen(jar.get(SIDEBAR_COOKIE)?.value)}
          running={tasks}
        >
          {children}
        </Shell>
      </body>
    </html>
  );
}
