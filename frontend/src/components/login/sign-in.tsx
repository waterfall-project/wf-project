// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sign-in page (US-0320): the providers the installation offers (`listAuthProviders`,
 * WF-ADM-0180). The local accounts always, by their address and their password, which the
 * accounts of the directory share when the installation enables it — the page names it —; the
 * identity provider when it is enabled, by a button that leaves for the starting point the API
 * gives it (`start_url`, TFX-07) — one without it cannot be started, and is not offered —; and
 * the password forgotten, in two steps (`/login/reset`).
 */
import { Fingerprint, KeyRound, LogIn } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PASSWORD_RESET_ROUTE } from "@/navigation/login";

import { SignInForm } from "./sign-in-form";

/** A provider of authentication, as the API lists them. */
export type AuthProvider = components["schemas"]["AuthProvider"];

/** An identity provider the page can start: enabled, with its starting point. */
type Startable = AuthProvider & { readonly start_url: string };

/** The providers the installation lists, and where the browser goes once signed in. */
export interface SignInProps {
  readonly providers: readonly AuthProvider[];
  readonly target: string;
}

/** Whether a provider is an identity provider the page can start. */
function isStartable(provider: AuthProvider): provider is Startable {
  return provider.kind === "oidc" && provider.is_enabled && typeof provider.start_url === "string";
}

/** The button of an identity provider, named after it when the installation names it. */
function IdentityProvider({ provider }: { readonly provider: Startable }) {
  const t = useTranslations("signIn");
  return (
    <a
      href={provider.start_url}
      className={buttonVariants({ variant: "outline", className: "w-full" })}
    >
      <Fingerprint aria-hidden="true" />
      {provider.label == null
        ? t("identityProvider")
        : t("namedIdentityProvider", { provider: provider.label })}
    </a>
  );
}

/** What the form takes: the local accounts, and those of the directory when it is enabled. */
function useAccounts(providers: readonly AuthProvider[]): string {
  const t = useTranslations("signIn");
  const directory = providers.find((provider) => provider.kind === "ldap" && provider.is_enabled);
  if (directory === undefined) {
    return t("local");
  }
  return directory.label == null
    ? t("directory")
    : t("namedDirectory", { directory: directory.label });
}

/** Render the card of the sign-in page. */
export function SignIn({ providers, target }: SignInProps) {
  const t = useTranslations("signIn");
  const accounts = useAccounts(providers);
  const identity = providers.filter(isStartable);
  return (
    <Card>
      <CardHeader>
        <CardTitle level="h1" className="text-lg">
          <LogIn aria-hidden="true" className="size-5 text-muted-foreground" />
          {t("title")}
        </CardTitle>
        <CardDescription>{accounts}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <SignInForm target={target} />
        {identity.length === 0 ? null : (
          <>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <Separator className="flex-1" />
              {t("or")}
              <Separator className="flex-1" />
            </div>
            {identity.map((provider) => (
              <IdentityProvider key={provider.start_url} provider={provider} />
            ))}
          </>
        )}
      </CardContent>
      <CardFooter>
        <Link
          href={PASSWORD_RESET_ROUTE}
          className="inline-flex items-center gap-1.5 text-sm underline"
        >
          <KeyRound aria-hidden="true" className="size-4" />
          {t("forgotten")}
        </Link>
      </CardFooter>
    </Card>
  );
}
