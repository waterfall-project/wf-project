// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The layout the filters of a table share (WF-IHM-0130, #2916): a regular grid of fields, each
 * with its label above (`FilterFields`), a discreet line of help under it, and, folded at the
 * bottom, the filters of audit — created by, modified by, and their dates (`AuditSection`). The
 * section is folded by default and its state is local: it is not kept, and a filter of audit that
 * is on shows by its chip. The grid wraps to the room it is given, never to a fixed count.
 */
"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useId, useState } from "react";

import { Button } from "@/components/ui/button";

/** The grid of the fields of a panel of filters, and its line of help. */
export function FilterFields({
  children,
  hint = true,
}: {
  readonly children: ReactNode;
  /** Whether the line of help stands under the fields. */
  readonly hint?: boolean;
}) {
  const t = useTranslations("grid.filtering");
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] items-start gap-x-4 gap-y-3">
        {children}
      </div>
      {hint ? <p className="text-xs text-muted-foreground">{t("hint")}</p> : null}
    </div>
  );
}

/** The filters of audit, in a section folded until opened, over the whole width of the grid. */
export function AuditSection({
  children,
  forced = false,
}: {
  readonly children: ReactNode;
  /** Whether the section is open whatever the user did: a filter of it refused by the server, to be said. */
  readonly forced?: boolean;
}) {
  const t = useTranslations("grid.filtering");
  const [opened, setOpened] = useState(false);
  const open = opened || forced;
  const id = useId();
  const Chevron = open ? ChevronUp : ChevronDown;
  return (
    <div className="col-span-full flex flex-col gap-3 border-t pt-2">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-expanded={open}
        aria-controls={id}
        className="h-7 justify-start self-start px-1 text-xs"
        onClick={() => {
          setOpened(!open);
        }}
      >
        <Chevron aria-hidden="true" />
        {t("audit")}
      </Button>
      <div
        id={id}
        hidden={!open}
        className="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] items-start gap-x-4 gap-y-3"
      >
        {children}
      </div>
    </div>
  );
}
