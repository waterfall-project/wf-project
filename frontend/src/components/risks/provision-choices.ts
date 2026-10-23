// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the form of a risk chooses its provision among (`provision-options.ts` reads it on the
 * server), and the rule that says which of the choices the form asks (WF-RIS-0010, EP-14/L42p,
 * #786): the category when the risk has more than one to choose — one alone is retained without
 * being asked —, the sub-project and the task when the project has any. Pure, and neither server nor
 * client: the page reads, the form asks.
 */

/** A choice of the form: what it writes, and what it says. */
export interface ProvisionChoice {
  readonly id: string;
  readonly label: string;
}

/** What the form of a risk chooses its provision among. */
export interface ProvisionOptions {
  /** The active categories of the type provision for risks. */
  readonly categories: readonly ProvisionChoice[];
  readonly subprojects: readonly ProvisionChoice[];
  /** The tasks of the main structure of the revision. */
  readonly tasks: readonly ProvisionChoice[];
}
