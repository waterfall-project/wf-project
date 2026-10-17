// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sign-in that could not be made (#687): the identity provider or the store of the sessions
 * out of reach, or silent past its time, at `/login` or at the return of the sign-in. Said as the
 * service out of reach, never a bare error, with the way to try the sign-in again, which comes
 * back to the screen it aimed at (`next`, held to `returnTarget`), and asks for the identifiers
 * again when the one that failed did (`reauthenticate`, #855) — a plain link: `/login` sends the
 * browser to another site, which the router would fetch.
 */
import { CircleAlert, LogIn } from "lucide-react";
import { useTranslations } from "next-intl";

import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { loginHref, NEXT_PARAMETER, REAUTHENTICATE_PARAMETER } from "@/navigation/login";

/** The query of the page, as Next gives it. */
interface UnavailableProps {
  readonly searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** What the page says, and the way to sign in again. */
function Unavailable({ href }: { readonly href: string }) {
  const t = useTranslations();
  return (
    <Screen>
      <PageHeader
        title={t("failure.unreachable.title")}
        icon={CircleAlert}
        subtitle={t("failure.signInUnreachable")}
      />
      <a
        href={href}
        className={buttonVariants({ variant: "outline", size: "sm", className: "w-fit" })}
      >
        <LogIn aria-hidden="true" />
        {t("outcome.signIn")}
      </a>
    </Screen>
  );
}

/** Render the sign-in that could not be made, and the way to try it again. */
export default async function SignInUnavailablePage({ searchParams }: UnavailableProps) {
  const query = await searchParams;
  const next = query[NEXT_PARAMETER];
  const href = loginHref(
    typeof next === "string" ? next : "",
    query[REAUTHENTICATE_PARAMETER] !== undefined,
  );
  return <Unavailable href={href} />;
}
