// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The notice of the bar of the shell that tells the writes refused once the screen that made them
 * was gone (#863): left by « Précédent », by the router, or by a link followed before the write
 * left, the screen cannot tell the refusal any more, and the bar, which outlives every screen,
 * does — nothing lost unsaid. It says how many, until the person dismisses it.
 *
 * The count is read from the store of the writes (`held-writes.ts`), outside React: it changes
 * above the pages, and only this notice listens to it (défaut n° 18).
 */
"use client";

import { CircleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { dismissLeftRefusals, leftRefusals, onLeftRefusals } from "@/navigation/held-writes";

/** The identifier of the sentence of the notice, which its button is described by: one per bar. */
const TOLD = "shell-left-refusals";

/** None on the server: no write has left there. */
function noneOnTheServer(): number {
  return 0;
}

/** Tell the writes refused once their screen was gone, if any. */
export function LeftRefusals() {
  const t = useTranslations("outcome");
  const count = useSyncExternalStore(onLeftRefusals, leftRefusals, noneOnTheServer);
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
