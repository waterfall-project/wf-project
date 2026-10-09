// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The refusal of the result of a background task, carried back to the screen the download left
 * from (#416). The result is handed on as a stream by a route of the front
 * (`app/tasks/[taskId]/result`), which the browser follows as a link: what the route refuses — the
 * API refusing the result, expired or not ready (409), the task unknown, the session lost, the API
 * out of reach — cannot be said by the route itself, the browser having left no screen to say it
 * in. The route sends the browser back to that screen, with the task and the refusal in its
 * address, which the tracker reads once the screen is loaded, tells by the entry of the task, and
 * takes away from the address.
 *
 * Pure, and neither server nor client: the route writes the address, the tracker reads it.
 */
import type { ErrorCode, Outcome } from "@/api/problem";
import { kindOf } from "@/api/problem-kind";
import { CATALOGUES } from "@/i18n/catalogues";
import { FALLBACK_LOCALE } from "@/i18n/locale";
import type { SearchParameters } from "@/navigation/context";
import { returnTarget } from "@/navigation/login";

/** The parameter of the address that names the task whose result was refused. */
export const REFUSED_TASK = "refused_task";

/** The parameter that says the refusal: `<status>:<code>`, or `unreachable`. */
export const REFUSAL = "refusal";

/** The parameter of the address of the result that names the screen it leaves from. */
export const FROM = "from";

/** What a refusal of the result says. */
export type ResultRefusal = Exclude<Outcome<never>, { kind: "done" }>;

/** The address of the result of a task, which leaves from the screen given. */
export function resultHref(taskId: string, from: string): string {
  const query = new URLSearchParams({ [FROM]: from });
  return `/tasks/${encodeURIComponent(taskId)}/result?${query.toString()}`;
}

/**
 * The address of the screen the download left from — a path of the front, the home otherwise —,
 * with the object whose download was refused, under its parameter — the task of a result by
 * default, `refused_backup` for a backup (`backup-address.ts`) —, and the refusal.
 */
export function refusedHref(
  from: string | null,
  id: string,
  refusal: ResultRefusal,
  parameter = REFUSED_TASK,
): string {
  const target = new URL(returnTarget(from), "http://front.invalid");
  target.searchParams.set(parameter, id);
  target.searchParams.set(
    REFUSAL,
    refusal.kind === "unreachable"
      ? "unreachable"
      : `${String(refusal.problem.status)}:${refusal.problem.code}`,
  );
  return `${target.pathname}${target.search}`;
}

/**
 * The refusal an address carries, and the object it is about, under its parameter; none when it
 * carries none it can stand for. A code the catalogue does not know is the unexpected error, as the
 * decoder makes it.
 */
export function readRefusal(
  search: SearchParameters,
  parameter = REFUSED_TASK,
): { readonly id: string; readonly refusal: ResultRefusal } | undefined {
  const id = search.get(parameter);
  const said = search.get(REFUSAL);
  if (id === null || !/^[\w-]+$/.test(id) || said === null) {
    return undefined;
  }
  if (said === "unreachable") {
    return { id, refusal: { kind: "unreachable" } };
  }
  const [, status = "", code = ""] = /^(\d{3}):([A-Z_]+)$/.exec(said) ?? [];
  if (status === "") {
    return undefined;
  }
  const known = Object.hasOwn(CATALOGUES[FALLBACK_LOCALE].errors, code);
  const problem = {
    code: known ? (code as ErrorCode) : "INTERNAL_ERROR",
    status: Number(status),
  } as const;
  return { id, refusal: { kind: kindOf(problem.status), problem, conflictingObjectId: null } };
}

/** The address without the refusal it carried, and the object named under its parameter. */
export function withoutRefusal(
  location: { readonly pathname: string; readonly search: string },
  parameter = REFUSED_TASK,
): string {
  const search = new URLSearchParams(location.search);
  search.delete(parameter);
  search.delete(REFUSAL);
  const text = search.toString();
  return text === "" ? location.pathname : `${location.pathname}?${text}`;
}
