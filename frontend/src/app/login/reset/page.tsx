// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The password forgotten (US-0320), outside the shell, in two steps at one address: without a
 * token, the address to which the API sends a link (`requestPasswordReset`); with the token of
 * that link, the new password (`confirmPasswordReset`).
 */
import { ArrowLeft, KeyRound } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { AskResetLink, ChoosePassword } from "@/components/login/password-reset";
import { WayIn } from "@/components/login/way-in";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { LOGIN_ROUTE, TOKEN_PARAMETER } from "@/navigation/login";
import { requestSession } from "@/session/request";
import { themePreference } from "@/theme/theme";

import { screenMetadata } from "../../title";

/** Title the tab with the password forgotten. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("passwordReset.title");
}

/** The card of the step the address is at: the token of the link, or none yet. */
function ResetCard({ token }: { readonly token: string | undefined }) {
  const t = useTranslations("passwordReset");
  return (
    <Card>
      <CardHeader>
        <CardTitle level="h1" className="text-lg">
          <KeyRound aria-hidden="true" className="size-5 text-muted-foreground" />
          {t(token === undefined ? "title" : "chooseTitle")}
        </CardTitle>
        <CardDescription>{t(token === undefined ? "request" : "choose")}</CardDescription>
      </CardHeader>
      <CardContent>
        {token === undefined ? <AskResetLink /> : <ChoosePassword token={token} />}
      </CardContent>
      <CardFooter>
        <Link href={LOGIN_ROUTE} className="inline-flex items-center gap-1.5 text-sm underline">
          <ArrowLeft aria-hidden="true" className="size-4" />
          {t("back")}
        </Link>
      </CardFooter>
    </Card>
  );
}

/** Render the step of the password forgotten the address is at. */
export default async function PasswordResetPage({
  searchParams,
}: {
  readonly searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([searchParams, requestSession()]);
  const token = pageSearch(search).get(TOKEN_PARAMETER) ?? "";
  return (
    <WayIn theme={themePreference(session?.user)}>
      <ResetCard token={token === "" ? undefined : token} />
    </WayIn>
  );
}
