// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Home page. The home is the list of projects (EP-02, « Contexte de lecture, accueil et pages
 * système »): until US-0210/L1 (#112) makes that list the home page itself, the home leads to
 * it, on the server — the sign-in page, without a screen to come back to, lands there too.
 */
import { redirect } from "next/navigation";

// The list of projects, which the home stands for until it is the home itself.
const PROJECTS_ROUTE = "/projects";

/** Lead to the list of projects. */
export default function HomePage(): never {
  redirect(PROJECTS_ROUTE);
}
