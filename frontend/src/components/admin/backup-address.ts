// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of the backups reads of its address: its page alone (`offset`, as the contract
 * names it), which its pages turn (`ListPages`); the list has no sort, no search, no filter.
 *
 * Pure, and neither server nor client: the page reads, the pages write.
 */
import { OFFSET_PARAMETER, type PagedList } from "@/navigation/pages";

/** The list of the backups, which reads nothing of the address but its page. */
export const BACKUPS_LIST: PagedList = { page: OFFSET_PARAMETER, reads: [] };
