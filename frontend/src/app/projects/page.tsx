// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The former address of the list of projects, which is the home now (US-0210): it leads there,
 * on the server, so that a bookmark kept from before still finds the list.
 */
import { redirect } from "next/navigation";

import { HOME } from "@/navigation/home";

/** Lead to the home, the list of projects. */
export default function ProjectsPage(): never {
  redirect(HOME);
}
