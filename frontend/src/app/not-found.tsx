// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one screen "not found", inside the shell: an address that leads to no screen, and one
 * whose object the API does not find or does not let the user read — which it answers alike
 * — show the same body, word for word; the tab keeps the title of the function the address
 * names, which says nothing of the object. Telling them apart would reveal that the object
 * exists (WF-ADM-0110). A link leads back home.
 *
 * Without a session — the API refusing the account of the request for want of one (`getMe`
 * answered 401) —, nothing is "not found": the API answers 404, before any session, an operation
 * it does not serve yet, and the screen, whatever it reads, asks for a session. The screen says so,
 * as the screen of failure says a read refused for want of a session, and offers the sign-in page,
 * which comes back to the address shown (US-0350, WF-SEC-0020, #1000); it goes nowhere by itself,
 * the request having left without a session, which a sign-in the realm refused would loop on
 * (`src/session/tokens.ts`). Every address alike, without a session: nothing is revealed.
 *
 * It answers with the status 200, not 404: every segment that reads the API has its
 * `loading.tsx`, so the response streams, its status is sent with the skeleton before the
 * page knows the object is not found, and Next marks the page `noindex` instead — a soft 404.
 * The status is the same for every address not found, which is what matters here; a loading
 * seen at once is worth more to an application behind a session than a status no crawler
 * reads.
 */
import { House, LockKeyhole, SearchX } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { SignIn } from "@/components/commands/outcome-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { HOME } from "@/navigation/home";
import { requestSessionState } from "@/session/request";

/** The address leads to nothing the user may consult, and back home. */
function NothingHere() {
  const t = useTranslations("notFound");
  return (
    <Screen>
      <PageHeader title={t("title")} icon={SearchX} subtitle={t("explanation")} />
      <Link
        href={HOME}
        className={buttonVariants({ variant: "outline", size: "sm", className: "w-fit" })}
      >
        <House aria-hidden="true" />
        {t("home")}
      </Link>
    </Screen>
  );
}

/** The screen asks for a session, and the sign-in page comes back to it. */
function SessionRequired() {
  const t = useTranslations("failure.signedOut");
  return (
    <Screen>
      <PageHeader title={t("title")} icon={LockKeyhole} subtitle={t("explanation")} />
      <SignIn />
    </Screen>
  );
}

/** Render the screen "not found", or, without a session, the screen that asks for one. */
export default async function NotFound() {
  const state = await requestSessionState();
  return state.kind === "signed_out" ? <SessionRequired /> : <NothingHere />;
}
