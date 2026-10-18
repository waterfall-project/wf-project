// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one screen "not found", inside the shell: an address that leads to no screen, and one
 * whose object the API does not find or does not let the user read — which it answers alike
 * — show the same body, word for word; the tab keeps the title of the function the address
 * names, which says nothing of the object. Telling them apart would reveal that the object
 * exists (WF-ADM-0110). A link leads back home.
 *
 * The API refusing the session of the request (`getMe` answered 401), nothing is "not found": the
 * API answers 404, before any session, an operation it does not serve yet, and the screen, whatever
 * it reads, wants a session it cannot have. The screen says why, as the screen of failure says a
 * read the API refused, from the same table (`FAILURE_TEXTS`) and with the same way out
 * (`FailureWayOut`): without a session, the sign-in page, which comes back to the address shown
 * (US-0350, WF-SEC-0020, #1000); the session closed, a sign-in that asks for the identifiers again
 * (#855); the account deactivated, nothing; not admitted, the way out of the session of the realm
 * (#664). It goes nowhere by itself, the request having left without a session, which a sign-in the
 * realm refused would loop on (`src/session/tokens.ts`). Every address alike: nothing is revealed.
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

import { PageHeader, Screen } from "@/components/shell/page-header";
import { FAILURE_TEXTS } from "@/components/system/failure";
import { FailureWayOut } from "@/components/system/system-failure";
import { buttonVariants } from "@/components/ui/button";
import { HOME } from "@/navigation/home";
import { requestSessionState, type SessionState } from "@/session/request";

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

/** A session the API refuses: the four refusals of `SessionState`, failures of the screen alike. */
type SessionRefusal = Exclude<SessionState["kind"], "open" | "unreadable">;

/** The screen says why the API refuses the session, and offers the way out the refusal has. */
function SessionRefused({ kind }: { readonly kind: SessionRefusal }) {
  const t = useTranslations("failure");
  return (
    <Screen>
      <PageHeader
        title={t(`${FAILURE_TEXTS[kind]}.title`)}
        icon={LockKeyhole}
        subtitle={t(`${FAILURE_TEXTS[kind]}.explanation`)}
      />
      <FailureWayOut kind={kind} />
    </Screen>
  );
}

/** Render the screen "not found", or, the session refused, the screen that says why. */
export default async function NotFound() {
  const state = await requestSessionState();
  return state.kind === "open" || state.kind === "unreadable" ? (
    <NothingHere />
  ) : (
    <SessionRefused kind={state.kind} />
  );
}
