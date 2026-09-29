// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sign-in page (US-0320), outside the shell: the providers the installation offers, read
 * without a session (`listAuthProviders`), and the way back to the screen the user was headed
 * for (`next`), which a refusal for want of a session (401) names — only a path of this front is
 * followed (`returnTarget`).
 *
 * EP-03 connects it to the real authentication: the fake back grants the session the whole
 * mock-up starts from, and this page gives it a door.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { SignIn } from "@/components/login/sign-in";
import { WayIn } from "@/components/login/way-in";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { NEXT_PARAMETER, returnTarget } from "@/navigation/login";
import { requestSession } from "@/session/request";
import { themePreference } from "@/theme/theme";

import { screenMetadata } from "../title";

/** Title the tab with the sign-in page. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("signIn.title");
}

/** Render the sign-in page, which leads to the screen `next` names once signed in. */
export default async function LoginPage({
  searchParams,
}: {
  readonly searchParams: Promise<PageSearchParams>;
}) {
  const [search, providers, session] = await Promise.all([
    searchParams,
    readOrFail("listAuthProviders", () => serverClient().GET("/session/providers")),
    requestSession(),
  ]);
  return (
    <WayIn theme={themePreference(session?.user)}>
      <SignIn providers={providers} target={returnTarget(pageSearch(search).get(NEXT_PARAMETER))} />
    </WayIn>
  );
}
