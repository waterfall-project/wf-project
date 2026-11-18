// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rate update of the current revision (WF-REV-0060, C-362), a command of the revision at the
 * right of the title of the screen of the revisions (US-2370): the revision lists it
 * (`apply_rate_update`), and it is offered as the revision lists it — available, or unavailable and
 * naming the conditions it lacks in its tooltip (WF-IHM-0090). Pressed available, it opens a dialog,
 * which reads the proposal of the API when it opens (`readRateUpdateProposal`, never when the
 * screen renders) and presents it category by category — the previous rate, the proposed one and
 * where the latter comes from: the rate of the reference, or the previous rate projected by
 * inflation —, each category kept or refused by a box, before it applies the categories kept.
 *
 * A revision marked keeps the rates and the amounts it calculated (WF-REF-0130): the server refuses
 * the rest (409). The revision is sent in the version the screen read, and the screen is read again
 * once the update is applied, so that the amounts of its lines and of its totals follow. What the
 * update told stays under the command once the dialog has closed. While the update is on its way,
 * the dialog stays: neither Escape nor « Annuler » closes it, so that a refusal is told in it.
 */
"use client";

import { RefreshCw, X } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type RefObject,
  type SubmitEvent,
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";

import { applyRateUpdate, readRateUpdateProposal } from "@/api/actions/revisions";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { PressRefusal, useUnmet } from "@/components/commands/command";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { useHeldCommand } from "@/components/commands/held";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import { type CommandOffer, UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice, useReadAnew } from "@/components/commands/outcome-notice";
import { Amount } from "@/components/amount";
import { DoneNotice } from "@/components/notices/done-notice";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TableCell, TableRow } from "@/components/ui/table";

/** The rate update the API proposes for a revision. */
type Proposal = components["schemas"]["RateUpdateProposal"];

/** The revision the update applies to, the version read, and what the revision lists of it. */
export interface ApplyRateUpdateProps {
  readonly projectId: string;
  readonly revisionId: string;
  readonly lockVersion: number;
  /** What the revision lists of `apply_rate_update`: available, or the conditions it lacks. */
  readonly offer: CommandOffer;
  /** How the screen names the revision, which a refusal and the history of the messages cite. */
  readonly name: string;
}

const AMOUNT = `${CELL} tabular-nums`;

/** The proposal as the dialog presents it, each category with the box that keeps or refuses it. */
function ProposalTable({
  proposal,
  refused,
  onToggle,
}: {
  readonly proposal: Proposal;
  readonly refused: ReadonlySet<string>;
  readonly onToggle: (categoryId: string, retained: boolean) => void;
}) {
  const t = useTranslations("revisionScreen.rateUpdate");
  const source = useTranslations("enums.RateUpdateProposal.categories.source");
  const { categories } = proposal;
  if (categories.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("none")}</p>;
  }
  return (
    <div className="space-y-2">
      <div className="space-y-1 text-sm text-muted-foreground">
        {proposal.target_year === undefined ? null : (
          <p>{t("year", { year: proposal.target_year.toString() })}</p>
        )}
        <p>{t("notImposed")}</p>
      </div>
      <ListTable
        label={t("title")}
        columns={[t("retained"), t("category"), t("previous"), t("proposed"), t("source")]}
      >
        {categories.map((category) => (
          <TableRow key={category.cost_category_id}>
            <TableCell className={CELL}>
              <input
                type="checkbox"
                aria-label={category.label}
                checked={!refused.has(category.cost_category_id)}
                onChange={(event) => {
                  onToggle(category.cost_category_id, event.target.checked);
                }}
              />
            </TableCell>
            <TableCell className={CELL}>{category.label}</TableCell>
            <TableCell className={AMOUNT}>
              <Amount value={category.previous_amount} />
            </TableCell>
            <TableCell className={AMOUNT}>
              <Amount value={category.proposed_amount} />
            </TableCell>
            <TableCell className={CELL}>{source(category.source)}</TableCell>
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/** What the dialog shows of the read of the proposal: its wait, the proposal, or why it is not read. */
function ProposalBody({
  proposal,
  refused,
  name,
  revisionId,
  onToggle,
  onUnread,
}: {
  readonly proposal: Outcome<Proposal> | undefined;
  readonly refused: ReadonlySet<string>;
  readonly name: string;
  readonly revisionId: string;
  readonly onToggle: (categoryId: string, retained: boolean) => void;
  /** The proposal could not be read and the refusal is dismissed: nothing is left to do here. */
  readonly onUnread: () => void;
}) {
  const t = useTranslations("revisionCommands.rateUpdate");
  return (
    <div aria-busy={proposal === undefined}>
      {proposal === undefined ? <p role="status">{t("reading")}</p> : null}
      {proposal?.kind === "done" ? (
        <ProposalTable proposal={proposal.data} refused={refused} onToggle={onToggle} />
      ) : null}
      {proposal !== undefined && proposal.kind !== "done" ? (
        <OutcomeNotice
          outcome={proposal}
          names={{ [revisionId]: name }}
          subject={name}
          onClear={onUnread}
        />
      ) : null}
    </div>
  );
}

/** The dialog of the update: it reads the proposal when it mounts, and applies the categories kept. */
function RateUpdateDialog({
  projectId,
  revisionId,
  lockVersion,
  name,
  onClose,
  onClosed,
  onApplied,
}: Omit<ApplyRateUpdateProps, "offer"> & {
  readonly onClose: () => void;
  /** Give the focus back to the command, once the dialog has closed. */
  readonly onClosed: () => void;
  /** Said under the command once the update is applied: how many categories it updated. */
  readonly onApplied: (count: number) => void;
}) {
  const t = useTranslations("revisionCommands.rateUpdate");
  const common = useTranslations("revisionCommands");
  const held = useHeldCommand();
  const description = useId();
  const [proposal, setProposal] = useState<Outcome<Proposal>>();
  const [refused, setRefused] = useState<ReadonlySet<string>>(new Set());
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [busy, startTransition] = useTransition();
  // An update lost once sent: the dialog waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  const waiting = busy || reading;
  // The dialog is mounted once per revision and unmounted when it closes: the command that opens it
  // is keyed by the revision (`object-commands.tsx`), so both values are constant for the life of
  // this component and the read starts once; `current` drops the answer of a read that outlives it.
  useEffect(() => {
    let current = true;
    void readRateUpdateProposal(projectId, revisionId).then((read) => {
      if (current) {
        setProposal(read);
      }
    });
    return () => {
      current = false;
    };
  }, [projectId, revisionId]);
  const proposed = proposal?.kind === "done" ? proposal.data : undefined;
  const retained = (proposed?.categories ?? []).filter(
    ({ cost_category_id: id }) => !refused.has(id),
  );
  const presented = proposed !== undefined && proposed.categories.length > 0;

  const confirm = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (waiting || retained.length === 0) {
      return;
    }
    setOutcome(undefined);
    // In a transition, as the dialogs that write are: the request runs while Escape is still held.
    // A refusal is set in a nested transition, committed with the end of the request; the end of an
    // application — `onApplied`, `onClose` — runs after the answer, outside it.
    startTransition(async () => {
      const answer = await held(
        applyRateUpdate(projectId, revisionId, {
          categoryIds: retained.map(({ cost_category_id: id }) => id),
          lockVersion,
        }),
      );
      if (answer.kind === "done") {
        onApplied(retained.length);
        onClose();
      } else {
        startTransition(() => {
          setOutcome(answer);
        });
      }
    });
  };

  return (
    <Dialog
      open
      onOpenChange={(opened) => {
        // Nothing closes the dialog while the update is on its way.
        if (!opened && !waiting) {
          onClose();
        }
      }}
    >
      <DialogContent
        className="max-w-2xl"
        aria-busy={waiting}
        aria-describedby={description}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("label")}</DialogTitle>
          <DialogDescription id={description}>{t("statement")}</DialogDescription>
        </DialogHeader>
        <form aria-label={t("label")} noValidate onSubmit={confirm} className="grid gap-3">
          <ProposalBody
            proposal={proposal}
            refused={refused}
            name={name}
            revisionId={revisionId}
            onToggle={(id, kept) => {
              const next = new Set(refused);
              if (kept) {
                next.delete(id);
              } else {
                next.add(id);
              }
              setRefused(next);
            }}
            onUnread={onClose}
          />
          {presented && retained.length === 0 ? (
            <p role="alert" className="text-sm text-destructive">
              {t("noneRetained")}
            </p>
          ) : null}
          <OutcomeNotice
            outcome={outcome}
            names={{ [revisionId]: name }}
            subject={name}
            reading={reading}
            onClear={() => {
              setOutcome(undefined);
            }}
            onDismissed={onClose}
          />
          <DialogFooter>
            <Button type="button" variant="outline" disabled={waiting} onClick={onClose}>
              <X aria-hidden="true" />
              {common("cancel")}
            </Button>
            {presented ? (
              <Button
                type="submit"
                aria-busy={waiting}
                aria-disabled={waiting || retained.length === 0 ? true : undefined}
              >
                <RefreshCw aria-hidden="true" />
                {t("submit")}
              </Button>
            ) : null}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * The button of the command, available: it opens the dialog. Unavailable, the command is the plain
 * one, which names in its tooltip the conditions it lacks and says them when it is pressed.
 */
function Opener({
  offer,
  open,
  onOpen,
  button,
}: {
  readonly offer: CommandOffer;
  readonly open: boolean;
  readonly onOpen: () => void;
  readonly button: RefObject<HTMLButtonElement | null>;
}) {
  const t = useTranslations("revisionCommands.rateUpdate");
  const helps = useTranslations("commands");
  const unmet = useUnmet();
  const [presses, setPresses] = useState(0);
  return (
    <>
      <CommandTooltip
        label={t("label")}
        help={helps("updateRates.help")}
        unavailable={offer.is_available ? undefined : unmet(offer)}
      >
        <Button
          ref={button}
          type="button"
          variant="outline"
          size="sm"
          aria-haspopup="dialog"
          aria-expanded={open}
          className={UNAVAILABLE}
          onClick={() => {
            if (offer.is_available) {
              onOpen();
            } else {
              setPresses((count) => count + 1);
            }
          }}
        >
          {commandIcon(REVISION_COMMAND_ICONS.apply_rate_update)}
          {t("label")}
        </Button>
      </CommandTooltip>
      <PressRefusal offer={offer} presses={presses} />
    </>
  );
}

/** Offer the rate update of the current revision, as the revision lists it, in a dialog. */
export function ApplyRateUpdateCommand({
  projectId,
  revisionId,
  lockVersion,
  offer,
  name,
}: ApplyRateUpdateProps) {
  const t = useTranslations("revisionCommands.rateUpdate");
  const [open, setOpen] = useState(false);
  // What was told is kept as it was told: the page read again may change what it would say.
  const [applied, setApplied] = useState<{ readonly count: number }>();
  const button = useRef<HTMLButtonElement>(null);
  return (
    <div className="space-y-1">
      <Opener
        offer={offer}
        open={open && offer.is_available}
        button={button}
        onOpen={() => {
          setApplied(undefined);
          setOpen(true);
        }}
      />
      {open && offer.is_available ? (
        <RateUpdateDialog
          projectId={projectId}
          revisionId={revisionId}
          lockVersion={lockVersion}
          name={name}
          onClose={() => {
            setOpen(false);
          }}
          onClosed={() => {
            button.current?.focus();
          }}
          onApplied={(count) => {
            setApplied({ count });
          }}
        />
      ) : null}
      <DoneNotice
        subject={name}
        title={applied === undefined ? undefined : t("done", { count: applied.count })}
        of={applied}
      />
    </div>
  );
}
