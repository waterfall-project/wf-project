// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The named timelines of a project, each a link to it, and their commands (FBS-4.3.1, WF-PLA-0140,
 * EP-14/L44c): a timeline created by its name, in a dialog — the form of the reference data
 * (`ReferenceForm`), the name required, no longer than the contract takes, a refusal of its field said
 * at it —; the timeline shown deleted once confirmed, its inscriptions with it, the tasks keeping
 * their dates — nothing refuses it but a terminal project (WF-DAT-0080). They follow the command
 * `manage_timelines` the project lists: absent, nothing is offered; unavailable, presented
 * `aria-disabled`, described by the conditions it lacks.
 *
 * What a write did is said in a region of its own; a refusal answered once its dialog is gone, and a
 * refusal of a deletion, above the timelines (`Reactivations`). A creation adds no link: the page read
 * anew lists the timeline where the server keeps it. A deletion answered takes its link away, for as
 * long as the screen stays — against the fake back, which keeps nothing (`MockupNotice`) —, and the
 * timeline shown deleted, the screen shows the first one the project keeps, as the page does when its
 * address names none it has; an answer that arrives once the screen is left, or another timeline
 * shown, moves nothing (défaut n° 1 de `typescript.md`). The body of the screen, which the server
 * draws for the timeline shown, gives way with it (`TimelineBody`): to nothing while the first one
 * left is read, to the saying that the project has none once the last is deleted. Neither writes
 * from a version: no command waits for an answer, and an answer closes only the dialog it was sent
 * from (#660, #672).
 */
"use client";

import { Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { createTimeline, deleteTimeline } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import { UnmetConditions } from "@/components/commands/command";
import { useHeldCommand } from "@/components/commands/held";
import { type CommandOffer, UNAVAILABLE, unmetId } from "@/components/commands/offer";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { ReferenceForm, required } from "@/components/reference/reference-form";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** A named timeline of a project. */
type Timeline = components["schemas"]["Timeline"];

/** The longest name of a timeline the contract takes. */
const LABEL_LENGTH = 200;

/** A dialog open — the creation, or the deletion of a timeline —, and what opened it. */
interface Opened {
  readonly deleting: Timeline | undefined;
  readonly trigger: HTMLElement;
  /** The how-many-th opening it is: what an answer closes, never a later one. */
  readonly opening: number;
}

/** The timelines deleted while the screen stays, and how to delete one more. */
interface Deletions {
  readonly deleted: ReadonlySet<string>;
  readonly drop: (timeline: string) => void;
}

/** The timelines deleted, which the links and the body of the screen both follow. */
const DeletionsContext = createContext<Deletions | undefined>(undefined);

/** The timelines deleted while the screen stays, within `TimelineDeletions` only. */
function useDeletions(): Deletions {
  const deletions = useContext(DeletionsContext);
  if (deletions === undefined) {
    throw new Error("the timelines are deleted within TimelineDeletions only");
  }
  return deletions;
}

/**
 * Hold the timelines deleted while the screen stays, for the links (`TimelineChoice`) and the body
 * (`TimelineBody`) it holds, which the header of the screen sets apart.
 */
export function TimelineDeletions({ children }: { readonly children: ReactNode }) {
  const [deleted, setDeleted] = useState<ReadonlySet<string>>(() => new Set());
  const value = useMemo(
    () => ({
      deleted,
      drop: (timeline: string) => {
        setDeleted((before) => new Set(before).add(timeline));
      },
    }),
    [deleted],
  );
  return <DeletionsContext value={value}>{children}</DeletionsContext>;
}

/**
 * Render the body of the screen the server drew for the timeline shown (`children`), as long as it
 * stands: nothing once it is deleted, while the page leads to the first one left; the saying that the
 * project has none once none is left — or none ever was.
 */
export function TimelineBody({
  timelines,
  shown,
  children,
}: {
  readonly timelines: readonly Timeline[];
  /** The timeline the body was drawn for; none when the project has none. */
  readonly shown: string | undefined;
  readonly children: ReactNode;
}) {
  const t = useTranslations("timelines");
  const { deleted } = useDeletions();
  if (timelines.every((timeline) => deleted.has(timeline.timeline_id))) {
    return <p className="text-sm text-muted-foreground">{t("none")}</p>;
  }
  return shown !== undefined && deleted.has(shown) ? null : children;
}

/** What the timelines of a project offer, and to which address each leads. */
export interface TimelineChoiceProps {
  readonly project: string;
  /** The command `manage_timelines` the project lists: absent, nothing is offered. */
  readonly offer: CommandOffer | undefined;
  readonly timelines: readonly Timeline[];
  /** The timeline the screen shows; none when the project has none. */
  readonly shown: string | undefined;
  /** The address of each timeline, by its identifier. */
  readonly hrefs: Readonly<Record<string, string>>;
}

/** Render the timelines of a project, each a link, and their commands; within the region of refusals. */
export function TimelineChoice(props: TimelineChoiceProps) {
  return (
    <Reactivations reads={[]}>
      <Choice {...props} />
    </Reactivations>
  );
}

/** The links, the commands, the region that says what a write did, and the dialog open. */
function Choice({ project, offer, timelines, shown, hrefs }: TimelineChoiceProps) {
  const t = useTranslations("timelines");
  const form = useTranslations("reference.form");
  const router = useRouter();
  const list = useListReport();
  // The list, which tells the refusal, holds the navigations while the deletion answers (#688).
  const own = useHeldCommand();
  const held = list?.held ?? own;
  const id = useId();
  const { deleted, drop } = useDeletions();
  const [said, setSaid] = useState<{ readonly text: string; readonly count: number }>();
  const [opened, setOpened] = useState<Opened>();
  // How many times a dialog was opened: what tells an opening from the next.
  const openings = useRef(0);
  const [pending, startTransition] = useTransition();
  const listed = useMemo(
    () => timelines.filter((timeline) => !deleted.has(timeline.timeline_id)),
    [timelines, deleted],
  );
  const current = listed.find((timeline) => timeline.timeline_id === shown);
  // What the screen shows now, read by an answer once it arrives, never by a render: set as what it
  // shows is committed, and no answer runs between a commit and its layout effects (défaut n° 2 de
  // `typescript.md`).
  const seen = useRef({ shown, listed, hrefs });
  useLayoutEffect(() => {
    seen.current = { shown, listed, hrefs };
  }, [shown, listed, hrefs]);
  // Whether the screen is still there, which a deletion answered leads from.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const unmet = offer === undefined ? undefined : unmetId(offer, id);
  const deleting = opened?.deleting;
  const say = (text: string) => {
    setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
  };
  const open = (deleting: Timeline | undefined, trigger: HTMLElement) => {
    if (offer?.is_available === true) {
      openings.current += 1;
      setOpened({ deleting, trigger, opening: openings.current });
    }
  };
  const close = (opening?: number) => {
    setOpened((now) => (opening === undefined || now?.opening === opening ? undefined : now));
  };
  const closed = (trigger: HTMLElement) => {
    if (trigger.isConnected) {
      trigger.focus();
    } else {
      list?.refocus();
    }
  };
  const confirm = (timeline: Timeline, opening: number) => {
    if (pending) {
      return;
    }
    const generation = list?.generation ?? 0;
    startTransition(async () => {
      const outcome = await held(deleteTimeline(project, timeline.timeline_id));
      if (outcome.kind === "done") {
        drop(timeline.timeline_id);
        say(t("deleted", { label: timeline.label }));
        // The timeline still shown deleted, the screen shows the first one the project keeps — what
        // the page shows when its address names none it has; left, or another timeline shown since,
        // the screen stays where it is.
        const now = seen.current;
        const first = now.listed.find((other) => other.timeline_id !== timeline.timeline_id);
        const href = first === undefined ? undefined : now.hrefs[first.timeline_id];
        if (mounted.current && now.shown === timeline.timeline_id && href !== undefined) {
          router.replace(href);
        }
      } else {
        list?.report({
          outcome,
          generation,
          names: {},
          target: `delete timeline ${timeline.timeline_id}`,
        });
      }
      close(opening);
    });
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      {listed.length === 0 ? null : (
        <nav aria-label={t("choice")} className="flex flex-wrap items-center gap-1 text-sm">
          {listed.map((timeline) => (
            <Link
              key={timeline.timeline_id}
              href={hrefs[timeline.timeline_id] ?? ""}
              aria-current={timeline === current ? "true" : undefined}
              className={buttonVariants({
                variant: timeline === current ? "default" : "outline",
                size: "sm",
              })}
            >
              {timeline.label}
            </Link>
          ))}
        </nav>
      )}
      {offer === undefined ? null : (
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-disabled={offer.is_available ? undefined : true}
            aria-describedby={unmet}
            className={UNAVAILABLE}
            onClick={(event: MouseEvent<HTMLElement>) => {
              open(undefined, event.currentTarget);
            }}
          >
            <Plus aria-hidden="true" />
            {t("create")}
          </Button>
          {current === undefined ? null : (
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={t("deleteNamed", { label: current.label })}
              aria-disabled={offer.is_available ? undefined : true}
              aria-describedby={unmet}
              className={UNAVAILABLE}
              onClick={(event: MouseEvent<HTMLElement>) => {
                open(current, event.currentTarget);
              }}
            >
              <Trash2 aria-hidden="true" />
              {t("delete")}
            </Button>
          )}
          <UnmetConditions id={unmet} offer={offer} />
        </>
      )}
      {opened === undefined ? null : deleting === undefined ? (
        <ReferenceForm<Timeline>
          key={opened.opening}
          kind="timeline"
          title={t("create")}
          hint={t("formHint")}
          creating
          fields={[required("label", t("labelField"), LABEL_LENGTH)]}
          initial={{}}
          ask={({ label = "" }) => createTimeline(project, label)}
          target={undefined}
          answering={(answer) => answer}
          onDone={(timeline) => {
            say(t("created", { label: timeline.label }));
            close(opened.opening);
          }}
          onClose={() => {
            close();
          }}
          onClosed={() => {
            closed(opened.trigger);
          }}
        />
      ) : (
        <Dialog
          key={opened.opening}
          open
          onOpenChange={(still) => {
            if (!still) {
              close();
            }
          }}
        >
          <DialogContent
            aria-busy={pending}
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              closed(opened.trigger);
            }}
          >
            <DialogHeader>
              <DialogTitle>{t("deleteTitle", { label: deleting.label })}</DialogTitle>
              <DialogDescription>{t("deleteHint")}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  close();
                }}
              >
                {form("cancel")}
              </Button>
              <Button
                type="button"
                aria-busy={pending}
                onClick={() => {
                  confirm(deleting, opened.opening);
                }}
              >
                <Trash2 aria-hidden="true" />
                {pending ? form("sending") : t("delete")}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
