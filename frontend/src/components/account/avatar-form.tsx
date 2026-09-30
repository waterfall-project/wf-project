// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of the account, which the user puts, replaces or withdraws alone (WF-ADM-0080): a
 * PNG or JPEG image, the media types the contract declares — the field offers no other, and
 * says so of a file of another kind rather than send what the API would refuse —, and, when the
 * account has one, the offer to withdraw it. The API judges the size of the image; once it has
 * done what it was asked, the page is rendered again with the avatar the account now has.
 */
"use client";

import { Trash2, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { removeAvatar, replaceAvatar } from "@/api/actions/account";
import type { Outcome, Settled } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AVATAR_ACCEPT, isAvatarType } from "./avatar-types";
import { DoneNotice } from "@/components/notices/done-notice";
import { WAITING } from "./form";

/** Whether the account has an avatar to withdraw. */
export interface AvatarFormProps {
  readonly hasAvatar: boolean;
}

/** What the API did last: put the image, or withdraw it. */
type Done = "uploaded" | "removed";

/** Render the choice of an image, and the withdrawal of the avatar the account has. */
export function AvatarForm({ hasAvatar }: AvatarFormProps) {
  const t = useTranslations("account.avatar");
  const id = useId();
  const [file, setFile] = useState<File>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [done, setDone] = useState<Done>();
  const [pending, startTransition] = useTransition();
  const field = useRef<HTMLInputElement>(null);
  const wrongType = file !== undefined && !isAvatarType(file.type);
  const blocked = pending || file === undefined || wrongType;
  // Withdrawn, the avatar takes its button with it: the focus goes to the choice of an image.
  useEffect(() => {
    if (done === "removed") {
      field.current?.focus();
    }
  }, [done]);
  const run = (action: () => Promise<Settled>, success: Done, form?: HTMLFormElement) => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      const result = await action();
      setOutcome(result);
      setDone(result.kind === "done" ? success : undefined);
      if (result.kind === "done") {
        form?.reset();
        setFile(undefined);
      }
    });
  };
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (blocked) {
      return;
    }
    const data = new FormData();
    data.set("avatar", file);
    run(() => replaceAvatar(data), "uploaded", event.currentTarget);
  };
  return (
    <form aria-busy={pending} onSubmit={submit} className="grid gap-4">
      {/* Held while an image is sent: one chosen meanwhile would be lost unsaid. */}
      <fieldset disabled={pending} className="grid max-w-sm gap-2">
        <Label htmlFor={`${id}-file`}>{t("file")}</Label>
        <Input
          ref={field}
          id={`${id}-file`}
          name="avatar"
          type="file"
          accept={AVATAR_ACCEPT}
          aria-invalid={wrongType ? true : undefined}
          aria-describedby={wrongType ? `${id}-type` : undefined}
          onChange={(event) => {
            setFile(event.target.files?.[0]);
          }}
          className="h-auto py-1.5"
        />
        {wrongType ? (
          <p id={`${id}-type`} role="alert" className="text-sm text-destructive">
            {t("wrongType")}
          </p>
        ) : null}
      </fieldset>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <DoneNotice title={done === undefined ? undefined : t(done)} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" aria-disabled={blocked} className={WAITING}>
          <Upload aria-hidden="true" />
          {t("upload")}
        </Button>
        {hasAvatar ? (
          <Button
            type="button"
            variant="outline"
            aria-disabled={pending}
            className={WAITING}
            onClick={() => {
              run(removeAvatar, "removed");
            }}
          >
            <Trash2 aria-hidden="true" />
            {t("remove")}
          </Button>
        ) : null}
      </div>
    </form>
  );
}
