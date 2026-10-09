// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The link of the screen of a function to the imports and exports of the project (FBS-4.3.4), in
 * the same context, where the import of its own file is exercised (#521): the estimate leads there
 * when the project lists the import of an estimate, the remaining to commit when it lists the
 * import of a remaining to commit, as the server lists it (`available_commands`) — available, or
 * unavailable, which the screen presents with the conditions it lacks (WF-IHM-0090), the guard of
 * that screen. One screen of the imports, with its report before it is applied (WF-INTF-0080): a
 * costing engineer who does not read the planning reaches it so. None when the import is not
 * listed: the caller may not exercise it.
 */
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { Project } from "@/components/context/reading";
import { LEAF_ICONS } from "@/components/shell/function-display";
import { buttonVariants } from "@/components/ui/button";
import type { ProjectContext } from "@/navigation/context";
import { functionHref, leafOf } from "@/navigation/functions";

import { listsImport } from "./offers";

type ExchangeKind = components["schemas"]["ExchangeKind"];

/** The imports and exports of the project, a leaf of the planning with a screen of its own. */
const EXCHANGES = leafOf("FBS-4.3.4");

/** The icon of the imports and exports, which their own screen shows too. */
const ExchangesIcon = LEAF_ICONS["FBS-4.3.4"];

/** What the link needs: the project read, the kind of file its screen imports, the context. */
export interface ExchangesLinkProps {
  readonly project: Project;
  readonly kind: ExchangeKind;
  readonly context: ProjectContext;
}

/** Render the link to the imports and exports, when the project lists the import of the kind. */
export function ExchangesLink({ project, kind, context }: ExchangesLinkProps) {
  const t = useTranslations();
  const href = functionHref(EXCHANGES, context);
  if (!listsImport(project, kind) || href === undefined) {
    return null;
  }
  return (
    <Link href={href} className={buttonVariants({ variant: "outline", size: "sm" })}>
      <ExchangesIcon aria-hidden="true" />
      {t(EXCHANGES.label)}
    </Link>
  );
}
