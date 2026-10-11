// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sign-in that could not be made (#687): the identity provider or the store of the sessions
 * out of reach, or silent past its time, at `/login` or at the return of the sign-in. Said as the
 * service out of reach, never a bare error, with the way to try the sign-in again, which comes
 * back to the screen it aimed at (`next`, held to `returnTarget`) — a plain link: `/login` sends
 * the browser to another site, which the router would fetch.
 */
import { CircleAlert, LogIn } from "lucide-react";
import { useTranslations } from "next-intl";

import { loginHref, NEXT_PARAMETER } from "@/navigation/login";

/** The query of the page, as Next gives it. */
interface UnavailableProps {
  readonly searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** What the page says, and the way to sign in again. */
function Unavailable({ href }: { readonly href: string }) {
  const t = useTranslations();
  return (
    <main className="space-y-4 px-5 py-4">
      <div role="alert" className="space-y-2">
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <CircleAlert aria-hidden="true" className="size-5 shrink-0 text-destructive" />
          {t("failure.unreachable.title")}
        </h1>
        <p>{t("failure.signInUnreachable")}</p>
      </div>
      <a href={href} className="inline-flex items-center gap-1.5 font-medium underline">
        <LogIn aria-hidden="true" className="size-4" />
        {t("outcome.signIn")}
      </a>
    </main>
  );
}

/** Render the sign-in that could not be made, and the way to try it again. */
export default async function SignInUnavailablePage({ searchParams }: UnavailableProps) {
  const next = (await searchParams)[NEXT_PARAMETER];
  return <Unavailable href={loginHref(typeof next === "string" ? next : "")} />;
}
