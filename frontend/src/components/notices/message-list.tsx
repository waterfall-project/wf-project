// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The history of the messages of the session, as the panel of the tasks and the messages shows it
 * (#1043): the last first, each with whether it tells a success or a refusal — in words, never by
 * its colour alone —, its sentence, the object it was about, the reference of an unexpected error
 * (WF-OBS-0020), when it was told, and a link back to the screen it was told on, named as the
 * breadcrumb names it. Shown, every message is seen: none is unread any more.
 *
 * Not a live region: each message was announced when it was told, by its notice, and the history
 * says nothing twice.
 */
"use client";

import { CircleAlert, CircleCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useId, useSyncExternalStore } from "react";

import { LocalTime } from "@/components/local-time";
import { crumbsOf } from "@/navigation/breadcrumbs";
import { readContext } from "@/navigation/context";

import {
  markMessagesSeen,
  type Message,
  type MessageScreen,
  NO_MESSAGES,
  onMessages,
  readMessages,
} from "./message-history";

/** None on the server: the history is the browser's. */
function noneOnTheServer() {
  return NO_MESSAGES;
}

/** The history of the messages, rendered again only when it changes. */
export function useMessageHistory() {
  return useSyncExternalStore(onMessages, readMessages, noneOnTheServer);
}

/**
 * The name of a screen, as its breadcrumb ends — the function it shows, the page of the account,
 * the project —, with the project it showed; a screen the breadcrumb does not name is the screen of
 * origin.
 */
function useScreenName(): (screen: MessageScreen) => string {
  const t = useTranslations();
  return ({ href, project }) => {
    const url = new URL(href, "http://screen.invalid");
    const last = crumbsOf(url.pathname, readContext(url.pathname, url.searchParams), []).at(-1);
    if (last === undefined) {
      return t("messages.unknownScreen");
    }
    if (last.kind === "project") {
      return project ?? t("projectSwitcher.unnamed");
    }
    const name = t(last.label);
    return project === undefined ? name : t("messages.screenInProject", { screen: name, project });
  };
}

/** One message of the history. */
function Entry({
  message,
  screenName,
  onFollow,
}: {
  readonly message: Message;
  readonly screenName: string;
  readonly onFollow: () => void;
}) {
  const t = useTranslations("messages");
  const failure = useTranslations("failure");
  const refusal = message.tone === "refusal";
  const Icon = refusal ? CircleAlert : CircleCheck;
  return (
    <li className="space-y-0.5 border-b pb-2 text-sm last:border-b-0">
      <p className={`flex items-start gap-1.5 ${refusal ? "text-destructive" : ""}`}>
        <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span className="flex flex-wrap gap-x-1">
          <span className="font-medium">{t(message.tone)}</span>
          <span>{message.sentence}</span>
        </span>
      </p>
      {message.detail === undefined ? null : <p>{message.detail}</p>}
      {message.object === undefined ? null : <p>{t("object", { object: message.object })}</p>}
      {message.reference === undefined ? null : (
        <p>{failure("reference", { reference: message.reference })}</p>
      )}
      <p className="flex flex-wrap gap-x-2 text-muted-foreground">
        <LocalTime value={message.at} />
        <Link href={message.screen.href} onClick={onFollow} className="underline">
          {screenName}
        </Link>
      </p>
    </li>
  );
}

/**
 * The history of the messages, the last first; `onFollow` is called as a link back to a screen is
 * followed — the panel closes.
 */
export function MessageList({ onFollow }: { readonly onFollow: () => void }) {
  const t = useTranslations("messages");
  const heading = useId();
  const history = useMessageHistory();
  const screenName = useScreenName();
  // Shown, the messages are seen — those told while the panel is open too.
  useEffect(() => {
    markMessagesSeen();
  }, [history]);
  return (
    <section aria-labelledby={heading} className="space-y-2">
      <h3 id={heading} className="font-medium">
        {t("label")}
      </h3>
      {history.messages.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("none")}</p>
      ) : (
        <ol className="space-y-2">
          {history.messages.toReversed().map((message) => (
            <Entry
              key={message.id}
              message={message}
              screenName={screenName(message.screen)}
              onFollow={onFollow}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
