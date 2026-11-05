// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The mark of a task or a line a risk occurred merged (WF-RIS-0060, US-1020): a small icon after the
 * nature of the row, in the label, that names the risk — `Node.origin_risk_id`, which the server
 * renders on the nodes the occurrence merged and on no other. The names come from the risks the
 * project lists as occurred, which the screen hands the grid (`OriginRisksProvider`); a risk the
 * list does not hold is said without its name. A node without the field, or without a risk, bears
 * nothing.
 */
"use client";

import { Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useContext } from "react";

/** The labels of the risks occurred, by their identifier. */
type OriginNames = Readonly<Record<string, string>>;

/** The names of a grid that has none: one object, so that the value of the context stays put. */
const NO_NAMES: OriginNames = {};

const NAMES = createContext<OriginNames>(NO_NAMES);

/** Give the marks of the rows under it the labels of the risks occurred. */
export function OriginRisksProvider({
  names,
  children,
}: {
  readonly names: OriginNames | undefined;
  readonly children: ReactNode;
}) {
  return <NAMES.Provider value={names ?? NO_NAMES}>{children}</NAMES.Provider>;
}

/** The risk a node came of, when the grid read the field and the node bears one. */
function originOf(node: object): string | undefined {
  return "origin_risk_id" in node && typeof node.origin_risk_id === "string"
    ? node.origin_risk_id
    : undefined;
}

/** Render the mark of the risk a row came of, named for it; nothing for any other row. */
export function OriginMark({ node }: { readonly node: object }) {
  const t = useTranslations("originMark");
  const names = useContext(NAMES);
  const risk = originOf(node);
  if (risk === undefined) {
    return null;
  }
  const name = names[risk];
  const text = name === undefined ? t("unnamed") : t("named", { risk: name });
  return <Zap role="img" aria-label={text} className="size-3.5 shrink-0 text-muted-foreground" />;
}
