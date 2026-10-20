// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The notice of the bar of the shell that tells the writes refused once what would tell their refusal
 * was no longer shown (#863): their screen left by « Précédent », by the router, or by a link
 * followed before the write left, or the list they were asked from read otherwise, nothing on the
 * screen tells the refusal any more, and the bar, which outlives every screen, does — nothing lost
 * unsaid. It says how many, until the person dismisses it.
 *
 * Each refusal is noted in the history of the messages (`message-history.ts`, #1043), once, in the
 * sentence a notice would have told it in, with the object in conflict it names and the screen the
 * write was made on: the bar says how many, the history what each was.
 *
 * The refusals are read from the store of the writes (`held-writes.ts`), outside React: they change
 * above the pages, and only this notice listens to them (défaut n° 18).
 */
"use client";

import { CircleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useSyncExternalStore } from "react";

import { useNoteRefusal } from "@/components/commands/outcome-notice";
import { noteMessage } from "@/components/notices/message-history";
import { Button } from "@/components/ui/button";
import {
  dismissLeftRefusals,
  type LeftRefusal,
  onLeftRefusals,
  refusedLeft,
} from "@/navigation/held-writes";

/** The identifier of the sentence of the notice, which its button is described by: one per bar. */
const TOLD = "shell-left-refusals";

/** No write refused: the same list each time it is read so. */
const NONE: readonly LeftRefusal[] = [];

/** None on the server: no write has left there. */
function noneOnTheServer(): readonly LeftRefusal[] {
  return NONE;
}

/** Tell the writes refused once no longer shown, if any, each noted in the history. */
export function LeftRefusals() {
  const t = useTranslations("outcome");
  const refused = useSyncExternalStore(onLeftRefusals, refusedLeft, noneOnTheServer);
  const noteRefusal = useNoteRefusal();
  const one = t("leftRefused", { count: 1 });
  useEffect(() => {
    for (const each of refused) {
      if (each.refusal === undefined) {
        // A write that answered no outcome: the bar's own sentence, for one write.
        noteMessage(each, { tone: "refusal", sentence: one, screen: each.screen });
      } else {
        noteRefusal(each.refusal, { screen: each.screen });
      }
    }
  }, [refused, noteRefusal, one]);
  const count = refused.length;
  if (count === 0) {
    return null;
  }
  return (
    <div
      role="alert"
      className="flex basis-full items-center gap-3 text-sm text-destructive sm:order-last"
    >
      <p id={TOLD} className="flex items-start gap-1.5">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        {t("leftRefused", { count })}
      </p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-describedby={TOLD}
        onClick={dismissLeftRefusals}
      >
        <X aria-hidden="true" />
        {t("dismiss")}
      </Button>
    </div>
  );
}
