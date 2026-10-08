// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of a project, as the contract names it: its one declaration, which the actions of the
 * API, the navigation of the home and the screens read. A module of its own, a type alone: the
 * layer of the API depends on no screen nor on the navigation, and a browser loads nothing of it.
 */
import type { components } from "@/api/generated/schema";

/** The state of a project, as the contract names it. */
export type ProjectState = components["schemas"]["ProjectState"];
