# Development guide

> This is the English version of [README-fr.md](README-fr.md); when the two differ, the French text
> is the reference.

This guide fixes what must look alike from one lot to the next, whether a person or an agent
wrote it: where each thing lives, how it is named, and the shape of the pieces that repeat. It
copies neither the specification (`docs/spec`), nor the contract (`docs/api`), nor
[CONTRIBUTING](../../CONTRIBUTING.md), nor the [roadmap](../roadmap/README.md): it refers to them.

Every rule a tool can check is checked, and the rule names its check; a rule that nothing checks
says so. The guide is written at the same time as the foundation (EP-01): each story adds the
section it establishes, and a section still empty names the one that will write it.

## Tree

| Path                                       | Contents                                                                                                                                                                                                      | PBS     |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `backend/`                                 | a single Python project, a single package `waterfall`: the core (`core/`, one sub-package per module, modelled on an FBS block), the API service (`api/`), the worker (`worker/`); the tests in `backend/tests/` | PBS-2   |
| `frontend/`                                | the Next.js application; the generated client in `frontend/src/api/`; the end-to-end paths in `frontend/e2e/`                                                                                                 | PBS-1   |
| `fixtures/`                                | the generated report of the numeric examples of the Vérif, and the fixtures attached to it                                                                                                                    | —       |
| `tools/`                                   | the repository tools, a single Python package, `wftools`, and their tests                                                                                                                                     | PBS-5.2 |
| `deploy/compose/`, `deploy/helm/`          | the packaging: Compose, then the Helm chart in EP-13                                                                                                                                                          | PBS-5.1 |
| `deploy/keycloak/`                         | the Keycloak image: the Java extension (`extension/`), the themes, the `waterfall` realm (`realm/`), and what the development platform adds to it (`development/`)                                            | PBS-5.4 |
| `.github/workflows/`                       | the chain                                                                                                                                                                                                     | PBS-5.2 |
| `docs/spec/`, `docs/api/`, `docs/roadmap/` | the specification, the contract, the roadmap                                                                                                                                                                  | —       |
| `docs/dev/`                                | this guide, and the coding rules per language                                                                                                                                                                 | —       |
| `LICENSES/`, `REUSE.toml`                  | the texts of the licences, and the licence of the files that carry no header                                                                                                                                  | —       |
| `docs/legal/`                              | the contribution licence agreement, and the commitments towards the community edition                                                                                                                         | —       |

A directory is born with the lot that puts the first file in it: `backend/`, `frontend/`,
`fixtures/` and `deploy/` do not all exist yet. The design of EP-01 says why each thing is
there (`docs/roadmap/EP-01-socle-de-developpement.md`, « Conception »).

## The back and the boundaries of the core

The back is a single package, `waterfall`, and two processes: `waterfall-api` and
`waterfall-worker`, two entry points of one distribution. They therefore carry the same
version by construction, that of `backend/pyproject.toml` (WF-ARC-0010).
A third command of the same distribution, `waterfall-migrate`, applies the migrations of the
database (see « Migrations ») and stops: it is not a process of the service, but it carries
the same version and is launched with the same image.
A fourth, `waterfall-restore`, is the restore service (US-0440, #953): the only reader of the
stream of restores, the only one to hold the owners of the two databases, it applies the
migrations like the bootstrap, and its module, `waterfall.restore`, is like it at the top of the
layers, imported by none.

The core, `waterfall.core`, has one sub-package per module, named after its second-level FBS
block, in English. A module exposes what the others may use in its `interface` module, and
nothing else: its tables and its data access are private to it.
A module imports another through `waterfall.core.<module>.interface`, never through its
tables. The core imports neither the API nor the worker, which do not import each other.

What is not a business function — settings and secrets, logs, correlation, typed exceptions
— lives in `waterfall.platform`, below the core: the core, the API and the worker import it,
it imports none of them, and none of its modules knows a table of the core. The layer contract
of `backend/pyproject.toml` guards it.

_Check_: `make imports-back` (import-linter, contracts in `backend/pyproject.toml`); a test
exercises them on a trial package (`backend/tests/test_boundaries.py`). An SQL query written
as text, which would name the table of another module, escapes the analysis of the imports:
it falls under the SQL rules of EP-03 and under review.

**Background tasks** (WF-ARC-0090). A task lives in the `background_task` table
(`waterfall.platform.tasks`), which is authoritative; the Redis stream (`waterfall.platform.queue`)
carries only its identifier. A route submits it by `submit(session, queue, genre, demandeur)`, in
its transaction, under the correlation of the request: the deposit in the stream follows the
commit, and a task whose deposit was lost stays `queued`, which the worker re-deposits at start-up
and then periodically. The worker (`waterfall.worker.runner`) runs the task in a single transaction,
under an advisory lock of its own, through the handler of its kind — a function
`(session, tâche)` that `handlers(réglages)` (`waterfall.worker.main`) registers, and which refuses
by a typed exception of the core, whose code becomes the reason of the failure. Stopped during a
task, it leaves nothing of its work: another takes it up from the start, and it fails after three
attempts; a task of a kind that no handler runs fails without running. A restore (`restore`) is
never the worker's: `startRestore` deposits it in a second stream, `waterfall:tasks:restores`,
which the restore service alone reads, in its consumer group; it sets the maintenance, a Redis key
beside the worker's stream that the API reads (503 except the liveness probe), and the worker runs
nothing while it is there (EP-03, « Sauvegarde et
restauration »). Scheduled
tasks are deposited by `waterfall-worker enqueue <genre>`, which deposits none when a task of the
same kind is queued or running: the `scheduler` service of Compose calls it at the interval of
`WATERFALL_IDENTITY_SYNC_INTERVAL`, in seconds, one day by default.
Whoever opens the queue says how long it waits for Redis: a request or the scheduler
`TaskQueue.connect(adresse, timeout=DEPOSIT_TIMEOUT)`, one second, so that a mute Redis does not
hold back the response; the worker `WORKER_TIMEOUT`, longer than each of its reads. An error the
worker does not expect — Redis or PostgreSQL out of reach — stops it in failure (1), said in its
logs by `worker.failed`, secrets masked.

Every served operation the contract keeps declares, on its route, the permissions it requires:
`dependencies=[Depends(Requires(...))]` (`waterfall.api.evaluation`), evaluated before the
validation of the parameters and of the body, after it is read: an unreadable body is refused
first (400). The permission to view comes first — without it, the object does not exist for the
caller, 404 `NOT_FOUND`; without another, 403 `PERMISSION_MISSING`, `params.missing_permission`
naming it (WF-ADM-0110). The evaluation itself, `require(actor, permission)`, is that of the module
`waterfall.core.access_roles`, which the following epics complete (the status of contributor in
EP-04). _Check_: `backend/tests/test_access_evaluation.py` lists the permissions of every served
operation and checks that the contract declares the refusal they can give — a new route is added
to it.

## The front

### The tooling: Next, pnpm and Vitest

The front is a Next.js application in strict TypeScript (`frontend/tsconfig.json`, with
`noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`). pnpm manages its dependencies,
at the version `packageManager` names in `package.json`, launched by corepack
(`corepack enable pnpm`); the lock, `pnpm-lock.yaml`, is authoritative and the chain installs
with `--frozen-lockfile`. The unit tests are `*.test.ts` or `*.test.tsx` files next to the code
they exercise, run by Vitest in two projects (`vitest.config.ts`), which the file name decides
between: `node` for the `*.test.ts` and `*.test.tsx` — the logic, and the server components of
`src/app/`, which render without a document as in production —, `dom` for the `*.dom.test.ts`
and `*.dom.test.tsx` — the client components, which Testing Library renders in the document of
happy-dom. A `*.dom.test.tsx` may live under `src/app/` when it exercises what a page composes with
its client components: the page is read as in production, on the server, and the tree it renders
is mounted in a document, where only a render shows what the banner and the grid share
(`structure-screens.dom.test.tsx`). Such a test does not exercise the Vérif of a requirement and
cites none: it holds in non-regression defect no. 20 of `typescript.md` and #819.3, the same
screens having their paths under `e2e/`. A test of the `dom` project that writes to the error
output — `console.error`, `console.warn`, `console.trace` — fails once its document is cleaned up
(`frontend/src/test/stderr.ts`, called by `setup-dom.ts`): a warning from React or ECharts, a
response the fake back does not have, are defects of the test or of the code, not noise to read in
passing. A test that proves an error is said on the console silences it itself with a spy
(`vi.spyOn(console, "error")`), and checks what was said. happy-dom measures nothing: a test that
mounts a curve gives its drawing the room a page gives it (`roomForCharts`,
`frontend/src/test/chart-room.ts`), failing which ECharts warns that it has neither width nor
height (EP-02/L37).

### Navigation: the table of functions and its routes

The shell (`frontend/src/components/shell/`) draws its navigation from
`frontend/src/navigation/functions.json`: for each second-level function of the FBS, its code,
the key of its label, its route, its scope and the permission that lets it be viewed; a
function for which the session lacks the `<fonction>.read` permission does not appear in it.
The table also carries the leaves of the FBS, each addressed in one of two ways. A leaf that has
its own screen is a leaf (`leaves`) of its function, of the same scope and the same permission:
the mapping of the extraction of actual costs, FBS-3.1.3, under the cost settings
(`/reference/costs/actual-cost-mapping`, US-0620), the timelines, FBS-4.3.1, the imports and
exports, FBS-4.3.4, and the task tree, FBS-4.3.5, under the planning
(`/projects/[projectId]/revisions/[revisionId]/timelines`, `…/exchanges`, `…/task-tree`), the
workload plan of the project, FBS-4.4.4, under the estimate (`…/workload`), and the Kanban,
FBS-4.5.3, under the remaining to commit (`…/kanban`). The navigation shows it, indented under its
function, in a list nested in the element of that function, with the guard of the leaf and in the
same context; the screen of its function leads to it too. The platform menu renders the leaves of
its functions the same way, the current leaf marked `aria-current`. The current link,
`aria-current="page"`, is that of the leaf; its function, which is the path, carries
`aria-current="true"`. Folded to icons, the bar shows only the function, marked so when the page is
one of its leaves. `readContext` reads it as its function, and the breadcrumb places it after it,
including a leaf of scope `platform`, in its FBS block. A leaf
that the screen of its function shows itself, where the ergonomics put it, is a section
(`sections`) of its function, addressed by the route of that function: its `code`, the role of what
shows it (`role`: `region`, `grid`, `treegrid`, `columnheader` or `heading`) and the key of its name
(`name`) — the work breakdown, FBS-4.2.1, is the « Work breakdown » region of the project
settings; the Gantt, FBS-4.3.3, the « Gantt » column of the planning grid; the financial progress,
FBS-4.8.1, the title of its card. Only a fact of a named list does without a role — a term does
not take its name from what it says —: it is found by its text in the list the `within` key names,
like the inflation rate, FBS-4.2.2, in the « Project settings »;
`functions.test.ts` refuses any other section without a role.

_Check_: `make screens` (`wftools.screens`, family `repo`, which runs on every change, since it
reads the projection like the front) confronts the table with the functions of the FBS of the
projection — the boxes of the figures of the tree and of each block, which name them all, and the
titles of their paragraphs, read as a safeguard; an arrow whose child does not extend the code of
its parent makes the reading fail — and with the pages of `frontend/src/app`; it fails, naming the
leaf or the route, on a leaf without a route in the table, on a code of the table that is not a
function of the FBS or a leaf filed under another function than its own, on a route to which no
page answers — the page of `[...path]`, which says « not found », answers none —, and on a leaf
with its own screen that the page of its function does not name by `leafOf("FBS-…")`, and so
cannot lead to. A leaf that has no screen yet would be declared, with its reason and the issue
that follows it, in `WITHOUT_SCREEN` of `tools/src/wftools/screens.py`, empty today; the
declaration fails as soon as the table addresses the leaf. The path `frontend/e2e/screens.spec.ts`
(`make e2e`, full tier) proves the links in a browser, one path per route, drawn from the table: a
function is reached by a click on a link of the navigation — from the screen of another function
of its block, or of a revision for a function of a project —, a leaf with its own screen by a click
on a link of the screen of its function; the link must be visible, the route is compiled in
advance (`compile`), and a starting project screen opens hydrated (`openHydrated`). Each screen
reached names its function and shows its sections. A route added to the table therefore has its
path.
Three scopes: outside a project; `project`, the functions of the project itself — revisions,
settings, lifecycle —, under `/projects/[projectId]/…`,
which a project without a revision offers; `revision`, the others, under
`/projects/[projectId]/revisions/[revisionId]/…`. The reading context is in the address: the
project in the path, the revision in the path or, on a function of the project, as the
`revision_id` parameter; filtered subproject and calculation date as parameters, `subproject_id`
and `as_of`, as the contract names them. The links between functions of a project carry them
over, and a cookie of the front, `wf_last_project`, keeps the last one, from which the shell draws
the « Back to the project » (WF-IHM-0010); it leads back only to a project screen of the table,
function or leaf that has its screen. Each route
of the table has its page, which `frontend/src/app/[...path]/page.test.tsx` checks; any other
address leads, through `frontend/src/app/[...path]/page.tsx`, to the « not found » screen. The
account pages (`/account`, `/account/avatar`, `frontend/src/navigation/account.ts`)
have their screens (US-0320): the information of the account and its display preferences — the
language and the mode, the same fields the account menu writes, saved together — and the avatar.
No screen of Waterfall asks for, displays or changes a password: the identity provider holds them
(WF-ADM-0140), and the account screen leads a local account to its account page of the realm
(`realmAccountPage`, `src/session/settings.ts`), in another tab; an account of the directory or of
an external provider has no password there, nor does the fake realm back. It sends the language
only if it has changed: the API passes it on to the identity provider, and a change of the mode
alone does not wait for Keycloak (#877). The image of the avatar, served by the API alone, is read
by the Next server while rendering the page and written into the page as a `data:` address
(`avatar-source.ts`): neither a call from the browser to the API, nor a relay; the avatar screen
alone shows it, the account menu keeps the initials.

### The name of an account

The name of an account is displayed only through `useAccountNaming`
(`frontend/src/components/account/account-name.ts`): `person` for an account by its first name
and last name, `kept` for the name a response kept of it — the author and the object of an entry
of the log, the author of a transition, the audit columns of an object. The API renders the names
of an anonymised account as null, with no sentence in their place (WF-ADM-0060, WF-ARC-0110): a
null name is said by the neutral label of the catalogue (`accountName.anonymized`, « Anonymised
account »), never by a blank nor by the identifier of the account. In a cell, this label has a
single rendering, `AnonymizedName` (`KeptName` for a kept name that may be null, in
`anonymized-name.tsx`), greyed out and marked `data-anonymized`; an option of a `<select>`, which
carries only text, takes `kept(null)`.

### The shell: sidebar, top bar and account menu

The shell is composed thus (`shell.tsx`, layout of the visual identity): on the left the sidebar
(`navigation.tsx`), the logo and the choice of the project at the head, the functions in three
groups — the platform, by foldable FBS block; the project, with the list of projects and the
« Back to the project »; the revision read —, the button that folds it at the foot; above the
page, the bar (`top-bar.tsx`): the button that folds the sidebar, the breadcrumb
(`frontend/src/navigation/breadcrumbs.ts`), the search — in place, without a function yet —, the
button of the panel of tasks and messages and the account menu. The folded sidebar keeps its state in
a cookie of the front, `wf_sidebar_state`, which the root layout reads to render it so
server-side. The layout, rendered once, does not know the address: the label of the project comes
from the screen, which has already read it for its banner — `ContextBanner` hands it back to the
shell through `ShowProject` (`shown-project.tsx`), which names it only as long as the address shows
that same project. The account menu (`account-menu.tsx`) carries the display preferences —
language and mode, each a choice in a sub-menu, written to the account on selection, the keyboard
traversal sending nothing —, the account pages and the sign-out. The sign-out
(`closeMySessions`, which closes every session of the account; a 401 counting as a session already
closed, the deactivated or not admitted account included) forgets what the browser kept of the
session — the `wf_last_project` cookie, the tasks of the `wf_background_tasks` storage and of the
tracking, the message history (`wf_messages`) — then loads as a
whole document the address the action renders: `/login`, usually. `/login?next=…` is a route
handler (`src/app/login/route.ts`), not a page: Waterfall has neither a sign-in form, nor a list
of providers, nor a forgotten password, the identity provider holding its screens. On the fake
back (`WATERFALL_AUTH=mock`), which grants the session, it leads straight to the target screen
(`returnTarget(next)`, `frontend/src/navigation/login.ts`) — without one, or outside the front,
the home page —: the layout re-reads the session, and the tracking takes up the tasks a lost
session had interrupted. Outside this mode, it starts the authorisation code flow of the
`waterfall` realm (US-0350) — see « The session of the front » below. The session is `getMe`
(`src/session/request.ts`): the account flattened, its display preferences and its permissions. A
401 `ACCOUNT_DEACTIVATED` or `ACCOUNT_NOT_ADMITTED` is not an absent session: the screen says so
(the failure `failure.deactivated` or `failure.notAdmitted`, the refusal of an action), and does
not send back to the sign-in, which would loop (#664). Without an account (401), there is neither
account menu nor sidebar; when the session is unreadable, the sidebar is rendered with the status
screen alone, its block open, and without an account menu. The sidebar is a landmark (a named
`<aside>`); on a narrow screen, it is a modal sheet that closes as soon as the address changes;
Ctrl+B folds it only if it is rendered, and folding it gives the focus of what the rail hides to
the button of the block or to the trigger.

### The session of the front

**The session of the front** (US-0350, `frontend/src/session/`). The browser holds no token
(WF-ARC-0030): the Next server holds them in Redis, under an opaque identifier that the
`__Host-wf_session` cookie alone carries (`HttpOnly`, `Secure`, `Path=/`, without `Domain`,
`SameSite=Lax`, without expiry): its prefix prevents a neighbouring subdomain from setting one of
its own, which `/login` would read first (#887); the browser also takes it from `http://localhost`
or `http://127.0.0.1`, where the paths and the workstation run, like any `Secure` cookie.
`/login?next=…` draws a `state`, a nonce and a PKCE verifier (S256), keeps them in Redis with the
target screen — already passed through `returnTarget` — for fifteen minutes at most, gives the
browser a cookie bound to this `state` (`wf_sign_in_<state>`, limited to `/auth/callback`, fifteen
minutes), and sends it to the sign-in page of Keycloak. `/auth/callback` requires this cookie — a
return carried to another browser opens no session there and starts the sign-in again, without
touching the request (RFC 9700, §4.7) —, takes up the request by its `state`, once only, exchanges
the code, checks the nonce of the identity token, opens the session — its tokens in Redis for the
duration Keycloak gives its session, `refresh_expires_in` — and leads to the target screen, its
whole address; an unknown `state`, already used or too old, starts the sign-in again; a sign-in
the realm refuses — an error on return, a refused code, a wrong nonce — leads to the home page
without a session, never to `/login`, which the Keycloak session would loop. Keycloak or Redis
unreachable, or Keycloak mute beyond the timeout, `/login` and `/auth/callback` lead to
`/login/unavailable`, forgetting the `__Host-wf_session` cookie — the page would otherwise re-read
Redis for it —, which says the service is unreachable and offers to start again towards the target
screen, never a bare 500 error (#687). `/login` also clears the `__Host-wf_session` cookie: the
sign-out leads there without touching it (#724).
`serverClient()` is the only place that carries the token to the API (`src/session/tokens.ts`): on
each request, it reads the session from the cookie and refreshes an access token that expires in
less than thirty seconds, under a Redis lock per session that lives twice the timeout of a request
to the realm (`REFRESH_TIMEOUT`, five seconds), so that two requests never present the same
refresh token. A refresh that fails once sent — refused, no response within this timeout, the
connection cut during the response, a proxy answering in its place — closes the session: Keycloak
may have taken the token, which is never presented twice (#687). Only a request that could not
leave (Keycloak unreachable: connection refused, unknown host or out of reach, certificate
refused) does not close it: the access token serves as long as it lives, then the request is the
service unreachable (`Unreachable`), which the screen says as such. Redis unreachable during an
ordinary request is the same, a component of the platform out of reach (WF-EXP-0040):
`requestBearer` turns the `StoreUnreachable` of the store into `Unreachable`, and the screen says
the service is unreachable, never an unexpected error (#861). When the session the cookie names no
longer lives, the request does not leave (`SessionLost`): a read leads to the sign-in at once,
without a click — the failure screen loads `/login?next=<écran>` —, a write is not applied, and the
screen says so before leading there by a link (`decode`). Without a cookie, the request leaves
without a token, and a 401 from the API (`SignedOut`), like the refusal of a living token, offers
the sign-in by a link without leading there by itself: a refused sign-in comes back without a
cookie, and leading there would loop. On a 401 `SESSION_REVOKED` only — a token of a sign-in
earlier than the closing of the sessions of the account —, this link, the failure screen
(`failure.revoked`) as well as the notice of an action, leads to
`/login?next=…&reauthenticate=1`, which `/login` sends to the realm with `prompt=login`: Keycloak,
whose session may have survived a missed closing, asks for the credentials again and renews
`auth_time`; a `SESSION_EXPIRED` does not ask for them again (#855). The sign-out (`signOut`)
closes the sessions of the account by `closeMySessions`, then clears those the front keeps of
this account, without waiting for Keycloak — the administration API also closes the Keycloak
session of the browser, and `/login` asks for the credentials again. It does not touch the cookie:
a server action that changes a cookie makes the page render again in its response, which would
read the API without a session (#724); `/login` clears it. A not admitted account keeps a Keycloak
session the API does not close: the browser goes to the sign-out endpoint of the realm. The shell
offers it neither bar nor account menu: the failure `failure.notAdmitted` offers « Sign out », a
link to `/auth/sign-out`, which leads to the same endpoint (`signOutAddress`); the realm, without
an identity token, asks to confirm, then leads to `/login`, which asks for the credentials again
(#664). When the session the cookie names no longer lives,
the request does not leave, and the browser goes through a silent sign-in
(`/login?sign_out=<ticket>`, `prompt=none`). Only the `signOut` action arms it: a ticket drawn at
random, kept one minute in Redis and bound to the identifier the `__Host-wf_session` cookie of the
request carries, without touching the cookie (`armRequestSignOut`, `armSignOut`); `/login` takes
it, once only, only if the cookie of the browser carries that same identifier (`takeSignOut`). An
unknown ticket, already taken or too old — a link from another site, which a top-level navigation
sends with the `SameSite=Lax` cookie —, or bound to another cookie, or a browser without a cookie,
make an ordinary sign-in, which closes nothing and leaves the ticket: the identifier of the action
is public, and a third party who calls it from its server, with a cookie of its own, obtains a
ticket that signs out only that cookie. Its return closes the sessions of the account by
`closeMySessions`, with the token it obtained (`tokenClient`), on all its workstations, then leads
to `/login`; without a Keycloak session either, there is no workstation left to close (#689). A
token the API then refuses by `SESSION_REVOKED` — the Keycloak session survived a missed closing —
leads, like the refusal of `closeMySessions` by this code in `signOut`, to
`/login?…&reauthenticate=1`, which asks for the credentials again: never a new silent sign-in,
which would bring back the same refusal (#855). A click on a link of the front waits for the
writes of the page (`holdNavigation`, `useNavigationHold`): a committed cell, an applied paste, a
command — the button of a command (`Command`), of a list or of a form of the reference data, the
saving of the preferences, the sending or the removal of the avatar, the request of an export, the
retry of a task, the sending of a file to import, which all go through `useHeldCommand`
(`components/commands/held.ts`); one refused — the lost session included —, the navigation does
not take place, and the screen says the refusal where the write was made (#688). The hold belongs
to whoever says the refusal: a form or a row of a list of the reference data takes that of the
list (`held` of `useListReport`), which says above itself the refusal of a dialog closed during
the sending; closing the dialog therefore does not release its write. The list says a refusal only
on the reading from which it left: read otherwise — a search, a state filter —, it releases its
writes, whose refusal is no longer said by the list, nor on return to that reading, whose clicks
are no longer held — a reading left and then found again is another one
(`useHeldCommand(generation)`); still under way and refused afterwards, the notice of the bar says
them, like those of a screen left (below). Every refusal holds the click, even said elsewhere than
on the screen left: the retry of a refused task holds the navigation, although its refusal is said
in the tasks panel of the shell, which outlives the screen — a rule without exception rather than a
write to judge one by one. The click is
judged by its gesture, which begins when the pointer goes down or a key is pressed: it waits for
the writes still under way and for those that left since the start of the gesture, even already
answered — the cell committed when the pointer goes down on the link, whose lost session answers
before the click, holds that click. Only the last held click is redone; a screen left releases its
writes, which hold nothing of the next screen. Not held: a programmatic navigation
(`router.push`), « Back » and « Forward » of the browser, a link that opens elsewhere — another
tab, modifier key, download, another site. « Back » and « Forward » change the address at once,
but since Next 16.4 the router shows the entry found again only once the action under way has
answered (vercel/next.js#99612, entry of 16.4.0): `runAction`
(`next/dist/client/components/app-router-instance.js`) now applies the state of the traversal in
the transition that `traverse` opens, where 16.3 applied it a microtask later, outside it; and
React gives a transition requested during an asynchronous action the lane of that action
(`requestTransitionLane`, `currentEntangledLane` of `react-dom`), which commits only on its
response — here the write awaited in `startTransition(async …)`. The screen left therefore stays
displayed until the response, and a write refused while it is left for another path — made before
the traversal or after — goes to the bar, even when what requested it says it still says it
(`told`), since it goes away with the screen (`away` of `holdNavigation`, `useHeldWrites`); brought
back to its path before the refusal, the screen says it itself. This holds as long as the router
keeps this order, perhaps an upstream defect. A write still under way when
its screen goes away, and refused afterwards, is said by no screen: the bar of the shell, which
outlives each of them, says it by a notice one closes (`LeftRefusals`, `refusedLeft` of
`held-writes.ts`, #863), and records it in the message history with its refusal and the screen it
had left from; a write refused before its screen left was said there, and is not said twice.
Keycloak, for its part, notifies the closing of the sessions of an account — sign-out,
deactivation, withdrawal of roles — through the back channel, `/auth/backchannel-logout`, a route
of the front and not an operation of the API, which checks the logout token with the keys of the
realm and clears the Redis sessions of the account it names. Only `src/session/provider.ts`
(`openid-client`, `jose`) and `src/session/store.ts` (`@redis/client`) reach Keycloak and Redis,
each only its own
: ESLint refuses these libraries elsewhere, and each of the two modules those of the other
(`src/api/network-guard.test.ts`).

The front, outside the `mock` mode, reads: `WATERFALL_KEYCLOAK_ADDRESS`, the address of Keycloak
for the browser, under which the issuer of the tokens falls (`https://<hôte>/auth`);
`WATERFALL_KEYCLOAK_BACKCHANNEL`, the one through which the Next server reaches it, the same by
default; `WATERFALL_FRONT_ADDRESS`, the address of the front, under which the return address is;
`WATERFALL_FRONT_CLIENT_SECRET`, the secret of the `waterfall-front` client; `WATERFALL_REDIS_URL`,
the Redis of the sessions. A missing variable makes the first sign-in fail, naming it;
`next build` and the `mock` mode read none. `openid-client` refuses any address of Keycloak that
is not in HTTPS, that of the sign-in page included: on the service platform, Keycloak is served in
HTTPS by a front end with a local authority, which the front trusts through `NODE_EXTRA_CA_CERTS`
(« Commands », #680).

### The system pages: loading, failure and « not found »

The system pages are pieces of the shell (`frontend/src/app/`,
`frontend/src/components/system/`). A read a screen cannot do without goes through
`readOrFail` of `frontend/src/api/problem.ts`, which renders its data or throws: a 404 leads to
the single « not found » screen (`not-found.tsx`), which a non-existent address and a refused
read reach without distinction (WF-ADM-0110); the API unreachable throws `Unreachable`, and
any other response `UnexpectedAnswer`. A read a screen can do without goes through
`readUnlessRefused`, next to it: it renders nothing on the refusals it expects — a status, and
the `code` of the envelope when the status does not say which —, and follows the same rule for
the rest. The failure screen (`error.tsx` in the shell, `global-error.tsx` when the root layout
fails) receives in production only the `digest` of the error thrown server-side:
`Unreachable` carries `UNREACHABLE_DIGEST`, which it announces as such, `SessionLost`
`SESSION_LOST_DIGEST`, which leads to the sign-in without a click, `SignedOut` (a 401)
`SESSION_REQUIRED_DIGEST`, which leads there by a link (`loginHref`), `UnexpectedAnswer`
the correlation identifier of the envelope, prefixed with `WATERFALL_CORRELATION;` so
that no value from the API takes on a meaning for Next (`NEXT_REDIRECT;…`), and which it
displays as a reference without the prefix (`failure.ts`). Without an envelope, or without a
`correlation_id`, the reference displayed is the digest Next computes, that of its own logs. A
screen never says « empty » on a response it has not read. When the session is unreadable, the
navigation keeps the status screen (WF-ADM-0130).
Each segment that reads the API has its `loading.tsx`, the `ScreenSkeleton` skeleton, which
carries a named `role="status"` — a screen reader does not always announce it; the response is then streamed, and « not found » answers
200 and not 404 — a soft 404, which Next marks `noindex`: the status leaves with the skeleton,
before the page knows the object is not found. It is the same for every address not found,
which is what counts here. Each empty state — no project, project without a revision, incomplete
reference data — is shown on a named example of the contract (`empty`, `incomplete`).

### The home page: the list of projects

The home page, `/`, is the list of projects (`frontend/src/app/(home)/`, a route group so that it
has its skeleton without giving one to every page): filtered by default on the projects of which
the user is a contributor, by the filter of the contract (`is_contributor`), which the screen shows
and which a link lifts — `?is_contributor=false`, under the name of the contract
(`frontend/src/navigation/home.ts`) —: a filter, never a restriction of reading (WF-PRJ-0060).
The link that lifts it is offered only to a session that carries `all_projects_read` (WF-ADM-0110):
lifted for another, the filter would render the same list, and the link would promise what it does
not do (WF-IHM-0090, #522); without this permission, the home page stays filtered whatever the
address says — `?is_contributor=false` included, the page asking for `is_contributor=true` —, the
« My projects » badge displayed without any link, and the choice of the project leads to the home
page rather than to the lifted list. The sidebar and the breadcrumb lead to the filtered list, the
choice of the project to the lifted list, « All projects »; `/projects`, the former address,
redirects to the home page. The projects are one more configuration of the dense grid
(`project-list-grid.tsx`, preferences under the `projects` key): the label, a link that opens the
project, the code, the state by its badge and the date of modification, each column sorted by the
server (`sort_by`), searched by it on the label and the code (`search`), filtered by state —
pressed buttons that write only the address (`states`) — and by period on the last modification
(`from`, `to`, EP-02/L42e): two days entered in the local time of the reader, sent as the instants
of the start of the first and of the start of the day after the last, the end excluded. An address
that names no state asks for all six, the home page showing everything the user may open, where
the contract, without `states`, would render only the projects in progress (WF-PTF-0010); the
pressed buttons are the states the address names, « Every state » when it names none: the address
is authoritative. A period the server refuses — an end before the start, 422 `VALUE_OUT_OF_RANGE`
on `/query/to`, `params.minimum` the start given — is said at its field, the start named by its
local day, which takes the focus each time the list comes back refused, like a bound of a column
of numbers (`range-filter.tsx`); the list is not read, and a sentence holds the place of the grid.
Its totals row says how many projects the server retains, and it leads to the other pages by
`ListPages`; a page asked for beyond its end says so, and brings back to its last page: only a
list that holds no project, without state, period or search, says it is empty. The screens of the
project itself — the project, its settings with its subprojects and its contributors, its
lifecycle — exercise the exit from the lifecycle (`ExitCommand`), irreversible, confirmed in the
page before its server action requests it, the editing of the project, on its settings
(EP-02/L44a, further down), and, on its settings again, the commands of its subprojects and of its
contributors (EP-02/L44b, further down). The data tables of the settings are three dense grids
(#301,
`settings-grids.tsx`), each with its preferences key and its names in the address (`breakdown_`,
`subproject_`, `contributor_`): the work breakdown, a tree grid — each work package, its work
items under it, their deliverables under them —, in the order entered, which does not sort and
folds, searched by the server on its labels (`breakdown_search`) and filtered by nature
(`breakdown_kinds`, EP-02/L42f) — read so, without a counter (`lock_version` null,
`WorkBreakdownReading`), its work packages and work items show only what is retained, which it
says, and such a read is never sent back to `setWorkBreakdown`; its totals row counts only the
elements retained, by nature (`is_match`, #574), and it is entered in its grid as the project
lists `update_work_breakdown`, unavailable also during a background processing (EP-14/L42s;
`breakdown-commands.tsx`, EP-14/L44c): each gesture — an element added, renamed or deleted, from
the menu of a cell on its row or from the bar on the row of the active cell (`RowCommands` of
`DenseGrid`) — sends the whole work breakdown from its whole read, which the page re-reads when
the grid reads it filtered, the added element without an identifier; a deletion is confirmed, that
of a work package or a work item saying that the tasks that carry it remain and lose their
attachment (WF-PLA-0170); a refusal by field that targets the element of the dialog is said at its
field, one that targets another names it; the subprojects, searched by the server on their code
and their label (`subproject_search`), sorted by it on each column (`subproject_sort_by`) and
filtered on their actual costs (`subproject_has_actual_costs`); the contributors, searched by the
server on the name of the account (`contributor_search`), sorted by it on each column
(`contributor_sort_by`), filtered on their status (`contributor_kinds`, `kinds` of the contract),
one pressed button per status (`ValuesFilter`, `filters.ts`), and on the state of the account
(`contributor_is_active`) — a boolean column is filtered by a choice (`ChoiceFilter`), `true` or
`false`, none retaining every row (`readBoolean`); each flat table is filtered so on each of its
columns (WF-IHM-0130, EP-02/L42e). The volumes of §4.6.2 — ten subprojects, fifty contributors per
project — fit in one page. The history of the states, a read-only list, remains a simple table.
The subprojects offer their commands as the project lists `update` (`subproject-commands.tsx`) —
absent, nothing; unavailable, « New subproject » presented `aria-disabled` with its conditions;
available or not, on each row, the editing and the deletion as the row lists them
(`Subproject.available_commands`, EP-14/L44e) — absent, nothing; unavailable, presented
`aria-disabled`, described by its conditions, and a press says them in the region of the list
(`UnavailableCellCommand`): a closed project no longer lists any command, neither its own nor
those of its rows (US-0702/L3), and the screen presents none; the refusal of a direct call,
`project_not_terminal`, stays with the server (WF-IHM-0090). The creation and the editing open the
form of the reference data (`ReferenceForm`), the code and the label required, a code already
carried (409 `ALREADY_EXISTS`, `fields[]`) said at the field, its carrier named by the label the
refusal gives
(`conflicting_object_label`); the deletion, confirmed in the page, is unavailable — or refused by
the server, 409 `STATE_FORBIDS_OPERATION` naming the first condition that is missing, said above
the list (`Reactivations`) — for a subproject that a marked revision cites
(`subproject_not_cited`, §4.4.1), to which actual costs are charged
(`subproject_without_actual_costs`, WF-PRJ-0050) or which estimate lines of the current revision
carry (`subproject_without_estimate_lines`, EP-14/L42q); the screen deduces nothing of it from
`has_actual_costs`. Read unavailable for want of this last condition alone, the deletion leads in
addition, for a session that reads the estimate, to the estimate of the current revision filtered
on the subproject (`subproject_id`, `leadsToEstimate`), the link said in the region of the list
with its conditions; it is not offered when the citation or the costs are missing too, which no
moved line lifts. It reaches the lines of the main structure, never those of another structure,
the own structure of a risk. The lines are named one by one only when the server refuses a
deletion read available (`params.estimate_lines`): each by its number in its structure, as the
grid shows it, and its label, in the sentence up to five, in a list below it beyond, a named list
that scrolls, outside the alert, which would read it in one go, and described by its sentence
(`LINES_IN_SENTENCE`, `OutcomeNotice`, #765), and the refusal recalls that a provision line
changes subproject through its risk (`problemMessage`, WF-DAT-0080); the refusal gives the
structure of a line by its identifier (`structure_id`), not by its label, which the screen does
not read (`structure_label`, requested in #764). The contributors, as the project lists
`manage_contributors` (`contributor-commands.tsx`), are edited as a whole list in a dialog
(`setContributors`): the status of each, their removal, and the enrolment, one by one, of the
suggestions of the server (`listContributorSuggestions`, WF-PRJ-0070), each with the node and the
roles that make it suggested (`org_node_label`, `resource_role_labels`), enrolled active as the
server says (`is_active`), nothing being written before the save; a list without a project
manager is refused before any request (WF-PRJ-0060), a refusal by field (`/contributors/<n>/…`) —
an unknown account (`UNKNOWN_USER`) or a deactivated one (`USER_INACTIVE`) — said at the row of
the account it designates, naming it. The write leaves from a whole read, with its counter: when
the grid reads the filtered list, the page re-reads it whole for the dialog, and the grid keeps
what its read retains. An answered edit replaces its row, a deletion removes it, an answered list
replaces that of a whole read, as long as their counter is more recent — against the fake back, as
long as the screen stays open (`MockupNotice`, under the header); a creation adds no row, the
re-read page files it. A response closes only the form, the confirmation or the dialog it left
from, never another opened since (openings counter, `key`, #672). The command that opens an edit
waits, inactive, `aria-busy` and described by « Saving in progress… », for the response of a
write of the closed dialog, whatever it is, so that the dialog opens on the version it brings
(#661, #734): that of a subproject as long as the edit of that subproject is under way, the other
rows remaining offered (`onWriting` of `ReferenceForm`, `writing` of `SubprojectCommands`, the
description hidden but for a screen reader in the cell, its title saying it to the eye); that of
the contributors as long as the list is being written — the openings counter remains there as a
safeguard. The common pieces of the reference data (`CommandedList`, `useAnswered`) being bound to
its kinds of object, these two lists have their own, on the same pieces: the form, the command of
a cell, the region of the refusals.

### Creating and editing a project

The project is created and edited in the mockup (EP-02/L44a, decision of the author of 2026-10-08,
#513, #524; `project-form.tsx`), through the form of the reference data (`ReferenceForm`, which
also writes an object other than those of the reference data and enters a planning date). The
home page offers « Create a project » to a session that carries the permission to create one
(`project_create`, `platformOffer`, WF-ADM-0100), unavailable, described by the refusal it would
meet, as long as the minimal reference data is incomplete (`getReferenceReadiness`, WF-CYC-0120)
— the home page names each missing prerequisite, the active labour category and, since
EP-14/L42p, the active risk provision category (`active_provision_category`) included, and leads
to the cost settings, as the `REFERENCE_INCOMPLETE` refusal names them under the form; the form
takes what `ProjectCreate` takes — the label, required (WF-PRJ-0080), the code, which may wait for
the order (WF-PRJ-0010), the description — and leads to the screen of the project the server
created, which the fake back serves in the guise of the witness, as long as the home page is still
shown: a response that arrives after one has left it does not replace the chosen navigation. A
response that arrives after « Cancel », the dialog closed but the home page still shown, leads
there all the same: it is the only way to say the success, which the simulated list does not show,
and closed during the wait, the dialog silences nothing. The project settings present its identity
and its facts — the label, the code, the date of receipt of the order, the description, the
inflation rate and the win probability — and their editing (`updateProject`) as the project lists
its command (`update`): absent, available, or unavailable with its conditions — a terminal project
(WF-CYC-0100). The two rates are entered as percentages and leave as ratios of the contract, the
comma moved without a float (`editablePercent`, `percentRatio`); the win probability follows its
own command (`update_win_probability`, EP-14/L44e): unavailable — from In progress on,
`project_before_in_progress` missing (WF-PRJ-0090) —, it is shown fixed (`control: "fixed"`), its
conditions said under it, and is not sent; a date or a text left empty leave null, a half-entered
date, which its field renders empty (`validity.badInput`), is refused before any call. A response
closes only the opening of the form it left from: arrived after the dialog has been closed and
then reopened, it is displayed and leaves the new dialog open (#660); and as long as an edit sent
from a closed dialog is under way, « Edit the project » is inactive (`aria-disabled`, `aria-busy`,
described by « Saving in progress… », `WritingNote`; `onWriting` of the form): reopened, the form
would write from the version its own response replaces, and the server would refuse it (412) — it
opens on the version it brings (#661, #673). It is released on the response, whatever it is — a
success, a refusal, a rejected server action, the API unreachable —; a server action that never
answers leaves it inactive until the page is reloaded. The openings counter remains, as a
safeguard: the command awaiting the write, no other opening comes before the response. The
response takes the place of the facts read as long as it is more recent than the project read
(`lock_version`) — against the fake back, as long as the screen stays open (`MockupNotice`, said
as long as the edit is available) —, the page re-read; the section is remounted when the screen
shows another project. A refusal by field is said at the field, any other under the form — the
probability fixed in the meantime (409 `STATE_FORBIDS_OPERATION`, the condition named), the stale
version with the offer to re-read; a rate outside its bounds (422 `VALUE_OUT_OF_RANGE`,
`params.minimum` or `maximum`, as ratios) is said at the field, the bound as a percentage as the
field enters it (`ratioPercent`); the code already carried by another project (409
`ALREADY_EXISTS`, `fields[]`) is said at the field, the project that carries it named by the label
the refusal gives (`conflicting_object_label`), the screen not showing the other projects —
generically without it (`kind="project"`, EP-02/L42g). The lifecycle says the next state of the
project, its trigger and the conditions it still lacks, one by one (`getProjectNextState`,
`NextStateFacts`, WF-CYC-0050), as no command leads to Pricing or to In progress (WF-CYC-0020); the
trigger is one of the two facts the contract enumerates (`LifecycleTrigger`), said by its
catalogue (`enums.LifecycleTrigger`). A project that no fact leads any further — the server
answers without a next state or a trigger — says so: in progress, only its exits remain; terminal
— a state an exit leads to (`EXIT_STATES`) —, it is closed, and no state follows it (WF-CYC-0080).

### The periods of a list

A period of a list takes one of the three forms of the contract (`period.ts`), all entered in the
same filter (`PeriodFilter` of `frontend/src/components/grid/`): two planning days, bounds
included, which the server receives as they are — the actual cost documents —; two local days
turned into instants, the end excluded — the home page —; two instants entered to the minute in
local time, the end excluded — the audit log. Only the browser knows its time zone: the instant
fields show the address, and the button sends, once the page is hydrated; a side left untouched
leaves as the address names it. The refusal of an inverted period, the rule of every period of the
contract, is said at the field of the end, the start named as its field shows it.

### The context of a project screen

A project data screen reads its context through `readAddress` of
`frontend/src/components/context/reading.ts` — project, revision, active filters, read once per
request — and shows it through `ContextBanner`, above its `<main>` (WF-IHM-0020). The read
carries `edits`, the `edit_*` commands of the revision the caller may exercise (`read-only.ts`),
which a screen receives rather than deducing them. What a grid offers — the entry, the gestures,
the paste — is however not read there, but in the structure it reads (`screen.commands`, of
`grid-screen.ts`, from `available_commands`): its own command — `edit_planning` for the planning
—, because the phase of the project is not that of the revision (the estimate of the main
structure of a project In progress is read-only, the remaining to commit is not, nor is the
estimate of a differential or of a risk) and because an estimator may enter the estimate without
touching the planning. The planning and the estimate read the structure the address names
(`structure`, `components/context/structure.ts`) — the main one by default, a differential of an
amendment, the own estimate of a risk —, which the revision lists (`listCostStructures`), another
one being not found; the remaining to commit, the timelines and the tree, the main one only
(`GridReading.chooses`). The banner names the structure read, its nature when it is not the main
one, and offers the others of the revision (`StructureChoice`); this parameter is that of the
grid: the links between functions carry it only from the planning to the estimate and from the
estimate to the planning, which read the same structure, and never towards another screen, which
falls back on the main one (`readsStructure`, `navigation/context.ts`, #1220). The grid is mounted
per structure (`key`), and the skeleton is offered only on the main one (US-0500). `readOnly` —
marked revision, or no `edit_*` command available — serves only the notice of the banner. A value
under a `Computable` envelope is displayed through `ComputedIndicator`, never without the date of
its `CalculationContext`, and when not computable with its reason, a code the catalogue renders
(`enums.NotComputableReason.*`, `indicator.tsx`).

### Curves

A curve is a figure of `Chart` (`frontend/src/components/chart/`, US-0240): Apache ECharts,
imported piece by piece and drawn in SVG, its `aria` option on; its legend names it, the drawing
is an image a sentence of the catalogue describes, and its values are a table under it, the
textual alternative (WF-IHM-0100). The client component of the curve's own (`index-chart.tsx`,
`milestone-chart.tsx`, `curve-series-chart.tsx`, `workload-chart.tsx`) hands it its option, built
in a palette: ECharts writes its colours in the attributes of its SVG, where a CSS variable does
not reach, and the tokens `--chart-1` to `--chart-4`, `--muted-foreground`, `--foreground`,
`--input`, `--border` and `--background` get there through hidden probes the browser paints in the
displayed mode; a change of mode, from the workstation or forced by the account (`data-theme`),
redraws the curve. It is drawn in one go, without animation, and a legend is inert there: a
click, with the mouse alone, hides no series. `curve` names each curve at its last plotted point,
whatever their number — no legend, which one entry per subproject would make overflow onto the
plot —, the names that would overlap set aside, and distinguishes it also by its colour, its symbol
and its stroke; a workload plan is a stacked histogram (`stackedRoles` of
`workload/stacked-load.ts`: one bar per month, divided by role, the patterns kept), whose tooltip
for a month lists the roles and their hours (`monthTooltip`, labels escaped); that of the project
has no capacity line (#375) but carries at the top of each bar the total of the month the server
renders (`monthly_totals`, `monthTotals`), like that of the portfolio, which also carries, dotted,
the capacity of the perimeter (`capacity_monthly_hours`), the table of the roles, their rate and
their signals being under the chart; the links to the workload plan open a basis (`basis`,
`workload/workload-basis.ts`): the remaining to commit `current_remaining`, the estimate
`reference_budget` for a project in progress or completed that has a reference, `current_remaining`
otherwise; the link from the remaining to commit to this plan is an icon alone (`aria-label`,
`title`), the title of the screen and the totals of its grid fitting in the 1280-point window only
at that price (`remaining.spec.ts`); a curve without a plotted point has no name on the drawing,
its table names it; a series of bars (`bars`) is also distinguished by the pattern of the symbol of
its rank, which the legend shows; `timeAxis` graduates a time axis at the first of each month that
`monthTicks` draws from the instants it shows — every two, three, six months or every year over a
long range, the year alone then, or every two, five, ten years, on the years that are multiples of
the step (#415) —, written in the language of the workstation, in its time zone or in UTC for an
axis of planning dates, which `planningInstant` places at their UTC midnight, the option of the
figure then saying `useUTC`. A curve plots the strings of the API as they are — ECharts draws a
position from them —, a non-computable value being a gap, a cumulation of dated events — earned
value, actual cost — as a staircase (`step`), one vertical step by two points at the same date,
and the table writes them through `src/i18n/format.ts`, the zones through `Signal`. The risk
matrix is a bubble cloud (`risks/risk-bubble-chart.tsx`, `RiskBubbleChart`, shared by the project
and the portfolio): one `scatter` per risk state — the circle, the diamond, the triangle, which
the legend shows —, over sixteen `markArea` of a separate series, one per cell, which
`ChartPalette.zones` colours with the tokens of the zones (`ZoneProbes` of `signal/signal.tsx`,
the only file that names these tokens); a zone is named in its area when its band has room for a
line, and its edge has a stroke of its own (solid, dashed, dotted), the colour never carrying it
alone. The axes run from zero to the end of the last level — which the server leaves without an
upper bound, and which ECharts does not extend for an area —, to the highest bubble at most; a
bubble is at the exact probability and share of severity of its point, and its size, bounded,
follows the severity upwards; the tooltip says the risk, its project in the portfolio, and the
click (`onPoint` of `Chart`, by the `id` of the datum) opens the detail of the risk in the address
of a project, or the project of a point that `can_open` allows to open. The table of the count per
cell (`RiskCountsTable`, `cells`) is that of the values of the figure. No bubble is reachable by
keyboard, and it is said: the risks grid, on the same screen (project), gives the keyboard access
to the same data, through the link of the label of each row, and in the portfolio the table of the
heaviest and `/portfolio/projects` suffice for it (#1253). The axes stay linear, at the exact
values (WF-IHM-0100), even if the band from 0 to 1 % of severity measures only some fifteen points
there: a piecewise scale would distort the reading of the positions. `folded` of `Chart` holds
only for the initial state of the drawing — a button shows it and folds it thereafter —, and a
later change of the prop neither folds nor unfolds it. A figure that receives `exported` offers
the « Export as PNG » command (WF-IHM-0130): `exportPng` redraws it in an off-screen instance, in
canvas rendering, at the size of an image, its title and its provenance (`useProvenance`) —
project, revision of the calculation, what the figure is otherwise calculated on (`detail`: the
basis and the filtered organisation node of the workload plan), calculation date, written in the
time of the workstation at the moment of the export — at the head, wrapped to the width of the
image (`wrapLines`), the figure moved down by the height of their lines, on the background of the
visual identity, then releases the instance. A choice that changes what a curve reads — the
payment terms, the basis and the organisation node of the workload plan — is a parameter of the
address, which the server sends to the API: the front neither filters nor shifts anything.

### The indicators screen

The indicators screen of a project reads its indicators and its curves in the revision of its
route (`revision_id`) — those of a marked revision as its marking preserved them —, or at the date
the address asks for (`as_of`), never both, which the API refuses together; an offer marked before
the In progress state, which preserved none, is refused like a project that is not in progress,
and the screen says so. A notice at the head names, among the indicators and the evolution of the
indices, the one that is calculated on another revision than that of the banner, and which — the
evolution, always to the day on the current revision (`ComputedElsewhere`); a curve names its own
in the image it exports. The subproject of the address, the one the banner shows (WF-IHM-0020),
restricts what the API reads for it (`scope`, WF-IND-0020) — the indicators, the evolution of the
indices, the cumulated costs and the earned value curves (EP-02/L42e) —, except the time/time
diagram, calculated for the project alone: it follows milestones, which a subproject does not have
(WF-IND-0020). The badge of the banner says so (`restricts` of `ContextBanner`, as for the grid of
the remaining to commit, #459), and the milestone tracking says that it covers the whole project
(`WholeProject`). A subproject the project does not have, refused by 422 `UNKNOWN_SUBPROJECT` on
`/query/scope`, is said like the indicators of a project that is not in progress, never read as
null indicators; a curve without a point says it has nothing to plot rather than plotting a zero,
and a series without a point among others that have some says so under the chart — the reference
budget of a mesh that no reference budgets —; an empty curve not shifted does not offer to shift
it, and, shifted, keeps the command that removes the shift.

### Key figures as cards

The key figures of a screen are presented through `FiguresCard` (`src/components/figures-card.tsx`),
never inline in a `<dl className="flex …">` laid on the page: a card is a region named by its
title (`role="region"`, `aria-label` of the title), which carries the calculation date when the
response has a context (`context`, `CalculationDate`, WF-IHM-0020) and its figures in a list of
terms (`FiguresList`, a `dl`) — the name, then the value, for a screen reader. The cards of a
screen are arranged in `FiguresGrid`, which wraps according to the width; the cards share the
width there, and a card alone stretches over the whole row. The calculation date is repeated on each
card of a response that has one: each region is read alone, with its title and its date, without
having to go back up to another. It is placed under the title, never after it on the
same line: written after hydration (`LocalTime`), it would make the card jump by a line. A card carries a block of figures that is read together — the
totals, a breakdown as a list, the risk coverage —, never the whole page. The values, their
format and their signals (`Signal`, WF-IHM-0070) are those the screen had: the card adds only the
frame. `IndicatorCard` (indicators screen) reuses it while keeping its former look (`spacious`), the curves and the tables it carries needing the room; the other cards are compact, so that the grid keeps its totals in the window. The six screens that
follow it are the risks, the estimate, the remaining to commit, the actual costs and the two views
of the portfolio, performance and risks on one hand, value on the other; the banner of the reading
context, an information band, is not one. On a filled screen (`Screen fill`), the totals row of
the grid stays in the window under the cards, at 1366 and at 911 wide by 768 high:
`e2e/grid-frame.spec.ts` checks it, risks included: the chart of their matrix, between the cards
and the grid, starts folded (`folded` of `Chart`), a button shows it and folds it, because unfolded
its height (288 points, `h-72`) does not leave the totals in the window at 768 high (#1252). _Check_: review;
`src/components/figures-card.dom.test.tsx`, `e2e/accessibility.spec.ts`.

### Grids

A grid is the dense grid of `frontend/src/components/grid/` (US-0110), configured per screen: a
`GridConfig` (`columns.ts`) names the key of its preferences, stable, its columns — key, label of
the catalogue (`grid.columns.*`), format, alignment, default width, those of its cells the server
computes, frozen or not, the column of the contract it shows (`contract`) — the one the server
sorts it by and the one a paste targets —, and, for a narrow column, the icon that stands in for a
header and that its label names, or what its cell renders in place of the formatted value
(`render`) — and, if it has one, its tree (level, nature icon by `RowNatureIcon`). Sorting is first
the grid's business: a tree grid whose rows keep the order of the plan sorts none of them
(`sorts: false`), and its address asks for none — the planning (§3.4, WF-IHM-0060, #525). The
estimate and the remaining to commit, of which the server sorts only the lines under each task,
the tasks keeping the order of the tree (WF-IHM-0060, #526), do not sort by a column of the task
alone, which the contract accepts but whose sort would change nothing: the column says so itself
(`GridColumn.sorts: false`), while keeping its column of the contract, which a paste targets
where the grid takes one (the planning, the estimate) — progress and finish in the remaining to
commit, which thus offers only what acts (in the spirit of WF-IHM-0090). Neither its header nor
the address offer the sort, and a sort by it, in the address or kept by the account, is ignored
like an unknown sort (`sortColumns`). The configuration reads the rows through functions: it is
handed to `DenseGrid` in a client component of the screen's own (`estimate-grid.tsx`,
`planning-grid.tsx`), and the page, server-side, passes it nothing but data — the structure read
and, of each node, the only fields the grid reads: those of every grid (identity, version,
computed fields, number, level, parent, nature, label) and those of its columns, which its
configuration names (`ESTIMATE_FIELDS`, `PLANNING_FIELDS`). The page asks `listNodes` for them
(`fields`, `nodeFieldNames`: a field of a facet under its name, `task.label`) and projects them
again (`projectNodes`): a server may render more than it is asked for — the fake back renders its
whole example —, and the six thousand whole nodes weigh six and a half megabytes in the page,
projected, forty-eight to sixty-five per cent — the parent, by which the tree folds, added four
points to it; the reading of the screen (`readGridScreen`) renders only the projected rows and the
totals, never the whole response. A field of a line that says nothing — null, or false for a
flag (`SPARSE_LINE_FIELDS`) — does not pass through, the cell reading it as null, and the
subproject identifier of a line passes through only to a grid that enters it
(`withoutSubprojectIds`). A column that reads a new field adds it to that list: the typing of the
row requires it, and `projection.test.tsx` checks that the grid reads the same thing from the
projected row as from the whole node, and that the page asks for what it projects. The computed is
read cell by cell (WF-IHM-0030, `computed-nodes.ts`): a field that no write carries — the
amounts, the float — is computed in every row that carries it, and its column has Σ in its
header; an enterable field is computed where the node names it in `computed_fields`, never from
its mode or its nature. A computed cell is greyed, marked Σ and named « Computed » — the mark
reads without the colour —; it is a button which, clicked or pressed on the keyboard, refuses the
entry in a Popover (`ComputedCell`, `ComputedRefusal`) by saying what its value depends on, which
the server says: each computed column names the field of the contract of each of its cells, and
the refusal calls `getComputedValueDependencies` for the node and that field, through a server
action (`readComputedDependencies`) that the grid receives from its screen (`nodeDependencies`,
one reader per reading of the page) — only while it is open, and once per question: the reading
of the page, the node and the field. A closed refusal asks nothing; reopened after a re-read of
the page, it asks again, because the rows it names may have changed number or label without the
node changing version; a failure is asked again at the next opening, only an answer is kept. In a
single announced region (`role="status"`, `aria-live="polite"`), present from the opening and
`aria-busy` during the reading, it says that it is reading it, then the rules that compute it
(`enums.ComputedDependency.*`) and the rows it comes from, named by their number and their label,
whether the grid shows them or not; a refusal of the server, or the API unreachable, are said by
`OutcomeNotice`. A row that says itself what its value depends on — a risk, its severity and its
provision (`Risk.computed_fields`) — gives it to its column (`dependsOn`), and the refusal names
the rules outright, without asking anything. The front reads no rule of the core. The Popover is
mounted only at the first attempt: one Radix root per computed cell would weigh down the
hydration of the first screen. The planning grid and the estimate grid are two configurations of
this single component (`planning.tsx`, `estimate.ts`), which share the tree, the number and the
label of a node (`nodes.tsx`) and the reading of the structure the address names
(`grid-screen.ts`); the planning asks the server for the tasks only (`kinds=task`). The estimate
presents, of a line as of a task, summary included, and in total, the amount at the reference
year, before inflation (`base_amount`), as the server renders it, never the budgeted nor the
re-estimated, inflation included (WF-DEV-0020, WF-DEV-0050); it names the category and the role of
a line by the labels the server resolves, the object active or deactivated
(`cost_category_label`, `resource_role_label`, #305); the subproject of a provision line, the one
its risk designates, is there a computed cell, which the node names
(`estimate_line.subproject_id` of `computed_fields`, EP-14/L42p), and its refusal asks the server
what it depends on, like its quantities — the lists of the reference data serve only the choice
of an entry, offered only on an object they know; they ask for the deactivated objects
(`include_inactive`) only for a session that carries the read permission of their part of the
reference data, which the contract requires, and an estimator without it enters on the active
objects (#351). What a write renders is read the way the grid reads it (`nodesWritten`): the nodes
written and their whole ancestors, of the re-dated tasks the part of their calendar it shows
(`rescheduled`), of the lines and tasks moved in time the part of their amounts it shows
(`reinflated`) — each part sets only its own fields: those of a same row, from one write or
several, are laid over one another in the order of the answers (`answers.ts`). The planning mode
and the progress show there by a named icon, the critical path by an icon and bold on the float,
never by the colour alone; a date shows in its short form. The sort and the search are in the
address, under the names of the contract (`sort_by`, `sort_order`, `search`, `query.ts`): a
clicked header or an entered search changes the address, the page re-reads the operation with
them, and the grid renders the rows in the order received, the totals of the response in the
footer — TanStack Table records no sorted, filtered or grouped model there. On the keyboard, the
grid is a single tab stop, its active cell, which the arrows move, header included — its buttons
and its handles out of the tabbing —: Enter or Space on a header sorts its column, Shift and the
arrows widen or narrow it (ARIA `grid` pattern, #182). A write refusal stays said until the user
closes its notice (`OutcomeNotice`, `dismissible`), whatever succeeds after it. Only the visible
rows are rendered (`row-window.ts`, on `@tanstack/virtual-core`): the virtualiser is read as a
store whose snapshot is a datum, which changes only when the window moves. The React Compiler is
not enabled in this front, but React's lint refuses the TanStack Virtual adapter, whose compiled
render would freeze the answers (`react-hooks/incompatible-library`). The height of a row follows
the size of the root font (1.75 rem). The header and the totals are stuck to the top and the foot
of the grid, the number and the label to its start. The header row of every table, list as well as
dense grid, is on the `muted` background of the visual identity: `TableHead` sets it on the header
of a column, in the `<thead>`, not on that of a row, and a hand-written `<thead>` takes it likewise
(#508), which `frontend/src/components/thead-guard.test.ts` checks in the sources. The grid takes
the height its screen leaves it: a grid screen is a `Screen` that fills the window (`fill`), the
page bounded to its height (`ShellFrame`), and the grid shrinks there by the height of its rows
down to a floor, ten rem at most and never more than its content
(`min(10rem, 2 × EDGE_REM + max(lignes, 1) × ROW_REM)`, `grid-floor.ts`, #1041) — no height is
computed there from what precedes it; a window too low for that floor makes the page scroll. The
envelope of the grid and its bar carries that floor, plus the bar, as minimum height: the
envelopes of the screen, which shrink to what remains (`min-h-0`), do not push the frame under its
floor onto what follows it in the same envelope — the filters above, the pages below. The floor
climbs no higher: an envelope in `min-h-0` may stay lower than the frame, which the page absorbs
by scrolling, as long as nothing follows it. A screen that has content under the envelope of its
grid, outside the chain that contains it — were it only in a narrow window, where the neighbouring
content lines up below (the actual costs, the risks) —, does not fill the window where it has it
below (`fillWide`, `lg:min-h-0`), just as `/admin/backups` and the reference data of resources and
costs, which stack their grids, do not fill it: the grid would overflow onto it (#1033).
`frontend/e2e/grid-frame.spec.ts` measures it on the nine screens that fill the window, in a low
window, at the two widths of the harness: the frame overlaps nothing. The bar and the « Columns »
button have the width of the frame of the table, as the browser sets it (scrollbars included,
`frame-width.ts`), without exceeding it, and never less than what the bar holds on one line
(`min-w-min`, the search shrinking before anything wraps, apart from the command list of a screen,
which wraps by itself); the notices — refusal, paste applied, columns not shown, entry problem —
keep the whole width (#1042). Hidden columns, widths and sort are a display preference
(`settings.ts`, WF-IHM-0060): read from the session, the grid replaced whole at each write and what
it does not set returned as is. It also writes the keys of all the columns it offers
(`known_columns`, `gridShape`, US-0650): a column hidden by default that the grid did not know at
the last write is hidden, a column the account chose to show stays so; settings written before
that list know none of them, and a column hidden by default is hidden there
(`docs/api/DECISIONS.md`). A grid keeps in the account its sort and its columns — those it hides,
and their widths —, never its page (rule validated by the author on 2026-10-09). Its filters, a
grid that declares them (`GridConfig.filters`) keeps them as a preference, as the criterion of
US-0380, which is authoritative, wants (#836, confirmation of the author to come): they are found
again at the opening of an address that says nothing of the grid; the page and the filters of an
address that says them live in the address. Any other grid keeps no filter. A column or a width
is written after a pause, with the sort kept as is; what is waiting leaves when the page is left
or hidden, before a search and at unmounting — at best: a server action does not carry
`keepalive`, and closing a tab can interrupt it. Only a header click writes the sort, once the
page shows it (`recordShown`), with the settings of that moment — a width changed during the
navigation included: Next carries a server action in the state of its router, and a navigation
does not show before the actions launched after it have answered — written at the click, the
preference retained the sort of a round trip, and of each action queued before it. Until then, it
waits like the rest, and leaves with it if the page is left, hidden or unmounted, or before a
search. The address is authoritative: a lifted sort stays there, `sort_by` empty, and the kept
sort serves only when it says nothing of the sort. Each grid is at the route of its function,
`…/revisions/[r]/planning` and `…/revisions/[r]/estimate`; the revision itself leads to the first
function of a revision the session can read, in the order of the FBS and of the sidebar — the
planning, or the estimate for an estimator who does not read the planning. The estimate screen
says above its grid the hourly rates its computation lacks, with the path of the reference data
for whoever reads it, and its indicators, with their date of computation, or that they are
unavailable when the API does not find them or refuses them for lack of an hourly rate
(`HOURLY_RATE_MISSING`, #159) — these two cases do not bring the screen down; any other response
follows the rule of the readings (`EstimateSummary`).

A grid that reads a differential (`CostStructure.kind` = `amendment`) is a diff against the main
structure, which the server computes (`Node.difference`, rendered on each node, with the removed
nodes in their place): it receives `GridConfig.difference` (`withDifference`, `nodes.tsx`) and a
`DiffMark` column at the head (`diff-mark.tsx`, `DIFF_MARK_KEY`), before the number. The character
says the difference — `+` an addition, `-` a removal, `M` a modification, a summary task whose
content changes included —, the colour doubles it, the mark in the green, the red or the yellow of
its token and the row tinted the same (`--diff-added`, `--diff-removed`, `--diff-modified` and
their `-mark`, with their dark values), never the colour alone: the word — « Added », « Removed »,
« Modified » — is read by whoever sees neither, and an unchanged node carries nothing. The tokens
are measured in both modes (`contrast.test.ts`), and the planning and estimate grids on amendment 2
are screens of the accessibility harness (`DIFFERENTIAL_SCREENS`, `e2e/routes.ts`). A removed node
is read and not touched: no structure gesture is offered on it, neither « Insert » nor « Delete »
nor Ctrl+Delete, it does not move, nothing drops next to it (`isRemoved`, `structure-rules.ts`,
#1185), and the predecessors cell follows `editable_fields` (`task.predecessors`): that of a
removed task, which does not name it, is not enterable (#1257).

The comparison of two revisions (`/revisions?from_revision_id=…&to_revision_id=…`) is the same
grid, read-only (`comparison-grid.tsx`, `components/revisions/`): the nodes of
`compareRevisions` — the tree of the compared revision, the removed nodes in their place —, each
with the mark the server renders (`difference`, `changes`, a task moved under another summary task
marked modified, WF-REV-0080), the `DiffMark` column at the head, then the number, the label
indented by its level under the icon of its nature, and what changes in the node, named as the
server names it. The comparison does not paginate, like `listNodes` (#1201): the screen asks for
the whole tree, reduced by `fields` to the columns it shows (`COMPARISON_FIELDS`, `kind`,
`task.label`, `estimate_line.label`) and projected (`comparisonRows`); the server always renders
the number, the level, the version and the mark. For lack of a parent among those fields, the tree
does not fold; nothing sorts or searches, the order is that of the plan. The 5,999 nodes of the
volume example (`volume/comparison_volume.json`, 2,770 of them modified) mount only one window of
rows, and the screen keeps the bound of a grid screen (`WORKING`, 15 s, `revisions.spec.ts`); the
path plays the example of the window, the fake back serving the first example of the operation.
The amount gaps remain a table under the grid, and the screen is one of those of the accessibility
harness (`DIFFERENTIAL_SCREENS`).

### The planning grid and the Gantt

Above the grid, the planning start date of the structure read (`CostStructure.planning_start_on`,
WF-PLA-0020), as the server gives it (`PlanningStart`, `planning-start.tsx`); where the structure
lists `edit_planning`, a confirmed command changes it (`updateCostStructure`, `updateStructure`)
with the counter of the structure, the page re-read for the tasks the server re-dates, and the
answered date shown as long as the page read is older; a day without a working hour is refused by
`NON_WORKING_DAY`, said under the field with the next working day. The write counts among those of
the grid (`StructureAccount.writing`). The grid presents the start and completion dates
(`started_on`, `completed_on`), read-only, after the float, and names the conflicting link
(`link_conflicts`) by an icon in the predecessors column — on the manual task as on its
predecessor — and in the name of the Gantt bar: the row of the predecessor, the type of the link,
the row of the task when the grid reads it (`link-conflicts.tsx`). The planning grid also presents
the description of a task and the physical progress of a summary task, a percentage computed or
not computable, its reason as title; then the Gantt (FBS-4.3.3, `frontend/src/components/gantt/`),
its last column, read-only, pinned to the right (`GridColumn.pinned: "end"`, `pinning.ts`,
US-0530): it slides over the columns that precede it when it widens, and the grid scrolls them out
from under it (`scroll-padding-inline-end`). Its handle, on its left edge — the mouse, or Shift and
the arrows, the left arrow widening it —, sets its width, that of `gantt` in `column_widths`, and
modifies no task, from a minimum up to the room of the frame at its greatest width
(`useFrameRoom`), minus the columns pinned at the head and the widest of the others, where the
active cell shows (`endMaxOf`). Each cell draws in SVG the row of its task — its bar, the pieces of
the links that leave it, run along it or reach it, the months of the axis —: the drawing is aligned
row by row on the grid, rendered with its visible rows only, and follows the width of its column,
as a share of that width. The layout (`ganttLayout`, `layout.ts`) is computed once for the rows the
grid shows, writes included, which `DenseGrid` hands to what a screen puts around it (`around`,
`GanttRows`) — never as a prop of each row; the header draws the axis (`GridColumn.axis`), its
label naming the column only to screen readers any more. Nothing is planned there: a task runs
from the start of its first day to the end of the last, a finish at hour 0 being the start of its
day, a milestone stands at its finish, and the axis runs from the first of the month of the
earliest to the first of the month that follows the latest (`monthTicks`, `chart/ticks.ts`, without
ECharts). A link joins the place its type names on the predecessor to the one it names on the
task; a predecessor outside the response draws none. A summary task is a bracket, a milestone a
diamond, a task a bar, solid on the critical path and hollow elsewhere, and each bar is an image
named by its dates and « critical »: nothing is read by the colour alone. No cell of the Gantt
takes an entry, and only the button that precedes the bracket of a summary task takes the pointer
there, to fold or unfold it. Its finest level divides each day into working hours, numbered within
their day, which the page reads from `getDurationUnits`: `hoursOfDay` (`scale.ts`) rounds
`hours_per_day` to the nearest whole hour, the half-hour upwards, from 1 to 24, on the digits of
the string, never through a float (#1393). « Export as PNG », after the zoom in the corner of the
header and in the menu of a cell, draws on a canvas (`gantt-image.ts`) the whole extent at the
level shown — the width of the zoomed drawing, that of the column once fitted to the project —,
one row per task the grid shows, folded like it, the days off with the same hatching as the screen
(`DAY_OFF_HATCH`, read from the classes of its tokens) and their legend, the provenance at the
head as for every curve (`useProvenance`, `provenanceOf` of `grid-screen.ts`); twice as dense as
the screen as long as a canvas holds it, as dense otherwise, and unavailable, its reason said,
beyond the bounds of the browsers (32,767 points a side, 268 million in all). Its « Attached to »
column presents the work package or the order item a task carries, by the label the server
resolves (`work_breakdown_label`); where the structure read lists `edit_planning`, the cell chooses
it among the work packages and the order items of the whole work breakdown read, or nothing,
written by `updateTaskFacet` — the chosen field, and the other set to `null` in the same write when
the task carries it (`planning-attachment.ts`) —, its refusal said by the reason of its field,
naming the task that already carries the element or those that would leave the subtree of their
work package (WF-PLA-0170); like every refusal of the write of a cell, it is said above the grid,
and its cell, marked, is described by it (`aria-invalid`, `aria-describedby`). There too, the task
is entered on the keyboard, cell by cell, through `updateTaskFacet` (US-0470, `planning.tsx`): the
label, the description — emptied, it is null —, the mode (a list), the duration with the suffix of
its unit and the dates, each where the node carries its task, names its field among those it
accepts (`editable_fields`) and does not compute it (`computed_fields`): the dates of an automatic
task, the duration of a summary task are passed over without entering entry mode (WF-PLA-0020).
The duration is read in the language of the interface (`parseDuration`, `cell-values.ts`),
regardless of case, a bare number in days: the suffixes WF-PLA-0160 names are read in every
language — « m » a month, « min » a minute, « h », « j », « sem », and their elapsed counterparts
prefixed with an « e » —, plus those the catalogue writes in the current language
(`enums.DurationUnit`), and no other: in English « d », « wk », « mo » are read, in French they are
not. It leaves in its unit, which the server keeps. A date is typed in the short form of the
language, or in its ISO form (`parsePlanningDate`), and leaves alone, without hours: the front does
not know the calendar, the server completes the hours — the start at the start of the working
day, the finish at the end of its hours —, and the cell shows what it renders (#1244). The
predecessors of a task are entered as in MS Project, « 3FD+2 j ; 5DD » (`predecessors-entry.ts`):
the row number, the code of the type of the link in the language of the interface — FD, DD, FF, DF
in French, FS, SS, FF, SF in English, nothing for a finish-to-start —, then the lag, positive or
negative, with the unit of a duration (the suffixes of `parseDuration`) or as a percentage of the
duration of the predecessor; the whole list leaves in place of the task's, through
`setPredecessors`, with the version of the node read. The number resolves on the rows the grid has
read (those of a predecessor a search has set aside are found again through the links of a row
read); a number they do not know is asked of the server, in the numbering of the whole structure
(`resolveRowNumber`, US-0650), the entry read-only and `aria-busy` as long as it has not answered
(`EntryKind.ask`, `useRowNames`), then validated again. A number no task carries — an estimate
line, or no node (404) — leaves the entry open, which says so, without sending anything; a server
that could not answer too, saying to validate again. Left by a click elsewhere during the request,
the entry validates at the answer, or is abandoned. A refusal of the server is said at the cell by
its code — a loop of links, with the tasks it crosses (`cycle`, `problemDetails`), a link between a
summary task and its subordinate, a project that would exceed fifteen years —, and the rows
written, with the tasks the server re-dates, take the place of the rows read, the Gantt following;
the front dates nothing. Validating the last enterable cell of a row places the cursor on the next
row, at the cell from which the row was started. Every cell write, of every grid, says a refusal
per field by the reason of its field (`byField` of `cell-writes.ts`, #817.1); only a refusal of the
value (422) marks the cell, the API out of reach, a stale version or a lost session saying nothing
of what was entered (#819.2); a value the answered row already carries writes nothing, failing
which the body would carry only the version (#819.8), and lifts the refusal of its cell, with the
notice that says it. Above the planning grid and the estimate grid, a filter chooses a work
package or an order item from the same whole work breakdown read (`BreakdownFilterChoice`,
`readGridScreen` with `byBreakdown`), written in the address under the name of the contract —
`work_package_id` or `order_item_id`, the one lifting the other, a malformed identifier ignored —
and sent to `listNodes`, which retains the subtree of the attached task; the banner shows it active
and lifts it (`breakdownChip`), in the estimate on the grid only, its indicators remaining those of
the project. A work breakdown the API refuses (404, 422, 503) removes only the filter, except where
the attachment is entered, which cannot do without it (`needsBreakdown`). In the empty grid, the
skeleton is offered as the revision lists `generate_skeleton`, unavailable with its condition as
soon as the structure has a task (WF-PRJ-0030); generated, its tasks fill the grid as long as the
counter of the structure it renders is more recent than that of the reading (EP-14/L44d). The
other leaves of the planning have their screen, where its header leads: the task tree (FBS-4.3.5,
`…/task-tree`, `frontend/src/components/tree/`), an ARIA `tree` under the root of the project, the
first level side by side, the next ones under their parent, a single tab stop the arrows walk
through, the depth in the address (`depth`); and the timelines (FBS-4.3.1, `…/timelines`), one per
link (`timeline`), each a strip with lanes, distinct from the Gantt (`gantt/timeline-chart.tsx`,
US-0530, #1068): on the axis of the Gantt, at its levels and its zoom (`GanttRows`, `GanttAxis`), a
task is a rectangle from its start to its finish, its name truncated and whole in the tooltip and
the accessible name — the task, its dates, its lane —, a milestone a vertical line over the whole
height, its name and its date at the foot. The rectangles stack in lanes (`lanes.ts`, a
presentation computation): each in the one where the user placed it as long as it fits there, the
others, in the order of the plan, in the first lane where they overlap none, the empty lanes closed
up. A rectangle is dragged with the mouse from one lane to another, or moved by Alt and the up and
down arrows on the one the keyboard designates — the strip is a single tab stop, the left and
right arrows passing from one rectangle to the other (`aria-activedescendant`). A lane where it
would overlap another is refused, the refusal said, and nothing moves; under the last lane an
empty one is always offered, never above another, and the keyboard targets the nearest lane where
the rectangle fits, skipping those where it would overlap, to reach everything the mouse reaches.
The layout is a display preference per timeline (`DisplayPreferences.timelines`, WF-ADM-0040),
written after a pause like the settings of a grid (`useKeptWriter`,
`updateTimelinePreferences`): the lanes of all the rectangles shown, the moved one first, within
the bound of 64 of the contract, so that a move moves nothing else; « Automatic layout » forgets
it (`null`). The table reading, under the strip, says each task, its dates and its lane; they are
created by their name and the timeline shown is deleted after confirmation, as the project lists
`manage_timelines` (`timeline-commands.tsx`, EP-14/L44c). The server selects what each one draws
(#463): the tree asks for the summary tasks down to the level of the address (`summaries_only`,
`max_level`), a timeline the tasks inscribed in it (`timeline_id`). The fake back ignoring these
filters, each one applies the same criterion again to the response (`summaryTree`,
`inscribedTo`): an idempotent filter, which changes nothing against a server that honours them, a
temporary gap of EP-02 removed with the back of EP-03. The tree offers exactly the levels the
structure has, from the first to that of its deepest summary task, which the server says whatever
the filters (`meta.summary_depth`, #494), and shows the level asked for, or the deepest when asked
for one beyond it (`depthShown`).

### The risks screen

The risks screen, `…/revisions/[r]/risks` (`frontend/src/components/risks/`), reads each of its
operations in the revision of its route (`revision_id`): the totals of the provisions of the
retained risks, by state and the grand total, as the server renders them; the filter by state,
pressed buttons that write only the address (`states`, under the name and the form of the
contract); the dense grid, one more configuration (`risk-grid.tsx`), read-only, where the
severity and the provision are entirely computed columns — no node field to ask for (`field`
renders `undefined`), their refusal names the rules the risk carries for each one
(`computed_fields`, `dependsOn`) — and the matrix cell a `Signal` column; the risk matrix, a bubble
chart (`RiskBubbleChart`, « Curves ») over the whole width between the cards and the grid — the
right-hand column no longer exists —, whose bubbles are the risks of the states of the filter, and
under it the table of the count per cell, its axes named by the bounds the server renders, each
cell by its signal and its number of risks; and, when the address names a risk (`risk`) — from a
click on its bubble or on its label —, its detail, in a column beside the grid that keeps enough
room to read it (the page scrolls in a window too low): notes, provision line present or withdrawn
at the occurrence, with the category and the subproject the risk designates for it, by the labels
the server resolves — the category said deactivated when it or its cost type is
(`provision_cost_category_is_active`), the provision outside any subproject when it designates
none (EP-14/L42p) —, history of the reviews. « Identify a risk » (`risk-commands.tsx`), in the
header of the screen, follows `declare_risk` as the revision of the route lists it: absent,
nothing; unavailable, described by the condition that is missing (`at_least_one_task`,
`active_provision_category`); available, it opens the form `risk-form.tsx` (`ReferenceForm`) —
label, description, mitigation actions, probability as a percentage sent as a ratio, category of
the provision asked for only when several active categories of the provision type offer
themselves, subproject and carrying task optional, read by the page when a command asks for them
(`provision-options.ts`) —, says the 409 under the form and, the creation done, opens the risk's
own estimate (`structure_id`) in the estimate grid, for a session that reads the estimate.
« Modify », in the detail, follows `update`, and the provision `update_provision`: unavailable, the
category, the subproject and the task show fixed and are not sent. Both commands wait, inactive,
until a write of their closed form is answered (defect no. 24 of `typescript.md`). The commands of
the detail (`RiskCommands`) share per risk the write under way and the most recent answer.
« Review » (`risk-review.tsx`, `review`) starts from the probability and the state the risk
carries — confirming it without changing anything produces a dated review (`reviewRisk`), which the
history shows at the re-read — and offers the states the contract lets one retain (identified,
dismissed); a dismissed risk whose category is no longer active
(`provision_cost_category_is_active`) asks for another one, among several active ones, on the
return to the identified state. « Delete the risk » (`risk-lifecycle.tsx`, `delete`) asks for a
confirmation, is unavailable for a cited risk (`risk_not_cited`) and, deleted, leaves the detail
through the address without the risk. « Declare occurred » (`declare_occurrence`) confirms, queues
the occurrence (202) and hands it to the tracking of background tasks (`Following`); it first reads
the report of the occurrence (`getRiskOccurrenceReport`, US-0680), presents it in the marks `+`,
`-`, `M` like that of a merge (`occurrence-report.tsx`), says the withdrawal of the provision and
the refusals, and confirms with the counters read; a stale version (412) offers to re-read it. A
failed task is not replayed from the tracking, which would confirm old counters: its entry says to
start again from the risk screen, where the command re-reads the report. An occurred risk lists
all its commands unavailable. The register paginates like every flat table (`limit`, `offset`,
`meta`): « Rows per page » and the pages under the grid (`ListPages`, `RISKS_LIST`), the totals
remaining those of all the retained risks. The label of a risk is a link out of the tabbing: the
grid follows the link of a cell that is not being entered on Enter (`grid-keyboard.ts`).

### The remaining-to-commit screen

The remaining-to-commit screen, `…/revisions/[r]/remaining` (`frontend/src/components/remaining/`,
`remaining.tsx` for the grid), reads its indicators in the revision of its route
(`getRemainingIndicators`, `revision_id`) — the total, the margin on the reference budget and the
gap to the previous review, absent rather than null without one, the totals by cost type and, by
subproject, the remaining to commit and the margin on its budget with the `Signal` of the zone the
server gives, and the risk coverage (`RiskCoverageSummary`) —, or says they are unavailable when
the API does not find them; and the dense grid, one more configuration, on the lines of the
started tasks only, unless the address also asks for the non-started ones (`progress`, under the
name and the form of the contract, which a link of its header writes). The budgeted amount, the
quantities and the re-estimated at the previous remaining to commit, then the current quantities
and re-estimated (WF-RAE-0040); the three amounts are computed columns there, the previous
quantities kept values, never entered; the quantities of a line are re-estimated one by one
through `setLineRemaining`, where the line says it accepts it (`remaining_entry`) and where its
node accepts the field — never from the progress of its task —, the `edit_remaining` command of
the structure read (`screen.commands`) setting Undo and Redo, and the grid, read-only when it does
not list it; it also filters by a work package or an order item of the whole work breakdown read,
like the planning and the estimate (`order_item_id`, `work_package_id`, restricting the grid
alone); the finish of a task shows there without being entered, and the overdue finish by a mark
of its own, which the server says (`finish_overdue`). The subprojects of the project
(`listSubprojects`, read with the banner, once per request) are read only where the structure
lists `edit_remaining` available, and refused they do not give the « Subproject » submenu; the
column and the submenu are those of the estimate, described with the context menu of the cells
(`choice-menu.tsx`). Its banner shows only the subproject, the only context parameter its readings
take, and says that it restricts only the grid, its indicators being those of the whole project
(`gridOnly` of `ContextBanner`, #459). The Kanban of task starts, FBS-4.5.3, is a leaf of the
function, `…/revisions/[r]/kanban`, where the header of the grid leads: all the non-started tasks,
the started and the completed ones with their date, as `listStartableTasks` renders them, each a
card, a non-started milestone whose predecessors are completed flagged to be completed
(`predecessors_completed`, a text and an icon); no percentage. The page cuts out the cards
(`kanban-cards.ts`: what the card shows and its gestures, never the whole node of a thousand
tasks) and reads the main structure of the revision (`listCostStructures`), where the gestures are
written. A card is chosen by click or by the arrows (up and down within the column, left and right
from one column to another; a single tab stop) and makes the gestures its task lists
(`available_commands`, never deduced from the nature of the task or its lines): through its menu,
which keeps the unavailable gestures with their conditions, by drag and drop onto a column, or on
the keyboard — Shift and right or left arrow carry the card to the neighbouring column, and to it
alone: a drag to a column further away has no key. The menu of the card, opened by Enter, offers
all the gestures the task lists: it is the complete keyboard equivalent of the drag (WF-IHM-0100).
The drag sets a type of its own (`application/x-waterfall-card`), not `text/plain`, which a text
field one drops into would insert. The gesture that leads to the state of the targeted column is
the one the card lists with that state (`progress`); without it, the card says so. A card that
asks for its date is not draggable, and no other request opens while it waits for it: the entry is
never lost in silence. Start and complete ask for the date of the event, today's proposed; « Enter
the remaining to commit » is a link to the remaining-to-commit grid, searched on the label of the
task (`remainingHref`). The answer of `setTaskProgress` replaces the card in the column of its new
state, as long as the reading that follows does not have the node at its version or a more recent
one (the counter of the node decides, `replaced`); the answered card lists no gesture before that
reading. The focus follows the card, a refusal is said on it (`OutcomeNotice`), and one write at a
time. The operation reads the revision in progress: on a marked revision, the screen says so and
asks for nothing.

### The actual costs screen

The actual costs screen, `…/revisions/[r]/actual-costs` (`frontend/src/components/costs/`), reads
those of the project — they are not versioned, the revision of the route is only the context of
the banner — page by page, as the server paginates them (`offset`, `listActualCosts`): the three
totals of the retained lines and the date of the last import, as the server renders them; the
filters by scope, by subproject — that of the reading context, `subproject_id` — and by period of
the documents, which write only the address, under the names of the contract, and bring back to
the first page; the dense grid, read-only (`cost-grid.tsx`), without search — the operation has
none: a configuration removes it by `searched: false` —, each line with its subproject named by
the server, its scope in words and each column kept from the file as a column, under the name the
file gives it, its values as imported (`passthrough.<colonne>`), each column sorted by the server
— the kept columns are those of all the retained lines, in the order the server names them
(`meta.passthrough_columns`, #414): the same from one page to the next —; and the import log,
paginated apart (`imports_offset`, `imports_limit`), with its « Rows per page » and its grid key
(`cost_imports`, `KeptListSize` of `grid/kept-list-size.tsx`, which records the size like a dense
grid: the log is not a grid). The imports of a project (`imports`) do the same. When the project
lists the exclusion of its lines (`exclude_cost_lines`), the document number of a line is a link
out of the tabbing, which the grid follows on Enter, to the same address naming the line
(`line`): its place in the tracked scope shows there (`CostLineScope`), with the command that
excludes it, on the reason entered, or reinstates it (`setActualCostTrackedScope`, WF-CRE-0040);
the write done, the page re-reads the line and the three totals, which the server holds (#291).
Filters the server refuses (422: a period that ends before it starts, a subproject the project
does not have) are said in place of the lines, the filters kept to be changed. A changed sort or
search brings every paginated list back to its first page (`sortHref`, `searchHref`). A page link,
like the label of a risk, starts from the last address requested (`usePendingLink`); when it reads
the costs otherwise than the page shown — a pending filter or sort —, it leads to their first
page.

### The reference data screens

The reference data screens (`frontend/src/app/reference/`, `frontend/src/components/reference/`,
US-0250) are outside any project, at the routes of their functions. The cost settings say the
currency of the installation and present the grid of hourly rates — one more configuration of the
dense grid (`rate-grid.tsx`), the third section of the screen, under the cost types and the
categories, one row per labour category, its state, one column per year of the whole grid,
whatever the page, whose header is the year itself (`GridColumn.heading`) —, searched, filtered by
state and on the bounds of the rate of a year (`RateFilterBar`, #545), sorted and paginated by the
server under the names of the contract (`search`, `is_active`, `rate_year`, `rate_min`,
`rate_max`, `sort_by`, `offset`, #509): each column sorts, the rate of a year by `rate.<année>`,
which the page accepts for any year `Year` takes (`RATE_SORTS`), before knowing those of the
response; its totals row says how many categories the server retains, and the currency. An
entered cell leaves alone through `setHourlyRate`, without a version for the first rate of a
year, with that of the rate read for a correction, and the answered rate takes its place. The
entry is offered only to a session that carries `cost_settings.write` (`platformOffer`), like the
addition of the column of a year the grid does not have (WF-REF-0060, #299): the contract has no
operation to create it — a year enters the grid through its first rate —, so that the column is
the grid's, empty, in its place among the years, until the entry of one of its cells writes that
first rate, and it withdraws as long as no rate is entered or being written there; a year already
present, or outside the bounds of `Year`, is refused in the page; the added column sorts like the
others, the server leaving the order of the code for a year without a rate. Above it, the cost
types then the cost categories, two dense grids (`cost-grids.tsx`, #510), sorted on each column,
searched, filtered — the types by kind (`kinds`, `ValuesFilter`) and by state, the categories by
cost type, offered among all those the session reads, and by state — and paginated by the server
— the three sections stack like those of the resource settings, in a page that scrolls (`Screen`
without `fill`, US-0570/L3, #1044), each grid capped at the window (`max-h-svh` of `DenseGrid`).
The resource settings present three dense grids (#301, #511, #533): the organisation, a tree grid
that neither sorts nor paginates, in the order of `listOrgNodes`, each node by its label indented
by its depth (`level`), which folds what is under it like the task grids (`GridTree.parent`,
`fold.tsx`), its code and its level, filtered by code (`code`), by level (`level`, offered among
those of the whole tree) and by state, the server rendering the retained nodes and their
ancestors, which a filter unfolds once; the roles, each by its label and its code (EP-14/L42r),
sorted by the server on each of their columns, searched by it on the label and the code, filtered
by code (`code`, like that of the nodes), by node (`org_node_id`, offered in the order of the
whole tree), by category (`cost_category_id`), by calendar (`calendar_id`) — each offered among
all those the session reads, read as a list of choices (#303), the categories absent when the API
refuses them — and by state, and paginated; the calendars, sorted on each of their columns, the
hours of each day included, searched, filtered by state and paginated, without a filter on the
hours of their days (WF-IHM-0130-A, #1047). The number columns are bounded (#545, WF-IHM-0130):
the monthly hours and the headcount of a role, the rate of a year of the rates grid — the year
chosen among those of the grid, written with its bounds (`rate_year`) —, under the convention of
the contract for every list, `<colonne>_min` and `<colonne>_max`, inclusive
(`docs/api/DECISIONS.md`). The filter is a component of the grid, reusable for the amounts of the
following lots (`RangeFilter` of `components/grid/range-filter.tsx`, `boundsHref` and
`readBounds` of `filters.ts`): one form per list, each bound entered as the language writes a
number (`parseDecimal`) and written as the contract writes it, bringing the list back to its first
page; an entry that is not a number, or an amount with more than two decimals, is said at its
field, which takes the focus, without asking anything. The server alone judges the bounds: the one
it refuses (422) — not a number of its type (`NUMBER_INVALID`), an upper bound under the lower,
which it names (`VALUE_OUT_OF_RANGE`), the year of the rate missing (`VALUE_REQUIRED`) — is said
at its field, which takes the focus (`refusedBounds`, `refusedSides`), and the list is not read
(`shownPage` of `address.ts`, `BoundsRefused`); the rest of the screen is. Each field is named by
its column and its side, both written next to it (« Hours a month, min », WCAG 2.5.3). The tree is
also bounded on the depth (`level_min`, `level_max`), next to the choice of a depth (`level`); the
rate is bounded only with a year the contract takes, failing which the page does not present its
bound. Each of the grids of the reference data is searched by the server, has its preferences
key, where its sort is kept, and writes its sort, its search, its filters and its page in the
address under its own names, those of the contract after its prefix (`org_`, `role_`,
`calendar_`, `type_`, `category_`: `role_search`, `role_sort_by`, `role_cost_category_id`,
`role_is_active`, `role_offset`; `prefixedAddress` of `query.ts`, `GridConfig.address`) — the
rates grid, that of the function, keeps the names of the contract —: the grids of a same screen
do not read one another, and the page asks the API under the names of the contract; the whole
tree is re-read when a search or a filter restricts it, for the filters of the roles. A sort, a
search or a filter bring their list back to its first page; a page link starts from the last
address requested, and leads to the first page when it reads the list otherwise than the one
shown — the sort of another list of the screen not counting there (`ListPages` of
`components/grid/list-pages.tsx`, named after its list, the only « same list » rule of
`readingOf`); the totals row says how many the server retains (`meta.total`). The duration units
follow: three constants, which the command « Modify the units of duration » — offered to whoever
carries `resource_settings.write`, like the calendars — opens as a form (`DurationUnitSettings` of
`settings-forms.tsx`, `setDurationUnits`), in decimals of the language; the refusal (422) is said
at the field, the stale version (412) offers to re-read, the answer takes the place of the values
read, and a sentence under the fields says that the change holds for all projects, the plannings
of the revisions in progress being recomputed and a marked revision keeping its hours
(WF-PLA-0160, WF-REF-0130, #1049). The risk settings present the bounds of the matrix and the zone
of each cell, placed by its rank in the order of the contract, the indicator settings the
thresholds of the indices and the delay between two reviews: matrices of fixed size, which remain
simple tables, without sort or filter (decision of the author of 2026-10-08, #508). An attached
object is named by the label the server resolves at reading time, active or deactivated — never
by matching lists in the front; a section is named by `aria-label` (#251).

The lists of the reference data read only the active objects, and the deactivated ones too when
the address asks for it (`include_inactive`, WF-REF-0150, #300), under the name of the contract,
which the header of the screen writes or lifts by a link (`InactiveSwitch`), which brings each
paginated list back to its first page — only for a session that carries the read permission of
their part of the reference data, without which the contract refuses it (403, `inactiveQuery` of
`address.ts`), like the lists of the estimate (#351). The filter by state (`is_active`,
`StateFilter`) prevails over it: all states, the active only, or the deactivated only, offered to
the same session only (`stateOf`). A deactivated object is said there by a mark and a word, and is
reactivated there as the server lists its command (`available_commands`, #532, WF-IHM-0090) — the
server lists it only for whoever can modify that part, and the front deduces nothing from it:
available, through the activation command of its nature (`setActivation`, a server action, from
the version read), then the page re-reads its lists; unavailable — a node under a deactivated
parent, a role under a deactivated node (WF-REF-0080) —, presented `aria-disabled`, described by
its conditions, and a press says them in the region of the list without asking anything, like the
deletion of a role in use (#515); absent, nothing. An object carries only the command that changes
its state, `deactivate` on an active object, `reactivate` on a deactivated one, both through the
same cell (`StateCell` of `commands.tsx`, EP-02/L43, below); the deactivation of the default
calendar is unavailable (WF-REF-0120). The refusal of the server — the conflict (409), which names
the node to reactivate first from the row that knows it, or the stale version (412), with the
offer to re-read — is said above the list (`Reactivations`), which a grid cell has no room to
say, until its notice is closed — a refusal arriving while another is said is added to it,
without replacing it, except that of the same command on the same object, which takes its place; a
success after it does not erase it, and the focus returns to the control that wrote when the
refusal names one (`back`, a cell of the permissions matrix), otherwise to the active cell of the
grid, or to the list —, and only as long as the list reads as at the moment of the command: the
parameters it reads (`listReads`), the sort of another list of the screen not counting there. In a
grid, the command is out of the tabbing, and Enter on its cell presses it (`CELL_COMMAND`,
`grid-keyboard.ts`). The fake back ignoring the filters, the pages and `include_inactive`, and
keeping nothing, the tests test what the screen asks for; the service will honour it in EP-05.

### Cost settings: types and categories

The cost settings offer the write commands of the cost types and the categories (EP-02/L43a,
decision of the author of 2026-10-08, #512; `commands.tsx`, `reference-form.tsx`, `cost-form.tsx`),
to project the layout and to test the contract of each write; those of the resources theirs
(EP-02/L43b, further down), through the same parts. To a session that carries
`cost_settings.write` (`platformOffer`), each list offers « New nature » or « New category » next
to its title — empty list included —, and each row « Modify », in a column of its own; the state
of the row carries the deactivation or the reactivation as the object lists it
(`available_commands`, `StateCell`), and presents it unavailable with its conditions when it is —
the last cost type of the provision-for-risks kind and its last category are deactivated like the
others since EP-14/L42p, which removes the rule of #578; no command deletes (WF-REF-0010,
WF-DAT-0080). Any other session sees none of them. Creation and modification open a dialog
(`ReferenceForm`, `ui/dialog.tsx`), which each list renders through the one of its nature
(`CostDialog`, `useListForm`): the code, the label and the kind of a cost type, chosen among the
three of the contract; the code, the label, the cost type — among the active ones, and that of
the modified category, marked deactivated — and the accounting code of a category, required, from
one to twenty characters (WF-REF-0040, decision of the author of 2026-10-09). What a modification
changes follows the commands of the object (EP-02/L42g, WF-IHM-0090): the kind of a cost type is
offered only if it lists `change_kind` available, and otherwise presents itself frozen, read-only
(`control: "fixed"` of a `FormField`), its conditions said under it (`note`) — a category in use
(`cost_type_unused`) —, the description of the dialog saying so too; a category is offered a cost
type of another kind only if it lists `change_cost_type` available, and otherwise the cost types
of its kind alone, its conditions said under the choice — in use, carrying rates (#577), attached
to a role (EP-14/L42r); the refusal of the server of a change of kind, the condition lifted since
the reading, names the roles involved, by their label and their code, to attach first to another
labour category — of another cost type, for a cost type — (`params.resource_roles`,
`problemMessage`, WF-IHM-0090), which the costs screen does not read. The kind is compared by the
`kind` of each cost type, deactivated ones included: for a session that writes, the page reads all
the cost types with `include_inactive=true` (`every` of `CostDialog`), a whole reading distinct
from the choices of the filter, which it does not do when those already include the deactivated
ones; a category under a deactivated cost type is thus offered the active cost types of its kind,
and its deactivated cost type is named by its code, which that reading gives. A cost type that no
reading gives — a session that writes without being able to read the deactivated ones, to which
the contract would refuse `include_inactive` (403), and for which the page does not ask for it —
leaves the category its only cost type, and the note says so apart (« The type of the deactivated
nature cannot be read: it alone is offered. »). `costs/page.test.tsx` tests what the page passes to
the form, the cost types served by `cost_types_with_inactive`, the reading with the deactivated
ones, which holds for it only. A node whose code is taken is named likewise, from the tree or the
list, otherwise by the label the refusal gives (`OrgNodeDialog`). The form refuses at its field
what is missing, or a number that is not one in the language of the reader (`parseDecimal`),
before any request, and the field takes the focus; the server judges the rest: a refusal per field
(422, `fields[]`, convention #293) is said at the field it designates, by the sentence of its code
and its parameters — `problemMessage` of a `FieldProblem`, the first refused field taking the
focus —, like a value already carried (409 `ALREADY_EXISTS`, `fields[]`), which names the object
that carries it (`fields[].params.conflicting_object_id`) by its code and its label when the list
shows it (`names` of `ReferenceForm`), generically otherwise; the decoder also draws the object of
the refusal from it (`conflictingObjectId`) when the envelope does not name one. Any other refusal
is said under the form (`OutcomeNotice`), which stays open — a state that forbids the write (409
`STATE_FORBIDS_OPERATION`) with its condition, the stale version (412) with the offer to re-read
the page; a refusal per field the form does not show stays there alone, without repeating what is
said at the fields. The submit button says the write under way; closed during the wait, the dialog
silences nothing: the success is said in the region of the list, the refusal above it, on the
reading it started from. Closed, it gives the focus back to the cell of the row — the grid is a
single stop — or to the creation command. `problemMessage` also reads the parameters of the
refusals per field of an envelope: the minimum of a refused rate is said with the refusal of the
cell, written in the language of the reader (« Minimum value: 0.01. »). Every answered write
re-reads the page (`refresh`): the cost types are what the categories filter and attach by, the
labour categories the rows of the rates grid, and a choice that would still offer a deactivated
cost type would be a command the server would refuse (WF-REF-0010); a write also changes the
commands of other objects — the attachment of a category the kind of the old and of the new cost
type (#577) —, which its answer does not carry. A rate re-reads the page only at its first entry:
the category that carries rates no longer attaches to a cost type of another kind
(`cost_category_unrated`); a first entry refused as a second rate of the year (409
`ALREADY_EXISTS`) also re-reads the page, and the cell shows the rate of the year with its
version, which the next entry corrects; a correction changes no command. That re-read, at the
same address, abandons nothing of the rates grid: a rate that left before it stays pending, the
refusal says the rest, and an answered rate, before or after it, keeps its cell as long as it is
more recent than the re-read cell, by the `lock_version` of the rate — the answer is the change of
a cell, found by its year among those of the re-read row and laid back on it (`RowPart.versioned`,
`rate-cells.ts`), a row of the grid having no counter of its own; elsewhere, an answer is judged
as a block by the counter of what it wrote (`GridConfig.fresher`, the `lock_version` of a node):
more recent than the re-read, it keeps everything it rendered, the recomputed summary tasks and
the totals included, a more recent answer always prevailing over an older one for a same row;
caught up, it yields everything; where the counter says nothing — same version, row without a
counter, fake back —, each value stays as long as the re-read reads its row, or its totals, as
before. Only a reading at another address — a sort, a search, a filter, a page of the grid —
abandons the answers under way; a reading that renders the same rows in the same order, another
list of the screen sorted or the address rewritten by `history.replaceState`, is the same one
(`cell-writes.ts`, defect no. 22). This last rule assumes that the content of a row does not
depend on the address: the day a grid computes its rows from a parameter of the address — a
currency, a value date —, two readings with the same rows are no longer the same one, and the
rule becomes false. An answered modification or activation replaces its row by what the server
renders, as long as the answer is more recent than the row read (`lock_version`, `useAnswered`) —
against the fake back, which keeps nothing, it therefore survives the re-reads —; a creation adds
no row, the re-read page files it where the server retains it. What a write did is said in the
region of its list (« “Disbursement” deactivated. »); the refusal of an activation, above the list
like that of a reactivation (`useListReport`). The fake back keeping nothing, the screen says so
under its header, for whoever writes — a written row remaining shown as the server rendered it as
long as the screen stays open — (`MockupNotice`, `components/shell/mockup-notice.tsx`, to be taken
up by each screen of the mockup whose commands write, removed when the screen is plugged into the
service of its epic). The entry of a rate remains that of the grid.

The mapping of the actual costs extraction (US-0620/L2, WF-REF-0190, FBS-3.1.3) has its page,
`/reference/costs/actual-cost-mapping`, which the header of the cost settings offers through
`leafOf("FBS-3.1.3")` (`components/reference/actual-cost-mapping.tsx`): the accepted headings of
each of the five columns read and the kept columns, as editable lists, and a bar that says the
required columns without a heading from the server's `is_complete` and `missing_columns`, never
recomputed. Under `cost_settings.write`, a single form replaces the whole mapping with the
`lock_version` read (`setActualCostMapping`); under `cost_settings.read` alone, the lists are read
without a command. The server alone judges: a 422 refusal is said at the field by its pointer
(`/columns/<rang>/labels/<rang>`, `/kept_columns/<rang>`), the duplicate (`DUPLICATE_COLUMN_LABEL`)
naming the heading it duplicates (`params.duplicate_of`); the stale version (412) is said under
the form, with the offer to re-read.

### Resource settings: organisation, roles and calendars

The resource settings likewise offer the commands of the organisation, the roles and the
calendars (EP-02/L43b, #512; `resource-commands.tsx`, `calendar-default.tsx`), to a session that
carries `resource_settings.write`: « New node », « New role », « New calendar », the modification
of each row, the deactivation or the reactivation as the object lists it — a node with its
descendants, which the answer replaces in the tree (WF-REF-0080), the roles it deactivates with it
being those of the other list, which the re-read page shows. A node is written by its code, its
label and its parent — null for a root, sent at modification as at creation (`OrgNodeUpdate`) —,
chosen in the order of the tree, each node indented by its depth (`treeLabel`): among the active
nodes only, whether the node is active or deactivated (WF-REF-0070, EP-14/L43g), never under
itself nor under one of its descendants, which it takes along; its parent is always offered, from
`parent_id` and `parent_label`, marked deactivated when it is, and the list shows it chosen — the
contract refuses a deactivated parent only if the modification changes it; deactivated, it keeps
its depth when the node above it is offered, or when it is a root, and then its place — in the
tree read, the front reordering nothing, or under its own parent when the row of the list names
it —; at the end without indentation otherwise. A role is written by its code, unique,
deactivated ones included (EP-14/L42r), its label, its node, a labour category and its calendar —
among the active ones, that of the modified role marked deactivated when it is (WF-REF-0090),
named without a mark when the list is not read, for lack of knowing whether it is, or when all the
categories read say it active, a category whose cost type has left labour (`read` of `offered`,
#714): a safeguard only, the contract forbidding that case since EP-14/L42r
(`docs/api/DECISIONS.md`, the mention of L42r in the section of L42j) — and its capacity, hours a
month and headcount, entered in the language of the reader (WF-REF-0100); its node is fixed at
creation, and its modification names it without offering it: a role is recreated under another
node (§3.4.4.2.1). The labour category is recognised by the kind of its cost type, which each
category says (`cost_type_kind`, `labourOf` of `kinds.ts`, EP-14/L43g): the page does not read the
cost types for that. A session to which the API refuses the categories can choose none: « New
role » is not offered to it (WF-IHM-0090), and the modification names the category of the role as
its row names it. A taken code is said at the field, the role that carries it named by the label
the refusal gives (`conflicting_object_label`), the list read without the deactivated ones
possibly not showing it. The modification of an object answered for another object is a failure
of the service (`INTERNAL_ERROR`), said under the form like the answer of a cell for another row. A
calendar is written by its label and its seven hour values, from Monday to Sunday, nothing else
(WF-REF-0110). A calendar is designated as default from its row as it lists the command
(`CalendarCommand.set_default`, `setDefaultCalendar`, WF-REF-0120, EP-14/L43g), from the version
read, the re-read page showing the previous one without the designation: absent — on the default
calendar, or for a session that does not modify —, nothing, the front deducing nothing from the
state of the row; unavailable for a deactivated calendar, presented `aria-disabled`, described by
its condition (`calendar_active`), and a press says it in the region of the list without asking
anything (`UnavailableCellCommand`); the refusal of the server — the calendar deactivated in the
meantime (409), the stale version (412), with the offer to re-read — is said above the list. A
refusal per field is said at the field (`ReferenceForm`): an unknown reference
(`UNKNOWN_ORG_NODE`, `UNKNOWN_COST_CATEGORY`, `UNKNOWN_CALENDAR`), a node placed under itself or
one of its descendants (`ORG_NODE_CYCLE`), a category outside labour (`LABOUR_CATEGORY_REQUIRED`),
a parent, a node or an attachment deactivated in the meantime (`INACTIVE_REFERENCE_OBJECT`), hours
outside 0 to 24 or a negative capacity, with the bound crossed (`VALUE_OUT_OF_RANGE`); the label
already carried by a calendar, deactivated ones included, names its carrier from the page, by its
identifier, generically otherwise; the rest as for the costs, the stale version under the form
with the offer to re-read; the screen says that the fake back keeps nothing (`MockupNotice`). A
write that would leave a task without a working hour — a calendar modified or designated as
default, a role modified — is refused (`TASK_WITHOUT_WORKING_HOURS`, « A task would have no working
hour left in the week. ») by saying why and by naming each project involved by its label and its
code, by its label alone without a code (`params.projects`, WF-PLA-0010), up to five in the
sentence, as a list outside the alert beyond, like the lines of a subproject. The cause is that of
`resource_role_ids`: the roles whose calendars overlap on no day, which the refusal gives only by
their identifiers — the page, for a session that writes, reads all the roles, deactivated ones
included as far as it can (`readEveryRole`), and lends them to each notice of their two lists
(`RoleNames`, `KnownNames` of `outcome-notice.tsx`), each by its label and its code, and the cause
is said without a name when it has read none —; no role given, the tasks without a labour line,
on the default calendar emptied or designated.

### Risk and indicator settings

The risk settings and the indicator settings are each modified in a form (EP-14/L43e, #512;
`settings-forms.tsx`), offered by « Modify the risk matrix » to a session that carries
`risk_settings.write`, by « Modify the thresholds and the delay » to a session that carries
`indicator_settings.write` (`platformOffer`); any other session reads the tables alone, without a
notice of the mockup. The one enters the six bounds, as percentages (`editablePercent`,
`percentRatio`), and the sixteen zones, one choice per cell; the other the four thresholds, as
values of the index, and the delay, in whole weeks (`control: "whole"`, a whole number, sign
included, its bounds left to the server, judged at the field with the others, said by the text of
the field's own, `invalid`). Each screen follows its single permission: a session that carries
one without the other reads the other screen without a command or a notice. Each sends through
`updateReferenceSettings` the single sub-object of its screen and the version read
(`RiskMatrixWrite`, `IndicatorWrite`), never a field of the other screen, which another permission
guards; neither the currency (WF-REF-0140) nor the language of the installation, which belongs to
EP-03, are offered there. The form of the reference data lays side by side, under a legend, the
fields that go together (`group` of a `FormField`, a `fieldset` that folds onto two columns in a
narrow window): the bounds of an axis, the zones of a probability level, the two thresholds of an
index, each field named by the legend of its group then by its label (`aria-labelledby`), which
the groups repeat; and it judges, in the same submission as the fields, on those that passed, the
rules that bind fields to one another (`rules`), before any request — a refused field has no
value, which a rule leaves unjudged, and its own refusal prevails; everything refused is said at
once (EP-14/L52) —: each bound that is not strictly above the previous one, at its rank
(`BOUNDS_NOT_ORDERED`), each alert threshold that is not below its watch threshold
(`THRESHOLD_NOT_BELOW_WATCH`), said at the field the server would designate, the decimals compared
without a float (`compareDecimals`). The refusal of the server is said likewise: per field at the
field, the missing permission (403) and the stale version (412, the two screens sharing the
counter) under the form. The answer takes the place of the settings read as long as it is more
recent than them, the page re-read, like the settings of the project, and closes only the dialog
it started from, never a dialog reopened since; the command that opens it waits, inactive, for the
answer of a write of a closed dialog (#661); against the fake back, which answers with the first
example of the operation — the thresholds written —, the matrix shown remains the one from
before.

### The administration screens

The administration screens (`frontend/src/app/admin/`, `frontend/src/app/system/`,
`frontend/src/components/admin/`, US-0250) are outside the project too, and read-only except the
one of the roles, wired to the service (below): the accounts, deactivated ones included by default
(`include_inactive`), each with its roles and its node named by the server, on the dense grid
(#514, `admin-grids.tsx`), sorted on every column, searched, filtered by origin (`origins`,
`ValuesFilter`), by organisation node (`org_node_id`, offered in the order of the tree,
`OrgNodeFilter`), by access role (`access_role_ids`, the roles that `listAccessRoles` returns, none
to a session that does not read them; all of them chosen still filter, an account without a role
being kept by none, `exhaustive: false`, EP-02/L42f) and by state, a single choice (`is_active`) —
all, the active ones only, the deactivated ones only —, which says what the grid shows: the page
always asks for the deactivated ones too (`include_inactive=true`, the contract hiding them by
default), an address from before that hid them (`include_inactive=false`) reads as « Active
accounts » (`readAccountState`), and any choice lifts that old parameter (`lifts` of
`ChoiceFilter`) — and paginated by the server, under the names of the contract — a sort, a search
or a filter bringing back to the first page —, the totals row saying how many the server keeps
(`meta.total`), the screen filling the window; the search covers the surname, the first name, the
address and the display name, regardless of case and accents, like every search of the contract.
The access roles are on the dense grid too (#515), sorted on every column, searched and filtered by
the server — their nature (`is_predefined`, `ChoiceFilter`), their holders between two inclusive
bounds (`holder_count_min`, `holder_count_max`, `RangeFilter` of the `count` form, an integer from
zero; a refused bound said at its field, the list not loaded) —, without pagination — §4.6.2 counts
no role, three are predefined, and the contract does not paginate them —, and the permission matrix
shows the roles the table keeps, in its order (US-0380) — one row per permission in the order of
the catalogue, the consecutive permissions of the same second-level function, or of the same nature
outside a function, grouped under a group header (`scope="rowgroup"`) that names the function —
never by its FBS code, an internal key no screen shows (author's decision of 2026-10-08, #515) —,
one column per role, granted or not said by a word; the state of the system; the backups and their
schedule, whose commands are wired to the contract (EP-02/L43c, below). The tables of the accounts
and of the roles end on their audit columns (#936, `audit-columns.tsx`): « Created », « Created
by », « Last modified », « Last modified by », each sorted by the server under the name of its field
(`created_at`, `created_by`…), an instant in local time (`LocalTime`), an author by the name the
row keeps of the account — deactivated since, still named; anonymised, the neutral label — or the
platform by its own label (`ActorCell`). Each can be filtered (`audit-address.ts`,
`audit-filters.tsx`): a period of local days per date column (`PeriodFilter` of the `day` form,
under `created_at_from` and `created_at_to`, `updated_at_from` and `updated_at_to`), a refused end
said at its field, the list not loaded; an author per author column (`AuthorFilter`), a single
choice that writes an account (`created_by_user_id`) or a kind of author — any account whatsoever,
or the platform (`created_by_kind`) —, each choice lifting the parameter of the others (`name` of a
`Choice` of `ChoiceFilter`). The contract has no list of the authors: the roles offer those of the
unfiltered list, loaded again separately when the grid restricts it; the accounts, those of the
page shown, and those that a search of the accounts finds (`findAccounts`, `listUsers` searched,
twenty at most). These filters are kept with the settings of the two grids, like the others. The
search and the filters of the roles table are kept with the settings of its grid
(`GridConfig.filters`, `kept-filters.ts`, under `filters` of `GridPreferences`, as the address
writes them): saved as soon as the page shows others than those kept — a lifted loading included —,
and found again only on an address that says nothing of the grid, neither sort, nor search, nor
filter, which the page, on the server and before any loading, redirects to the one of the kept
filters (`restoredAddress`, `kept-address.ts`), as it takes the kept sort when the address says
nothing of it — wherever one comes from, the link of the sidebar followed from the screen included.
Lifting the last filter is said in the address, the search written empty (`search=`, `spokenHref`,
which the `PendingAddress` of a screen that names what its grid keeps sets), as a lifted sort
writes `sort_by` empty: the preference empties, and the page does not find the kept filters again
(#836). The roles screen is wired to the service (US-0380/L2, #380): to a session that carries
`access_roles.write`, the table creates a role inline, by its label alone (`role-commands.tsx`),
renames it in its cell — the grid's input, written by `updateAccessRole` with the permissions of
the role — and deletes it from its row, after a confirmation that names the role and says the
deletion is definitive (`AlertDialog`, outside the grid, Escape abandoning it) — a logical deletion
(#456), which nothing restores, a predefined role included —, unavailable, `aria-disabled` and
described by its condition, as long as an account carries the role (`ACCESS_ROLE_IN_USE`,
WF-ADM-0090); the matrix is the place where permissions are changed, one checkbox per permission
and per role (`permission-matrix.tsx`), which writes the whole role, its permissions in the order of
the catalogue, the other boxes of the role waiting for the answer. The table and the matrix read a
single source of the most recently answered role by its `lock_version` (`RoleAnswers`,
`role-answers.tsx`): a rename then a box ticked before the reload, or the reverse, starts from the
answered version, and a reload older than the answer does not undo it; the header of the column of
a renamed role and the name of each of its boxes take the answered label too (`RoleLabel`,
`PermissionCell`), without waiting for the reload (#976). What a command of the table does is said
in its region, named « Commands of the access roles »; a refusal, by the catalogue of error codes
above the table or the matrix, on the loading it started from (`Reactivations`) — the last
administrator (`LAST_ADMINISTRATOR`), the stale version with the offer to reload —, the focus given
back, the refusal closed, to the box that wrote; a label refused by the server, or blank, refused
outright like the grid's input (`parsedEntry`), is said at its field; every answered write reloads
the page. For the accounts (US-0360, #379), the table is its own input, to a session that carries
`users.write` (`platformOffer`): the surname and the first name of a local account in their cells
(`updateUser`), those of a directory or provider account staying read-only (WF-ADM-0050); the state
on a switch, its word beside it (`setUserActivation`); the roles in a multiple-choice list of the
roles of the installation, whatever the attachment (`setUserAccessRoles`, `user-cells.tsx`) — each
as the account lists its command (`User.available_commands`): an absent command is not presented,
an unavailable one is, with its condition, and a click says it without launching it. Deactivating
the last active account that carries the permissions to change the accounts and the roles is
unavailable, `last_administrator` missing (WF-ADM-0120, #540) — the front could not find it on its
own, the list being paginated; assigning its roles stays available, the server judging the roles
sent, and refusing by `LAST_ADMINISTRATOR` those that would take these permissions away from it — a
refusal said like any other. The password setup link of a local account
(`createPasswordSetupLink`) is handed over in a dialog, whole and read-only, with the time at which
it stops being valid, never loaded again; unavailable for a deactivated account
(`is_active_account`), absent from an account that is not local or that is anonymised. « Create a
local account », at the head of the table, opens the dialog of the surname, the first name and the
address (`user-dialogs.tsx`): a blank field is refused at its field outright, an address already
carried said at its field; when no invitation has left (`invitation_sent` false), the created
account says so and offers its setup link at once (#816). The « Anonymisation » column carries the
`anonymize` command of a deactivated account (`anonymizeUser`), after a confirmation that names the
account and says the action is irreversible (`AlertDialog`, like the deletion of a role); an
anonymised account is named by the neutral label of the catalogue, and its surname and first name
cannot be entered, even if its origin is local (WF-ADM-0060). No deletion (WF-ADM-0060). As for the
roles, a single source of the most recently answered account by its `lock_version`
(`UserCommands`, `user-commands.tsx`): the next write of a row, whatever its cell, starts from its
version. The writes of a row go one after the other: a name entered while another write of its row
is under way waits for its answer and starts from the version it answered, and the switch, the
roles and the anonymisation of the row mark themselves busy and unavailable (`aria-busy`,
`aria-disabled`) as long as a write is under way there — the anonymisation also as long as a
requested reactivation has not answered. What a write does — a rename included — is said in the
« Commands of the accounts » region; a refusal of the switch, of the roles or of the anonymisation,
above the table, on the loading it started from (`Reactivations`), that of a name, at its cell. The
search and the filters are kept with the settings of the grid and found again when the address says
nothing of the table (`USER_KEPT`), as for the roles. Without the permission, nothing is written
and no command is presented. Above the table, the reading of the accounts of the identity provider
(US-0370, WF-ADM-0070, `identity-sync.tsx`) shows the report of the last completed reading
(`getLatestIdentitySync`), or says that none has succeeded yet (404): its accounts created,
updated, deactivated, those whose identity it restored in the provider, the local accounts it
removes from it, and, on request, what it left as is, each with the reason from the catalogue — an
account named as it reads on consultation, under the neutral label if anonymised since
(`useAccountNaming`, `AnonymizedName`); a person of the provider by their name and their identifier
there (#918); the one whose address an account carries (`ALREADY_EXISTS`) by their identifier and
that account, as it reads, or by their identifier alone when none carried it any more (#920). To a
session that carries `users.write`, « Read the accounts » (`startIdentitySync`) hands back control
as soon as the task is queued and entrusts it to the tracking, which announces it completed and
offers to reload the screen, without ever reloading it on its own. A list the server paginates —
accounts, backups — says how many it holds and leads to the neighbouring pages by `offset`
(`ListPages`, for the accounts as for the backups), the other parameters of the address kept,
without ever showing a page for the whole; it only says it is empty if it holds nothing
(`meta.total`) and nothing restricts it, and a page requested beyond its end says so and brings
back to the last one — a single rule for all paginated lists, `pageOffsets` of
`frontend/src/navigation/pages.ts` (#317). The time of a scheduled backup is displayed as is, in
UTC, as the contract gives it: a time of day has no date from which to derive the offset of a time
zone with daylight saving. Its form enters it the same way, and says beside it the workstation time
it gives in the week it is open — the time alone for a daily schedule, the local day too for a
weekly one, which may be the day before or the day after the universal day (`localTimeOfDay` of
`format.ts`, in the browser): nothing is converted on sending.

### The backups screen

The backups screen (FBS-1.4, `/admin/backups`, EP-02/L43c, #519, EP-14/L43f, EP-14/L43d) presents
their schedule (`backup-schedule.tsx`) and a page of their list on the dense grid
(`backup-columns.tsx`, `backup-grid.tsx`, preferences under the `backups` key): the date, in local
time, the size, the verification, the trigger and the retention, in the order of the server, the
totals row saying how many it keeps (`meta.total`). The server sorts every column in both
directions (WF-IHM-0060), the most recent first when the address and the account say nothing, and
the sort is never lifted, like the one of the log; it filters on every column (WF-IHM-0130,
`backup-address.ts`), under the names of the contract: the period of the capture, two days of the
reader turned into instants, `from` included and `to` excluded, like the home page (`PeriodFilter`,
`day`); the trigger and the verification, by their values (`origins`, `verifications`,
`ValuesFilter`); the retention, by a choice (`is_retained`, `ChoiceFilter`); the size, by its two
bounds in bytes, inclusive (`size_bytes_min`, `size_bytes_max`, `RangeFilter`, kind `bytes`: an
integer that has more digits than a count). A filtered list never says it is empty, and a bound
that the server refuses (422) — an end before the start, a maximum below the minimum — leaves the
list not loaded, the filters kept, the bound said at its field. « Back up now », in the head of the
list, empty list included — a background task handed to the tracking with its command —, follows
the `backups.write` permission (WF-ADM-0100, `platformOffer`); the other commands are those that
each backup lists (`Backup.available_commands`, WF-IHM-0090, `backup-commands.tsx`), the front
deducing nothing from the session nor from the state of the backup: « Keep » or « Stop keeping »,
whichever of the two changes its marking, in the retention column; « Download » and « Restore »,
each in its column as soon as a backup of the page lists it — the server lists the marking only
under `backups.write`, the download only under `backups.read` and `backups.write` (author's decision
of 2026-10-10, #705, which replaces the one of 2026-10-09, #588), the restoration only under
`platform_restore` —, and none deletes. An absent command is not presented; an unavailable one is,
`aria-disabled` and described by the condition it lacks (`enums.CommandCondition`) —
`backup_verified` for the download and the restoration of an unverified backup,
`no_backup_running` for the restoration while a backup is running, `no_restore_running` for the
marking and the restoration while a restoration is running —, and a click says it in the head of
the list without asking anything, like the activations of the reference data. The head of the list
says what the last command did as soon as a command is offered. A backup having no counter, the
answer of a marking stays shown as long as each reload reads the backup as the previous one; a
reload that changed it wins for good, and an unmarking by a third party that the reload does not
show stays invisible (#588). The download is a link to the route
`/admin/backups/[backupId]/content`, which relays `downloadBackup` as a stream like the result of a
task (`src/api/relay.ts`, common to both routes): bytes, the only type the contract declares, under
the name the API gives (`Content-Disposition`, which the contract requires: `waterfall-backup-`,
the instant of the backup and the extension of its archive), with its length when the body arrives
without `Content-Encoding` — any other type, or a file without a name, returns the error of a bad
gateway (502). A refusal — 403, 404 without distinction (WF-ADM-0110), 409 of an unverified backup,
502, the API unreachable — sends back to the backups screen, its page and its filters kept, the
address naming the backup and the refusal (`refused_backup`, `refusal`, the parameter names of
`result-refusal.ts`): the screen says it above the list until its notice is closed — the download
named, the backup by its date when the page carries it —, and the notice, rendered with the page,
takes the focus on mount, without which no screen reader would announce it; the address is
rendered without the refusal once the page is revealed (`afterReveal`), the notice closed or not.
« Restore » opens a dialog (`restore-dialog.tsx`) that states the date of the backup and its
verification, the loss without return of what has been entered since, the disconnection of the
users and the entry in the audit log (WF-ADM-0160, WF-SEC-0030); the button is only enabled once
the identifier of the backup is entered, regardless of case, and the request states the date said
(`acknowledged_backup_taken_at`). During the request, neither Escape, nor a click outside, nor
« Cancel » close the dialog: a refusal is said there — a state that forbids it (409), the condition
named like any refusal; a confirmed date that is not the one of the backup (400,
`CONFIRMATION_REQUIRED`, EP-03/US-0440/L2), said at the date the dialog states, the list loaded no
longer being the one of the backup, and the page reloaded —, and nothing leaves that one believes
abandoned. Once queued, the restoration gives way to the screen of its maintenance
(`restoration.tsx`, `maintenance.tsx`, US-0440), which follows its task as long as the platform
serves, then the liveness probe, and says the disconnection of the users, then the end; the
tracking of the shell does not receive it: a restoration is only relaunched from this confirmation.
The refusal of a command of the list is said above it (`Reactivations`), the condition named for a
409; the screen says that the fake back keeps nothing (`MockupNotice`) as soon as a command is
offered. The restoration from a file goes through the chunked upload of EP-03 (#350,
`completeChunkedUpload`), offered to whoever carries `platform_restore` under the list, whose date
read in the manifest is the one the confirmation names: the same dialog, the identifier of the
upload entered, its verification said pending — its restoration does it (EP-14/L42o). The schedule
and the external locations, which the service does not serve yet (404), are left aside without
taking the list down.

The schedule is changed, to a session that carries `backups.write` (`platformOffer`), in the form
of the reference data (`ReferenceForm`), which sends it back **whole** from the version it opened on
(`setBackupSchedule` is a `PUT`): enabled or suspended, the frequency and the time in UTC (a `time`
field: a half-entered time, which its field renders empty, `validity.badInput`, is refused before
any call by the sentence proper to its field, `invalid`, never sent as « no time ») — required of
an enabled schedule only, the contract not requiring them of a suspended one —, the day — required
of a weekly schedule, null for a daily one —, the number of backups retained, an integer whose
bounds the server judges, sign included; a field required according to the draft says so
(`required` of a `FormField`, a function of the draft, which also gives `aria-required`, #678);
then the external copy, offered when the installation declares a location or when the schedule
sets one: the location, chosen among those the page reads for this session only
(`listExternalBackupLocations`) by its name and its nature, its description under the field, never
a secret nor an address — a set location that the installation no longer declares stays offered by
its name, refused at the field before sending (`UNKNOWN_EXTERNAL_BACKUP_LOCATION`) rather than
removed silently —, « No copy » removing it; the relative folder; the number of copies, at least
that of the backups retained (WF-EXP-0050), checked before sending and said at the field with that
minimum, as the server would say it — for a retention within its bounds, from 1 to 365
(`RETENTION`), the rest falling back to the server, which then gives the minimum of copies as 1 —;
the copy enabled or suspended.
The rules between fields go through the `rules` of the form, a note that follows the input by a
function of the draft (`note`), and what follows the fields without being one through `after`:
« Test the location » (`testExternalBackupLocation`), offered for a location that the installation
declares, which says the location tested, the instant of the test in local time, the folder or the
root, and the success or the reason of the failure (`enums.ExternalBackupFailure`) in an announced
region; a refused folder (422, `/path`) is said under the button by the sentence of its own code;
only the answer of the last test requested is said, as long as the folder entered is the one it
tested, and another location chosen drops the test under way. The answer of a save replaces the
schedule displayed as long as its `lock_version` is more recent than the loading, the page
reloaded, and only closes the open dialog it started from (a counter of openings, like the settings
of the reference data), the command waiting, inactive, for the answer of a write of a closed dialog
(#661, #678); a refusal per field (422: unknown location, invalid path, retention too short) is
said at the field, any other under the form, the stale version (412) with the offer to reload.

### The audit log

The audit log (FBS-1.5, WF-SEC-0030, `/admin/audit-log`, `frontend/src/components/audit/`,
#517) is an administration screen of its own; the « Last operations » table of the state of the
system, three facts of the platform (WF-ADM-0130), stays as it is. It is a read-only function,
which only has its permission to consult (WF-ADM-0100): `FunctionPermission` names every function
by its permission to consult, and `WritableFunction` those that also have the permission to
change, the only ones `platformOffer` accepts. The screen is guarded by `audit_log.read`, not found
without it like an address that leads nowhere (WF-ADM-0110). It presents a page of the entries of
`listAuditEvents` on the dense grid, read-only (`audit-columns.tsx`, preferences under the
`audit_log` key): the date, in local time, the author, the action and, under it, what it did to its
object — composed by the front in the language of the reader from the codes and the parameters the
entry keeps (`AuditEvent.params`, `useAuditDetails`), the API returning no sentence (WF-ARC-0110);
a second line of the action cell, which sorts by the code of the action, never a column of its own,
which the server would not sort (WF-IHM-0060) —, the nature and the label of the object — a backup,
which has none, by its nature, never by its identifier —, the project and the correlation, each as
the entry keeps it, and a link to the history of the object — the log filtered on its nature and
its identifier, its whole history: the other filters and the search lifted, the sort kept —, the
correlation leading likewise to the entries of its request alone. The server sorts on every column
(#550), in both directions. The most recent first when the address says nothing, and the sort is
never lifted (`GridConfig.lifts`): the header of the date asks for descending first
(`GridColumn.descendingFirst`), and thus brings back, from another sort, to the default order. An
object only leads to its own screen if the session reads its function — the risks, the planning
whose exchanges are a sheet, the revisions —, otherwise to its revision, which leads to the first
readable function, and to nothing without a revision function to read (`auditReach`). The entered
correlation only leaves in the form the contract accepts (`pattern` of the field, which the browser
says). The search of the grid covers the label of the object (`search`). The filters only write the
address, under the names of the contract, and bring back to the first page (`audit-filters.tsx`):
the period, two instants entered in local time and sent in universal time — only the browser knows
its time zone, so that the fields show those of the address once the page is hydrated; a bound left
as is leaves again as the address names it, and an input is dated by the period of the address, the
form never remounted —, the nature of the author (`ValuesFilter`), the author and the project among
those the whole log names (`listAuditFacets`, which the mere consultation of the log reads: an
auditor without `users.read` filters by author) — without an author to choose nor an author chosen,
the author filter is not offered —, the actions in a menu, the nature of the object, the object
whose history the address asks for, named and lifted, and the correlation, entered (`TextFilter`);
an author or a project the address names without any choice offering it stays chosen under the
name the entries give it. The project and the object are links where the session can consult
them — a project it can open (`listProjects`, all states; none when the API does not find the list
of projects, which the service only serves from EP-04 on, a tolerance of the 404 that #962 then
removes) —: the project, a revision of such a project, and an object that lives in a revision,
towards its own screen in the one the entry names (`AuditObject.revision`) — a risk towards the
risks of the revision, its detail open (`risk`), the import of a planning, of an estimate or of a
remaining to commit towards its exchanges, its report shown (`import`), the differential of an
amendment towards the cost structures of the revisions screen read in it (`revision_id`); an actual
cost line and the import of the actual costs live in no revision, and an account, a role or a
backup have no screen of their own: their name stays alone. A period the API refuses (422, the end
designated out of its bounds) is said in place of the entries, the filters kept, and any other
refusal of the filters by its envelope (`problemMessage`); no command is offered.

### The imports and exports screen

The imports and exports screen, `…/revisions/[r]/exchanges` (`frontend/src/components/exchanges/`,
US-0260), is the FBS-4.3.4 sheet of the planning, whose header leads to it in the same context,
like the one of the actual costs screen; an import nevertheless applies to the current revision,
created if needed (WF-INTF-0090), whatever the revision read. An import is done in two steps
(WF-ARC-0100): the command of its nature opens in the page the choice of the file — and, for an
extraction of actual costs, the period it covers —, which a server action uploads for an import
(`uploadFile`, `purpose: import`) then analyses (`openImport`); a file of more than 10 MiB, the
bound the contract gives to the upload of an import, is refused in the page, and the bound of
Next's server actions is set a little above (`next.config.ts`). The task of the analysis goes to
the tracking of the shell, and the address names the import (`import`, an identifier or nothing),
whose report the page reads (`getImport`) — lines read, reasons for confirmation, lines rejected by
their place — their tab when the file has some, and their rank — and their reason, rendered like a
refusal from its code and its parameters (`problemMessage`), differences with the fields they
change, named by the catalogue of their columns (`NodeColumn`, `ActualCostColumn`), tasks that the
file dates otherwise than Waterfall recomputes them (`date_mismatches`, WF-INTF-0040) —, in the
order received. The commands of a report are its own: another import shown replaces them. The
application is only offered to an analysed import, and only leaves once confirmed in the page; its
task goes to the tracking. Abandoning brings back to the starting address, if the screen still
shows that import. The report also names what the import ignores (`report.ignored`), the columns
of an extraction of actual costs by their heading as the file carries it. Each import is offered as
the project offers its command (`importOffers`): `import_planning`, `import_estimate`,
`import_remaining`, `import_actual_costs`, with or without a current revision — without it, whoever
cannot create the revision sees the import unavailable, `may_create_revision` named. The one of
the actual costs, unavailable for lack of a mapping (`actual_cost_mapping_complete`), says in
addition the required columns without a heading and leads to the page of the mapping (FBS-3.1.3):
the columns come from `getActualCostMapping`, which the page reads (`readMappingGap`) for whoever
carries `cost_settings.read`, the others reading the condition alone. The refusals of
`openImport` — the 409 that names the columns (`columns`), the 422 `FILE_FORMAT_UNREADABLE` that
names each absent column with its headings (`missing_columns`) — are said by `problemMessage`. A
project without a revision, which no revision address reaches, offers the same imports on its own
screen (`ImportPart`), and shows there the report of the import its address names (#332). The
screen is guarded by the commands it exercises, and not by the mere reading of the planning (#521):
it shows itself to a session that reads the planning, of which it is the sheet, or to which the
project lists an import (`listsAnImport`) — an estimator, whom the estimate and the remaining to
commit lead there when the project lists their import, available or not, the screen then
presenting it with its conditions (`ExchangesLink`, WF-IHM-0090); it is not found for anyone else.
The list of the imports, paginated by the server (`offset`, `ListPages` of
`components/grid/list-pages.tsx`), leads to the report of each; the export request only offers the
natures that the revision read offers to export (`exportOffers`, `export_*`) — an export, guarded
by the permission to consult its nature, is present or absent —, and leaves for that revision — the
image of the tree at the requested level —, and the tracking only offers to download the result of
a successful export (`givesFile` of `tracking.ts`), the one of the other tasks being read on their
screen: Next's server reads it (`getBackgroundTaskResult`) and forwards it as a stream, without
holding it whole in memory and outside the queue of the server actions, to the route
`/tasks/[taskId]/result`, which the browser follows like a link, without `download`: a type the
contract declares for its nature, and the attachment named with the base name the contract promises
(`Content-Disposition`, `attachmentName`), without its length, which `fetch` has decoded, and which
nothing keeps in cache (`private, no-store`). What the route does not forward — a refusal of the
API, including the result expired or not ready yet (409), the API unreachable, an answer that does
not name the file or whose type is not declared, the unexpected error of a bad gateway (502) —
sends the browser back, by a relative address, to the screen it was leaving from (`from`), the
address naming the task and the refusal (`refused_task`, `refusal`, `result-refusal.ts`): the
tracking reloads the task, follows it and says the refusal in its entry (`OutcomeNotice`) — or, the
task unreadable, in a notice of its panel —, and removes it from the address once the page is
revealed, Next's router rendering afresh a page whose address changes (#416).

The page of a project proposes to start its planning through the « Start the project » insert
(`ProjectStart`, `components/projects/project-start.tsx`, US-0490) as long as the main structure of
the current revision has no task. The condition is read at the server (`startOffers`,
`start-offers.ts`): the current revision lists `generate_skeleton` — the caller may change the
planning — without lacking `main_structure_without_tasks`; the front deduces nothing else from it.
The page takes it from the list of its revisions, each element of which is a whole revision,
without reloading it. What the generation produces (a summary per lot and per workstation, their
end milestones) is the back's business: the front sends the command and leads to the grid, and the
criterion of `WF-PRJ-0030-A` on the result goes to the test of the back, not to the insert.
« Automatic planning from the work breakdown » leads to the work breakdown
(`settings?start=skeleton`), where « Generate the planning » (`GeneratePlanning`) calls
`generatePlanningSkeleton`, reloads the page after the generation as after a 409 (#819.5, #819.6)
and leads to the grid. « Import an MS Project file » opens the drop zone (`FileDrop`,
`components/exchanges/file-drop.tsx`): a button that opens the picker, the zone named and
described, the type (`.xml`) and the size checked before sending; it sends like the form of the
imports screen (`useOpenImport`, `open-import.ts`), the report displaying on the page, and the
confirmed application leads to the grid. « Later » folds the insert for the session of the tab
(`start-fold.ts`, `sessionStorage`); a button reopens it. The fake back, stateless, serves the
witness a structure of a thousand tasks: the insert never appears there, and the two end-to-end
paths (work breakdown then generation; upload then report) are only played in the tests of the
components, against the examples of the contract (`project-start.dom.test.tsx`, #1350).

### The portfolio screens

The portfolio screens, `/portfolio/…` (`frontend/src/components/portfolio/`, FBS-2), are outside
the project: each reads its view on the perimeter of the address, under the names of the
contract — the states kept (`states`), the period (`from`, `to`), the calculation date (`as_of`)
and the organisation node (`org_node_id`), which also keeps its descendants, offered in the order
of the tree that `listOrgNodes` returns, each node indented by its depth (`treeLabel`, like the
filter of the workload plan of a project) —, of that perimeter what the operation takes
(`perimeterQuery`, `Takes`). A state shows pressed as the address asks, or, when it names none, as
the server kept them (`scope.states`): the front assumes no default. Under the title, the perimeter
the server kept and the calculation date of the view, `scope.as_of` (`PortfolioHeader`), which all
its figures carry, and the node kept, named by the server (`scope.org_node_label`). A period the
server refuses — an end that precedes the start, `PortfolioPeriodRefused`, EP-02/L42f — is said at
the field of the end, the start named, as the actual costs say it (`usePeriodProblem`) — a single
bound completing itself with the default period, a start later than the completed end is said at
the field of the start, the end named (`params.maximum`) —; the view is not loaded, its title stays
without a kept perimeter and a sentence takes its place (`RefusedView` of
`frontend/src/app/portfolio/refused.tsx`); its states are pressed as the address names them, and,
without a named state, the filter of the states is not offered, nothing saying what the server
would keep. The aggregated workload plan and the project control health, on which a completed
project has no effect (G-05), say so by a note of the perimeter (`completedWithoutEffect` of
`PerimeterBar`) as soon as the server keeps `completed`, read from `scope.states` and never from
the address (US-0703/L9). The list of projects (FBS-2.1) is one more configuration of the dense grid, sorted,
searched and paginated by the server, its totals row the number of projects kept (`meta.total`),
under the value of the portfolio. The six other views (FBS-2.2 to FBS-2.7) show what the server
computes: the aggregated workload plan and the disbursements take in addition the horizon
(`horizon_months`) and, for the first, the under-load threshold (`under_load_threshold`),
parameters of the view and not preferences (WF-PTF-0060): the menu proposes a few values, but any
value of the address that the contract takes — a horizon from 1 to 240 months, a threshold in
`Percent` — is sent and shows as chosen; without a threshold in the address, the menu shows the one
the server kept (`under_load_threshold` of the answer), like the states; the columns of the
workload plan are the months of the answer (`months`), which each role carries in the same order.
A health signal says what it names (`params`: the weeks without a review, the milestone overrun and
its reference date), like an alert of the state of the system the unavailable component. Each
named project — label of the list, heaviest risk, health signal — opens the project (WF-PTF-0030).
The zones of index, of load and of health are those of the server, by `Signal`; the quarterly
evolution of the indices, the S-curve and the disbursements are figures of `Chart`, exported as PNG
with the provenance of their view (`usePortfolioExport`): the perimeter the server kept — states,
number of projects, period, organisation node — and its calculation date, `scope.as_of`, the very
sentence of the header (#312).

### Grids: pasting a block from a spreadsheet

A block copied from a spreadsheet is pasted on the active cell, in two steps (WF-IHM-0050,
`paste.ts`): the block is read at the `paste` event, listened to on the document — the browser
targets it where a click left the cursor, the cell is the one that has the focus in the grid, and
an input under way keeps the paste for its field —, never by `navigator.clipboard`, which asks for
a permission; as tab-separated values, a cell between quotes keeping its tabs and its line endings
(`readBlock`). The server fills, from the targeted column, the columns of the facet of the targeted
node in the order of `NodeColumn`, without knowing those the grid shows (#200): the front therefore
measures the block on those columns (`GridPaste.span`, `pasteSpan`, #223), and refuses at once,
without asking anything, a block wider than them from the cell — as the server would refuse it
(`PASTE_TOO_WIDE`) — and a block whose span, from the targeted column to the last column filled in
that order, reaches a column the grid does not show, hidden or absent from its configuration,
which it names — by its header, or by its label from the catalogue (`enums.NodeColumn`); it
likewise refuses a block one of whose rows would not fall on the one the server writes: the server
fills the rows of the plan under the targeted row, which the grid knows by their number in the
whole structure (`row_number`), not the rows displayed after it. A single guard compares, from the
target to the last row of the block, the number of each displayed row to the one it would have in
the order of the plan (on a differential, the server skips the nodes the amendment removes and
fills the next ones: the guard counts neither their rank nor their row, like the preview, #1278) —
a grid that pastes reads all the kinds of node, and its numbers follow one another —; folded
(`fold.tsx`), moved by a sort, hidden by the search or a filter, or beyond the last row shown, the
cause said is the one the user lifts first (L40, #527). Otherwise `previewPaste` returns the plan,
which a shadcn dialog box shows (`PasteDialog`, `ui/dialog.tsx`), in a single announced region —
how many rows will be written, each refused row by its place in the block, its cells as copied and
its reason, a row refused for several cells counted once —, and `applyPaste` applies it on
confirmation, in a single operation: the valid rows are written, the refused rows are not
(WF-IHM-0050, EP-14/L42q). A plan that refuses rows and writes others says so, and is confirmed; a
plan that writes no row only offers abandoning. The confirmation waits for any other write of the
grid under way — an entered cell, a gesture — and the reload that follows a gesture: it would carry
the version of the structure that their answer is going to advance, and would be refused (412);
« Apply the paste » stays offered, inactive, busy and described by the wait, until their answer
(`busy` of `useGridPaste`, #1224). What the confirmation returns takes the place of what was loaded
(`CellWrites.applied`), like the rows a choice of a cell's menu writes; a cell write that left
before them and answered after is taken like any answer, the counter of the structure deciding
which of the two a row shows (`answers.ts`, #202, #421), and only its refusal stays silent when
they have written its row since. What the paste did not write (`PasteApplied.rejected`) — the
refusals of the preview, and those the server adds by judging the accepted rows again, a category
or a role deactivated in the meantime — is said above the grid with the cell from which the block
was pasted and the number of rows written (`PasteAppliedNotice`), each refusal as in the preview,
read in the answer and never in the plan, until the user closes the notice or pastes again; the
refusals are there a named region, reachable by keyboard, whose height is bounded — they scroll,
the grid stays in the window (defect no. 13), the sentence and the closing outside the scrolling —,
outside the alert, which only says the cell, the number of rows written and that of the rows
refused, « listed below » — a sentence of its own, the preview keeping its own —, and which
describes it (#765). A paste written in full says nothing more than its grid. Escape abandons, an
answer arrived after the abandon is ignored, and the focus returns to the cell. The front judges
nothing of the content: the targeted column leaves under its column name of the contract
(`NodeColumn`), whether the grid sorts it or not, and the confirmation carries the version of the
structure loaded (`structureVersion`), the server refusing by 412 a plan judged on a structure that
has changed since the preview (#200, #201). The fake back only serves the first example of each
operation, the plan that refuses nothing: the partial paste is only tested by the tests of the grid
(`paste-applied.dom.test.tsx`, `paste-dialog.dom.test.tsx`), and the real height of the notice will
only be proved in a path. A grid without `paste` in its configuration, read-only, takes no paste.

### Grids: undo and redo

Undo and Redo are placed, not wired (WF-IHM-0110, US-0140, `undo-commands.tsx`): every grid whose
loaded structure lists its `edit_*` command as available places them (`undoable` of `DenseGrid`) —
the estimate by `edit_estimate`, the planning by `edit_planning`, the remaining to commit by
`edit_remaining` (#115); no grid outside a current revision places them: neither the marking, nor
an applied import, nor the exclusion of a cost line can be undone. Such a grid shows them as
buttons in its bar and in the context menu of its cells (right click, Shift+F10, Menu key —
`CellMenu`, without one more tab stop), with their shortcuts, and takes Ctrl+Z and Ctrl+Shift+Z —
Cmd on a Mac — in the grid or its bar, outside a menu or a box it opens. Unavailable as long as the
server does not keep the history of the inputs, they stay reachable by keyboard, `aria-disabled`,
described by their reason; the shortcut says it in an announced region. A field being entered — the
editor of a cell, the search — keeps Ctrl+Z for itself: the browser's undo stays there. EP-06 wires
them to `undoLastChange` and `redoLastUndo`, an undo carried by the server, never a stack in the
browser; their refusal will be said like any refusal, its condition named by the catalogue — the
one of an undo that would bring back a subproject deleted since, `restored_subproject_exists`, is
already there (EP-14/L42p).

### Grids: creating and deleting tasks and lines

A grid takes input, and offers its structure gestures, according to the command of the structure
it reads (`CostStructure.available_commands`, WF-IHM-0090): `readGridScreen` returns those that are
available (`commands`), the planning reads `edit_planning`, the estimate `edit_estimate`, the
remaining to commit `edit_remaining`. The front never deduces the phase of the project: on the main
structure of an In progress project the estimate is read-only, the remaining to commit is before
(WF-DEV-0050, WF-RAE-0040). The gestures — « Insert below », « Insert a sub-task », « Insert a
line », « Indent », « Outdent », « Move up », « Move down », « Delete » — are in the context menu of
the cells and on the keys Insert, Alt+Insert, Ctrl+Insert, Alt+Shift+→, Alt+Shift+←, Alt+Shift+↑,
Alt+Shift+↓ and Ctrl+Delete (`structure-gestures.tsx`, pure rules in `structure-rules.ts`); the
bar, held on one line, only offers the first task of a grid without a row. A creation goes through
a dialog that names it, and names the row under which it acts (label; for a line, category and
quantity, which the contract requires), `createNode` and `deleteNode` are the actions of
`src/api/actions/nodes.ts`. A creation designates its place by the node it follows among its
siblings (`after_node_id`), never by a rank that a filtered grid could not count: the active row
for « Insert below » and for a line under a line; without it, a sub-task goes after the last
sub-task, a line under a task after its last line, the lines of a task always preceding its
sub-tasks (#1183, #1187).

The number cell of each row is its handle (`row-selection.tsx`), in a grid whose screen moves rows
(`RowCommands.drag`): named by the number of its row, described by the way to select and to move,
it is traversed with the arrows like the other cells. A click selects it alone, Shift and a click
extend the selection from its anchor; by keyboard, on the column of the handles, Space selects,
Shift+↑ and Shift+↓ extend the selection with the active cell, Escape lifts it. The selection is
made of contiguous rows, kept by their identity: a reload that moves them keeps them selected, and
the active cell follows them; a reload that no longer shows one of its ends — a filter, a folding —
lifts it. Folding a row that carries an end of the selection, its parent for instance, therefore
lifts it, without saying so; folding rows under the selection, its ends staying shown, keeps it.
The active cell also follows the row a gesture moved, selected or not (`RowCommands.moved`), at the
arrival of the reload, which gives it back the focus if it was in the grid. Each row says whether
it is selected (`aria-selected`), the grid that it takes several (`aria-multiselectable`), a status
how many — the rows shown: the subordinates folded under a selected summary follow it without being
counted. A selected computed cell keeps its shade. A move gesture bears on the selection when the
row it starts from belongs to it, on that row alone otherwise, and on the nodes that carry the
others (`topsOf`): a summary takes its subordinates along. Deletion only bears on a single row.

« Indent » places the tasks under the one that precedes the first among its siblings, in last
place (`after_node_id` absent); « Outdent » places them after their parent, under the parent of the
latter (`after_node_id` = the former parent); « Move down » places them after the sibling of their
kind that follows the last, and « Move up » places the sibling that precedes the first after the
last — the same order, without relying on a row the grid does not show. The rows the grid shows are
not always the tree: a search, a filter, the remaining to commit, which by default only reads the
started tasks, or the planning, which reads no line, leave some out. A move is therefore only
offered, in the menu as on the key, if the moved nodes are siblings from rank to rank, of the same
kind, and the neighbour it relies on is rendered: its rank (`Node.position`, from 1, the lines of
a task counting before its sub-tasks) is that of the first minus one, or of the last plus one;
« Indent » is not offered under a milestone, nor under a line. « Outdent » depends on no hidden
row, the place being that of the parent (`parent_id`, `node_id`), but is not offered if the grid
does not show that parent, nor at the root. Alt+Shift and an arrow, where the move is not offered,
are taken without effect: the active cell does not move (AltGr, which is Ctrl and Alt, stays with
the grid). A write under way — a gesture, an entered cell, an applied paste, any write of the grid
(author's decision of 2026-10-21, #1224) —, then the reload that follows a gesture, hold back the
gestures and the confirmation of a paste, the grid saying it is busy (`aria-busy`): the next one
starts from the neighbours the reload rendered, never from those of before with a version already
advanced. The grid says its own writes to the commands of its screen (`RowCommands.writing`), which
count them with their own (`useStructureVersion`), each for the structure where it left: an answer
arrived when the grid shows another does not advance its version and does not reload it.

The handle drags the selection — or its single row, which does not belong to one — beside another
row: before it or after it, at its level, by the top or bottom quarter of the row, or under it, in
last place of its kind, by its middle; between two rows, it is before the lower one, and at the
bottom of the last row of the grid, after it. The active cell follows the first of the dragged rows
(`RowCommands.moved`); when the reload does not show it — dragged under a folded summary, or out of
a filter —, the active cell stays at its index and the focus comes back to it, as after a deletion,
instead of falling on the page; that focus is only given to a cell of the grid, never to an element
outside it. A line is dragged under a task that carries lines, a task under a task that is not a
milestone. Before a row, the place is the one that follows the sibling of rank minus one, rendered,
or the head (`after_node_id` null) at rank 1: the planning, which reads no line, therefore offers
no drop before the first sub-task of a task that carries lines, its sibling of rank minus one being
a line it does not render; dragging it under the task puts it in last place. The indicator — a
stroke between the rows, or the greyed row — only appears where the drop is accepted (`dropOf`):
never among the dragged rows nor under them, nor beside a row of another kind, nor as long as the
grid is busy (`RowCommands.busy`, which `drag` requires). The drag only carries its type
(`application/x-waterfall-rows`): a drop come from elsewhere, a text for instance, moves nothing.
The drag has its keyboard equivalent, Alt+Shift and the arrows on the selection; but a distant
place, or a selection that is not made of siblings, require several gestures there, where a single
drop is enough.

`moveNodes` is called for the list of the nodes in the order of the grid. The version of the
structure it carries is that of a single tracking per grid (`useStructureVersion`,
`structure-version.ts`): the highest between that of the page and those the writes returned
(`NodesWritten.structure_lock_version`), entered cell, creation, move, deletion or paste, because
the contract advances `CostStructure.lock_version` at every write of the tree. That tracking holds
the version and the writes under way per structure: what an answer applies — the version it
reached, the row the active cell follows, the reload — is applied for the structure where it was
sent, and nothing is reloaded for it once the grid shows another (defect no. 1). A refusal per
field is said by the reason of the field (`byField`), for every write of the hook — creation, move
and `deleteNode`, for which the contract cites no field, its refusal then being said by its code —,
like that of a cell; `NODE_NOT_SIBLING`, which comes from a stale loading, reloads the grid in
addition, the focus given back to the grid if the reload removes the cell that had it. The deletion
of a summary is confirmed, that of a leaf or a line is not, and the focus then returns to the
active cell of the grid. The grid is reloaded after a write, the server's loading being
authoritative for the numbers and the levels (#1160), and the version the structure reached is said
to the grid, which the next paste carries. The task gestures of the estimate require
`edit_planning` (`tasksEditable` of `estimate-grid.tsx`) in addition to `edit_estimate`: creating
or deleting a task writes the planning, and an estimator who can only enter the estimate does not
create one. A refusal — a finished task, for instance — is said above the grid naming the row at
issue, whose label is marked and described by it; that of a creation without a row (the first task
of an empty grid) names the attempted task. Success is said by `useSaid` and refusal by
`OutcomeNotice`, both noted in the message history.

The context menu of the cells offers two more submenus (`choice-menu.tsx`, pure rules in
`row-choices.ts`, US-0480). « Timelines »: a box per timeline of the project (`listTimelines`),
ticked when the task is entered in it, and « Time/time tracking » for a milestone; the task offers
it when it names `task.tracking` in its `editable_fields`. « Subproject »: radio buttons, « No
subproject » and each subproject of the project (`listSubprojects`), named by its code and its
label — the code alone is unique within a project —, the one of the line ticked; the line offers it
when it names `estimate_line.subproject_id`, which neither a provision line does, nor the one of a
started task whose subproject has received actual costs (`SUBPROJECT_HAS_ACTUAL_COSTS`): the front
deduces none of these guards. In the estimate, the choice is made as long as the project is not In
progress, in the remaining to commit afterwards, according to what the line names. A submenu
applies to the selection, or to the single row: one call per row that names the field, with the
version of that row — `setNodeTracking` with the complete list of its entries,
`updateEstimateLine` with `subproject_id` —, in the order of the grid — without a write for a row
already in the targeted state — and up to the first refusal, said for its row like that of a
gesture: the rows written before it stay so, those after are not written. Each answer takes the
place of the row loaded (`applied` of `RowCommands.menu`), then the grid is reloaded as after a
gesture. A project without a timeline proposes « Create a timeline… » (`createTimeline`), named in
a dialog, in which the tasks are entered, according to the `manage_timelines` offer of the project:
absent, the entry is not presented; unavailable, it is, greyed with its condition. The
« Timelines » column of the planning and « Subproject » of the estimate and of the remaining to
commit are read-only and hidden (`GridColumn.hidden`) as long as the account has kept no list of
hidden columns (`initialSettings`); it shows them through the choice of the columns.

### Tree grids: folding and unfolding

The tree grids — planning, estimate, remaining to commit — fold and unfold (WF-PLA-0080,
WF-PLA-0090, EP-02/L40, `frontend/src/components/grid/fold.tsx`): a grid whose tree names the
parent of each row (`GridTree.parent`, `parent_id` of `listNodes`) is a `treegrid`, each row
carrying `aria-level`, `aria-posinset`, `aria-setsize` and, when the answer holds rows under it,
`aria-expanded`. A folded row takes its subordinates out of the rows of the grid: the
virtualisation no longer renders them, the keyboard no longer traverses them, and the Gantt, a
column of the same grid, loses them with it; the active cell stays on its row, or moves to the one
that carries it. The button of the label — or the one that precedes the bracket of a summary in the
Gantt — folds or unfolds its row, outside the tab order; by keyboard, as in Microsoft Project, Alt
and minus folds the row of the active cell — the one that carries it, from a row under which
nothing folds —, Alt and plus unfolds it, Alt and * unfolds all, Shift or not according to what the
keyboard layout requires to type the character, on the numeric keypad too; the character is the
one the key typed, and, when it names no command, the one the key carries in the layout the browser
says (`navigator.keyboard.getLayoutMap`) — never the mere place of the key, which carries another
character on another layout. Ctrl and AltGr are excluded; Alt+Shift and the arrows move the tasks.
These shortcuts are only accelerators: without `getLayoutMap`, under Safari and Firefox for Mac,
Option and a key type another character, and they are not recognised. The context menu of the
cells (Shift+F10, Menu key, right click), offered in every tree grid, Undo and Redo or not,
replaces them everywhere: « Collapse the row » — « Collapse « label » », which names the row that
carries it, from a row under which nothing folds —, « Expand the row » when it is folded, « Expand
all », offered even outside a cell, so that the menu is never empty; the focus returns to the
active cell. The keys are said by `aria-keyshortcuts` — Shift+F10 on each cell, those of the
folding on the label of a row that folds, in the menu and in the bar —, as far as the browser
recognises them (`useFoldReach`, read after hydration): all outside a Mac; on a Mac, Alt and minus,
Alt and plus when `getLayoutMap` exists, none otherwise; Alt and * outside a Mac only. A pasted
block that would extend, from the targeted row, over a folded row is refused without asking
anything, like the one that reaches a hidden column. The « Tree » menu of the bar folds all,
unfolds all, or folds down to a level. A search or a filter that keeps a folded row unfolds its
ancestors, once for that search. The folded state is kept in the session storage of the tab
(`sessionStorage`), per grid and per revision, without sending anything to the server: the server
renders the tree unfolded, which the browser folds again once hydrated.

### The commands

A command is displayed by `Command` of `frontend/src/components/commands/` (WF-IHM-0090): absent
when the object does not list it in `available_commands` — the server only puts there those the
caller has the permission to exercise, and the front does not know which permission guards which
command; the only exception, decided by the user on 2026-10-05, an import without a current
revision that the caller could not create, listed unavailable, `may_create_revision` missing —,
present and available, or present and unavailable, marked `aria-disabled` and described by the
visible text of the conditions it lacks (`enums.CommandCondition.*`). `LifecycleCommands` renders,
in the order of the server, the exits of the life cycle of a project — the other commands of the
project belong to the forms of their domain, its modification to the one of its settings
(`ProjectIdentity`) —, and `RevisionCommands` those of a revision, each according to its
`is_available` and its conditions — a marked revision lists them unavailable, for lack of being
under elaboration —, its exports left to the imports and exports screen, which offers them
(`ExportForm`), its inputs (`edit_*`) to their grids and the skeleton to the empty planning grid
(EP-14/L44d); `findOffer` draws a single one from it, and `UnmetConditions` names what the offer of
a form that is not a `Command` lacks. Outside the project — accounts, roles, reference data,
backup —, `platformOffer` follows the permission to change of a function of `platform` scope
(`PlatformFunction`) in `Session.permissions`, or `project_create` for the creation of a project,
which no project lists; the commands of a backup are those it lists (`Backup.available_commands`,
EP-14/L43f), the download and the restoration included. Greying out is only a convenience: an
available command launches its server action, and the server's refusal is said by
`OutcomeNotice`.

### The tooltips of the commands

A button carries `CommandTooltip` (`frontend/src/components/commands/command-tooltip.tsx`, US-0580,
#1071), never a `title=` attribute, which the browser shows late, without formatting nor dark theme,
and never on keyboard focus. A link drawn as a button and a menu item carry it likewise. The
tooltip says:

- **the name** of the command, the one the control already carries;
- **a help sentence**, the `help` prop, already translated: for a command, `commands.<commande>.help`,
  in both languages, held by `make catalogs` and read by `t("commands.<commande>.help")`, which the
  typing of the catalogue refuses for a command that has none (`CommandHelp` names those that have
  one, for a table of commands); for the header of a column, its definition
  (`columns.<grille>.<colonne>.help`); or a sentence with parameters (`helpValues`). `help` and
  `unavailable` never take a literal (`make lint-front`);
- **its keys**, in `<kbd>`, written according to the workstation — ⌘ on a Mac, Ctrl elsewhere —, each
  key by its name from the catalogue (`commands.keys`, `commands.macKeys`). They have only one
  source: the `keys` prop, written as `aria-keyshortcuts` names it (`"Control+Z Meta+Z"`), which
  `CommandTooltip` sets on the control and shows at the same time (`shortcut.ts`);
- **the missing condition**, for an unavailable command (WF-IHM-0090): `unavailable`, which marks
  the control `aria-disabled` — never `disabled`, which would take it out of hover and keyboard. The
  condition describes the control, tooltip closed as well as open: by the text that already says it
  beside the command, which `describedBy` designates, or, the screen saying it nowhere else, by a
  hidden text of `CommandTooltip` itself.

A menu item is written by `MenuCommand` (`menu-command.tsx`), which takes the item
(`item={ContextMenuItem}` or `DropdownMenuItem`), the name, the help, the keys, the condition, the
icon and `onSelect`: the name is both the text of the item and that of the tooltip, and the keys
are set on the item, shown at its end and in the tooltip, from a single input.

The tooltip follows WCAG 1.4.13: it opens on hover, after a short rest, and on keyboard focus, at
once — in a menu, after the same rest, so that Escape pressed at once closes the menu (`inMenu`,
which `MenuCommand` sets); it closes by Escape without moving the focus — in a menu, the first
Escape closes the tooltip, the second the menu —, and stays open as long as the pointer passes over
it, even in a modal menu, which takes the pointer away from the rest of the page
(`pointer-events-auto` of `TooltipContent`). Open, it also describes the control
(`aria-describedby`) by its help sentence: it never carries alone what has to be known, the name
remaining that of the control and the condition its description. The control is a single element,
which receives the attributes and the events of the tooltip: it does not itself set
`aria-keyshortcuts`, nor `aria-disabled`, nor `aria-describedby`, which `CommandTooltip` sets; it
does nothing, pressed unavailable. The tooltips share a single `TooltipProvider`, at the root of
the shell (`shell.tsx`): one closed, the next one the pointer reaches opens without waiting; each
says its delay (`delayDuration` of `Tooltip`), and a tooltip rendered outside the shell, in the
test of a component, brings its own.

_Check_: `src/components/button-title-guard.test.ts` (`make test-front`) reads each component with
TypeScript's parser and refuses a `title=` on a button — `<button>`, `Button`, `CellCommand`,
`Command`, a switch, a menu item, checkbox or radio, or a trigger, an element of role `button`, a
link drawn by `buttonVariants`, written in place or by a constant of the same file —, and a `title`
passed by the destructuring of an object written or named in the file. Left to the review: classes
or props imported from another module, the destructuring of the props a component receives
(`{...props}`), and a component of ours that draws a button under another name. The object commands
move to `CommandTooltip` with US-0580/L2 (#1137), and the guard no longer tolerates any `title=` on
a button: `Command` and `ConfirmedCommand` take `help` (for an object command,
`commands.project.<commande>.help` or `commands.revision.<commande>.help`, after the enumerations
of the contract), `CellCommand` and `UnavailableCellCommand` take the name (`label`), `help` and
the missing condition (`unavailable`), which `CommandTooltip` sets as `aria-disabled` and as
description, without a hand-written hidden text. The header of a column carries its definition the
same way (`GridColumn.help`, key `<grille>.<colonne>` of the `columns` catalogue, and `helpValues`
for a sentence with parameters). The guard follows the bound names in the closest block of the
button that binds them, no longer in the whole file. The submit and cancel buttons of a form or a
dialog, whose label is the action, carry no help sentence. The tests of the component are in
`command-tooltip.dom.test.tsx` (hover, focus, Escape in a menu, keys, condition, shared provider,
axe); `help-keys.test.ts` fails for any `commands.*.help` key of the catalogue that no component
reads, and `column-help.test.ts` for any column of the estimate, the planning, the remaining to
commit or the risk register without a definition.

### Online help

Each screen the table of functions knows opens its help (WF-IHM-0140, US-0580): the « Help » button
of its header (`PageHeader`) — a single icon, named, at most the height of a line of the title,
which follows its last word in the same text flow: on the right, among the commands, it would
shrink the title; an element of a row that wraps, it would take a line of its own under a title on
two lines, the one of the remaining to commit at 1280 × 720; in both cases, the header would grow
and push the totals of a grid out of a low window (`grid-frame.spec.ts`, `remaining.spec.ts`). It
only wraps if the last line of the title is full, and it is then there without an indent: a space
separates it from the title, not a margin —, or F1 anywhere on the screen, opens beside it a side
panel (`shell/help-panel.tsx`, a `Sheet`) on the page of its FBS code — the one of the route the
address follows (`helpCodeAt`, `src/help/help.ts`): a function, a sheet, the list of projects
(FBS-4). A page is a Markdown file, `frontend/help/fr/<code>.md`; a notion of the method,
`frontend/help/fr/notions/<notion>.md`. The server reads them when the panel opens, through the
`readHelp` action (`src/api/actions/help.ts`, `src/help/read.ts`, `server-only`), which names no
file after the request without having checked it against the codes of the table or the form of a
notion name, and whose reading refuses, where the path is written, any file outside the help folder
(#1462); the standalone takes them along through `outputFileTracingIncludes` (`next.config.ts`).
The panel renders them with `react-markdown` and `remark-gfm`, without raw HTML (`skipHtml`) and in
the elements of a text only; a code between backticks reads there as a key (`<kbd>`). A relative
link to a code or a notion (`FBS-4.4.md`, `notions/valeur-acquise.md`, `../FBS-4.3.md` from a
notion) shows its page in the panel; any other link reads as text. The search covers the titles of
the written pages, which the action returns with the page. The panel holds the focus, closes by
Escape and gives the focus back to what had it — the button, or the cell where F1 was pressed; a
page followed through a link gives the focus to its title. An answer arrived after another request
is ignored.

The page of a screen follows the structure of #1075, its second-level headings in this order
(`SCREEN_HEADINGS`): « Ce que montre l'écran », « Ses commandes », « Ses colonnes et ses valeurs
calculées », « Les gestes au clavier », « Voir aussi ». The definitions of the columns are not
written there: the panel renders them after the third section, from the configuration of the grid
of the screen and the keys of its headers (`columns.<grille>.<colonne>.help`, `COLUMNS` of
`read.ts`), a single source with their tooltips. A notion quotes the glossary of appendix A word
for word, without the requirement identifiers between parentheses (« (WF-RIS-0050) »), which mean
nothing to whoever reads the help, and which `help.test.ts` ignores in its comparison (#1440), one
quotation per term (`> **Terme** — définition`), under « Ce que dit le glossaire », then « Dans
Waterfall » and « Voir aussi ». The help exists only in French: an interface in English shows it in
French, a deviation from WF-IHM-0140 as long as the translation is not decided (#1075). `lang="fr"`
only covers the rendered page (`WrittenPage`), the title of the panel and the titles the search
finds: the messages of the interface of the body (loading, failure, number of results) keep its
language (#1442).

_Check_: `src/help/help.test.ts` (`make test-front`) requires a French page per code of the table
that has a screen, or its place in the list of the pages to come with the lot that writes it
(`SCREENS_TO_COME`, `NOTIONS_TO_COME`) — a list that fails as soon as a code it names receives its
file; it holds the structure of the pages, the quotations of the glossary, the links, which lead to
a written page or one to come, and the absence of raw HTML. A page to come says so in the panel.
`help-panel.dom.test.tsx` tests the panel, and `e2e/accessibility.spec.ts` audits it opened by F1 on
the planning.

### Long actions and the tracking of background tasks

A long action hands back control on receiving its background task (WF-ARC-0090): its server
action goes through `decodeTask` of `frontend/src/api/problem.ts`, which holds the reason of a
failure to the rule of the catalogue, and the screen hands the reference to the tracking of the
shell through `useTrackTask()` (`frontend/src/components/tasks/`), with the command that launched
it and, if there is one, the name the user gave it (WF-IHM-0080). The tracking is common to the
nine kinds of task: it reloads the task every two seconds as long as it runs, through the server
action `readBackgroundTask`, shows its progress, adds its end to a log (`role="log"`) read whatever
the screen, offers to reload the screen when it has succeeded — it never reloads on its own —, and
replays the command of a failed task. Its panel is a sheet (`Sheet`) along the right edge of the
window, which also carries the message history (below): a modal dialog titled « Tasks and
messages », which holds the focus as long as it is open and which Escape, its close button, a click
outside the panel or « Reload the screen » close, the focus given back to the button of the bar.
The button of the bar (`TasksButton`) opens it and says, in its name and its badges, the number of
tracked tasks and that of the unread refusals. Nothing opens it on its own, except the refusal of a
result on the browser's return, whose download left from the panel. A handed-over or finished task
is said under the bar, in the flow of the page, on the screen where one is: the last one, in a
short line that stays until the next — the confirmation in place of a success the screen does not
show —, without an announcement, the log speaking for the ends; its button closes it, by keyboard
as by mouse, and gives the focus back to the button of the bar, the task staying tracked (author's
decision, #1179).
Closed, the panel still follows its tasks — the shell reloads them (`TaskPolling`), outside the
entries — and its log still speaks, outside the panel, or inside as long as it is open, where the
focus is held. A relaunch refused as stale (412) loses its command, which would still be, and a
refused reload (404, 401) interrupts the tracking, which says so. No screen tracks its tasks
itself. An answer only applies to the task for which it was requested, never to the one a relaunch
put in its place. Next's server actions leave one by one, in a single queue: tracking k tasks adds
k actions every two seconds, in the very queue of the writes of the screen, which a slow reload
delays as much. The session storage of the tab keeps the running tasks for a full reload, without
their command but with the name the user gave them; and, for an open session, the root layout asks
on the server side for the running tasks of its user (`listBackgroundTasks`), launched from another
tab or another workstation — rather than through a server action on the mount of the shell, which
`StrictMode` launched twice in development. It does not wait for them: it passes their promise to
the tracking (`running`), which reads it by `use()` under a `Suspense` that renders nothing, and
the document leaves without them; without a session, nothing is asked. The tracking asks for them
again through an action (`listRunningTasks`) each time the tab becomes visible again
(`visibilitychange`, `signedIn`); it follows those it was not following — a refused or unreachable
list leaves it as it is, and the promise never rejects. A task found again through the storage or
the list is not relaunched from the tracking: failed, its entry says to relaunch it from the screen
of its object. The `mark` command of a revision (`MarkCommand`) is its first use: it opens, in the
page, the input of the version name.
« Contractualise the amendment » (`MergeAmendmentCommand`, `revisions/`) is another: offered by
the planning grid of an unmerged differential, as the revision lists `merge_structure`, it reads
the report on opening (`getStructureMergeReport`), presents it in the `+`, `-`, `M` marks of the
grid, asks for the version name and confirms with the two counters read; a stale version (412)
proposes to reload the report, and abandoning sends nothing. The merge handed to the tracking,
`useWhenTaskSucceeds` tells the screen that it succeeded, and it states the new reference.
« Prepare an amendment » (`create_structure`) asks for a label and opens the created differential
in the planning grid.

### The message history

The message history (#1043, `components/notices/message-history.ts`) keeps each outcome of a
command the screens have said, success as well as refusal, so that a notice closed or left on
another screen can be read again. It is not the audit log (WF-SEC-0030): a help to the user, for
them alone, proper to the browsing session — the session storage of the tab (`wf_messages`), the
last hundred, erased on sign-out —, without an operation of the contract. The tasks and messages
panel shows it, the last one first (`MessageList`); opened, it has shown them all, and the count of
the unread refusals falls back to zero.

An entry (`Message`) keeps:

- **the time** the notice was said, an instant of the workstation, shown by `LocalTime`;
- **the tone** — `success` or `refusal`, said in words, never by colour alone; the unreachable
  service, a failed or interrupted task, refused rows of a paste are refusals;
- **the sentence of the notice**, as it was said, in the language of the moment: the history
  repeats, it does not rewrite; and, for a failed task, **the reason** as a second sentence (`detail`);
- **the object**, when the notice names one: the one the screen gives — `subject` of `OutcomeNotice`,
  of `Command`, of `DoneNotice` and of `ReferenceForm` (the object changed: a line of the reference
  data, a project, a subproject; the project of an exit of the life cycle, the revision of a revision
  command), `object` of `useSaid` —, otherwise the object in conflict, the task — its kind and the
  name the user gave it —, the external copy tested;
- **the correlation reference** of an unexpected error (`INTERNAL_ERROR`, WF-OBS-0020);
- **the screen**: its address, to which a link brings back, and the project it showed
  (`useShownProjectLabel`); the link is named like the end of the breadcrumb (`crumbsOf`), followed
  by the project; a screen the breadcrumb does not name is « Screen of origin ». The end of a task
  keeps the screen from which it was launched; a task found again — through the list of the API,
  after a reload — the screen where its end is said.

What feeds it — the outcome of each command, success as well as refusal:

- **the refusals**: `OutcomeNotice`, for each refusal it says — the notices of the grid included,
  which go through it —, `UnshownNotice` of the grid; a refusal said outside a notice, through
  `useNoteRefusal`, in the very sentence a notice would give it: a refusal said at the fields of a
  form (`ReferenceForm`, the creation of an account, of a role, the list of the contributors, the
  breakdown), the refused date of a restoration, the refusal of a write that left from a screen since
  left, which the bar says (`LeftRefusals`) with the screen it had left from, and the one of the
  tracking of a task, entered by `TaskPolling`, mounted with the shell, panel closed;
- **the successes**: each status of a screen that says what a write did, through `useSaid`
  (`components/notices/said.ts`), the only entry point of these statuses, which says it and enters
  it; `DoneNotice` (its `of`: the outcome it says, one per save); the generated skeleton, the upload
  of a backup, the test of an external copy (`LocationTest`);
- **the pastes**: `PasteAppliedNotice`, a success when all the rows are written — nothing is then
  said in place, the grid shows them —, a refusal otherwise, the number of refused rows as a second
  sentence;
- **the tracking**: a handed-over task (`useTrackTask`) and each end of its log.

Each enters the outcome there once, whatever the frequency of its renders (the identity of the
outcome, `noteMessage`), without announcing anything: the notice in place remains the alert
(`role="alert"`) or the status, and the history is not a live region. A refusal said partly at the
fields is entered whole, and the part the notice under the form says is not entered a second time
(`parts`). In place, nothing changes. Do not enter it, for lack of a command having left: what a
pressed unavailable command does not have — its conditions, which a status repeats (`noted: false`
of `useSaid`, `ToldConditions` of the lists of the reference data) —, and the refusal of an input
the screen judges before sending anything (a required field, a file too heavy, a mistyped cell).
Nor the « Backup started » status, whose handed-over task is already entered by the tracking.

### The development image

The development image (`frontend/Dockerfile`) starts from an image pinned by its digest, and runs
under an unprivileged user, designated by their number.

### The API client

The API client is generated from the contract (PBS-1.2, WF-ARC-0060): `make generate-client`
writes its types in `frontend/src/api/generated/schema.d.ts`, which nobody touches up, and
`frontend/src/api/client.ts` makes typed calls of them through openapi-fetch, a list of the query
written in a single parameter, its values separated by commas, as the contract declares them all
(`explode: false`, which `make lint-openapi` requires of every array parameter:
`rule/array-parameter-explode-declared` and `rule/array-parameter-not-exploded` of
`docs/api/redocly.yaml`). It writes beside it `examples.d.ts`, the examples of `fixtures/api/` that
the contract cites per operation and per status (`wftools.exampleroutes`), which types the answers
of the fake client of the tests. An operation missing from the client is a change to the contract,
followed by a `make generate-client`; the generated file is versioned with it.

The client keeps its connections open, and the next one reuses the one an answer has freed. The
API closes an idle connection after a delay of its own — five seconds for Prism as for uvicorn —,
and undici, the `fetch` of Next's server, only reuses its own within a margin below that delay;
but its timer is that of the server's loop, which a load holds longer than the margin: the request
then leaves on a connection the API has just closed, and `fetch` rejects it (`UND_ERR_SOCKET`,
`other side closed`, or `ECONNRESET`), without any shorter delay changing anything, held likewise.
A read (`GET`, `HEAD`) cut this way leaves a second time, on a new connection, and the cut is
written to the server's log (`console.warn`); cut again, it is the API out of reach
(`Unreachable`), never a silence. A write never leaves again: the API may have done it before
closing. `WATERFALL_API_CONNECTIONS` says how the server holds its connections: `kept`, or nothing,
in production as in development; `closed`, one connection per request, closed once answered
(`Connection: close`), which only the harness sets (« An end-to-end path »), and which the server,
started this way outside the harness of the fake back (`WATERFALL_E2E`), reports once to the log;
no file of `deploy/` nor the image of the front names it, which `src/api/server.test.ts` checks.
Any other value stops the server at its start-up (`src/startup.ts`), rather than answering an error
to every request. The cut written to the log only says its method and its path, never the query.
`src/api/client.test.ts`, `src/api/connections.test.ts` — against a server on a real socket, which
cuts the reused connection — and `src/api/server.test.ts` test it. No network call is written
outside `frontend/src/api/client.ts`, and only the Next server calls the API: a client component
imports from `src/api/` only its server actions (`src/api/actions/`) and types.

_Checks_: `make client-up-to-date` fails if the versioned client is not the one the contract
produces; a change to the contract therefore wakes the front family. ESLint refuses outside
`src/api/client.ts` the known means of reaching the network — `fetch`, `XMLHttpRequest`,
`WebSocket`, `EventSource`, an imported http client —, and, in a `"use client"` file, the direct
import of `src/api/` outside the server actions, which open on `"use server"`;
`src/api/network-guard.test.ts` tests it on trapped excerpts, and freezes the list of the
dependencies of `package.json`, so that a new one is examined for the guard before entering. The
transitive case — a module without a directive that imports `@/api/server`, and that a client
component imports — escapes ESLint: `client.ts` and `server.ts` import `server-only`, the safety
net of `next build`, which `make build-front` launches at the fast tier, without a reachable API: a
page that would read the API at build time, pre-rendered instead of being rendered at the request,
makes it fail (#131); at the full tier, the end-to-end paths launch it before playing against the
built front (`make e2e`, `make e2e-measure`, and the `front-build` job of `ci.yml` in the chain).
After either build, `make prerendered-front` asserts that it pre-rendered no page (« The chain »).
`make typecheck-front`, `make test-front`;
`make lint-docker` (hadolint).
## The fake back

The fake back serves the contract through prism, without one line of response written by hand:
what it answers are the **examples of the contract**. A missing response is an example added to
the contract, never a file in the front; an example invalid against its schema makes
`make lint-openapi` fail.

A long example goes under `fixtures/api/`, as an OpenAPI Example object (`summary`, `value`),
and the contract cites it by `$ref`; the bundle embeds it. Its numbers take up those of the Vérif
where they make sense — probability of winning, inflation, amounts.

**The witness universe.** The examples describe one single universe, at one single instant, today:
3 June 2026 at 14:05 UTC (`docs/api/DECISIONS.md`, « L'univers témoin »). The first example of
each operation is the witness project, PRJ-001, or the portfolio that counts it, at that instant;
another named example is another reading of it, an earlier instant of the same chronology, the
sequel of a write made today, or a declared counterfactual variant.

**What is generated is not written by hand.** `make mock-data` (`wftools.mockdata`) writes,
reading neither the clock nor chance — every drawn value comes from the digest of a fixed seed and
of what it describes, and two generations write the same bytes:

- in `fixtures/api/volume/`, which is never touched up, the volumes of §4.6.2: the structure of
  the witness, a thousand tasks and five thousand lines, its readable core at the head and linked
  to the drawn tasks around it, dated in hours on the calendar of each task and read today
  (`wftools.mockstructure`, dated and emitted by `wftools.mockcore`), first example of
  `listNodes`, the indicators of its estimate, what its first summary task depends on and a
  lengthened duration that pushes a task into 2027 (`task_lengthened`); the comparison of the offer
  and of the reference over that whole structure, read with `fields`, second example of
  `compareRevisions` (`wftools.mockcomparisons`, #1201); the three hundred projects of
  `getPortfolioProjects` and the views that sum up from their rows — value, performance,
  cost structure, risks and coverage (`wftools.mockportfolio`) —; the two hundred cost
  categories and fifteen years of hourly rates, in one page and by pages, the grid sorted
  also by the rate of one year (`wftools.mockreference`);
- under `fixtures/api/`, by their name, the examples of the witness, declared generated in
  `tools/paths.toml`: the readings of its core (`wftools.mockcore`, described once in
  `wftools.mockwitness`, its hours of work in `wftools.mockcalendar`, its lines sorted under
  each task, or filtered by the bounds of a column, by `wftools.mocksort`); the responses of the
  grid writes, difference of two readings (`wftools.mockwrites`), among them those of the gestures
  of structure and of the entry of tasks, with their refusals (`wftools.mockgestures`, the place of
  a node and the loops a gesture would close in `wftools.mocktree`, the gestures of the estimate
  made on amendment 2, and the entry and the paste the end-to-end paths make there, in
  `wftools.mockamendmentwrites`), the gestures of the cards of the Kanban and their
  responses (`wftools.mockkanban`), and the refusals
  of a paste and of an import that a subproject or the phase of the project command
  (`wftools.mockexchanges`), and a manual date on a non-working day, refused at entry and
  flagged at import (`wftools.mocknonworking`, #1271); its
  history (`wftools.mockhistory`), its revisions read before the designation of the offer, while it
  is still proposed (`wftools.mockcycle`), its marked revisions read with their snapshot
  (`wftools.mocksnapshot`), its compared revisions (`wftools.mockcomparisons`) and its risks, and the responses of the
  entries of a risk, with the own estimate of risk 751 and the preliminary report of its
  occurrence (`wftools.mockriskwrites`); its indicators, its curves and
  its workload today, over the whole structure of a thousand tasks (`wftools.mocktoday`,
  `wftools.mockindicators`, `wftools.mockcurves`); its actual costs — those the witness describes and
  the invoices of its drawn tasks that are completed — and the log of their imports (`wftools.mockcosts`);
  and the views of the portfolio over time — aggregated workload, S-curve and its variant
  at 31 December 2025, project control health —, which sum the witness at its own readings and the other projects by
  simple formulas (`wftools.mockportfoliotime`); and the audit log of the installation, drawn from
  the chronology of the witness and from the examples that date its accounts, its roles and its backups
  (`wftools.mockaudit`, held by `tools/tests/test_mockaudit.py`); and the readings of the lists
  written by hand — the projects of the home page, the subprojects and the contributors of the witness, the
  accounts and the access roles, the backups — and of the work breakdown of the witness, sorted,
  searched and filtered as their screens ask for them, with the entry of the work breakdown, its response
  and its refusals (`wftools.mocklists`, held by `tools/tests/test_mocklists.py`); and the
  contributors of the witness once an account is anonymised (`wftools.mockanonymized`, held by
  `tools/tests/test_mockfindings.py`); and the exit of the witness, which marks or abandons its
  revision in progress, its refused code, and its readings according to the quality of the reader —
  participant, or non-contributor who registers a project manager when none has an active account — or during the
  marking of its revision in progress (`wftools.mockproject`, held by `tools/tests/test_mockexit.py`); and the refusals of one
  form each (`wftools.mockrefusals`, held by `tools/tests/test_mockrefusals.py`), with those the
  contract declared without a code, a condition or an example (`wftools.mockdeclared`, held by
  `tools/tests/test_mockdeclared.py`).

What the same command generates is never re-read from the disk: the indicators, the risks
and the curves of the witness, which the portfolio sums, are passed to it in memory, so that one single
run of `make mock-data` reaches its fixed point.

**What stays written by hand** — sessions, accounts and roles, reference data (resource roles and
their headcounts, calendars, organisation nodes), the project, its revisions and its transitions,
imports and their reports, background tasks, state of the system and backups, counterfactual
variants — is read by the generators, never copied, and confronted with what is generated:
`tools/tests/test_mockhistory.py` for the chronology, `tools/tests/test_mockuniverse.py` for the
rest (the monthly hours of a role, its whole headcount included, are its headcount times the
weekly hours of its calendar × 52 / 12, the row of the witness in the portfolio is that of
its indicators, every view of the portfolio is computed today…). A volume example is written one line per element, so that a change can be read
in the diff. The marks the end-to-end paths read — line numbers, labels,
totals — are fixed by `test_the_marks_the_journeys_read` (`tools/tests/test_mockstructure.py`)
for the structure, `test_the_marks_the_portfolio_journey_reads` (`tools/tests/test_mockdata.py`)
for the portfolio and `test_the_marks_the_review_journey_reads` (`tools/tests/test_mocktoday.py`)
for the monthly review: a change of the generator that moves them fails there, before the
paths. The grid tests check only lines that stay within the window the virtualised grid
renders. The tests of the front read the address of a node of the witness in the example — its
identifier, its index or its number found by its label —, never a hard-coded number,
except where the number is what the test puts to the proof (#400).

`make mock-spec` derives from the contract the variant prism serves: paths under the prefix of the
server, `/api/v1`, which prism would ignore, and no security required (`security`
removed) — the fake back grants the session the mockup starts from (EP-02), and Prism therefore does not require the
token. A third difference: Prism serves the first example of an operation whatever its
path, so that `listNodes` of the amendment would have rendered the main structure. The variant
therefore repeats the paths of `listNodes`, `updateEstimateLine`, `previewPaste` and `applyPaste` for
each structure of kind `amendment` that the first example of `listCostStructures` lists, its
identifier written in the path, and places the `amendment` example of each operation at their head
(`wftools.mock`, #1219, #1277): the reading of the installation on the amendment, the hours of its
added line entered, and a block pasted on its lines 7 to 9, previewed then applied
(`wftools.mockamendmentwrites`). Prism ranks a path by its written segments, ahead of the one that
leaves them as templates. No response is written by hand: the choice follows the identifier of the
path. The other paths of the amendment — its gestures, its planning — answer like those of the
main structure; amendments 212 and 213 and the risk structures are not routed (EP-16).
**Where the writing paths play.** The main structure of the project in progress lists the estimate
read-only (#1176): a path that writes the estimate therefore does not read it there. The one of the entry
of a line (`entry.spec.ts`) and the one of the paste (`paste.spec.ts`) play on amendment 2, structure
203, whose three `amendment` examples the fake back serves; the paste finds there `[WF-IHM-0050-A]`,
the three lines of the block of `paste_applied_amendment` written after the confirmation. The paths
that have no example of their own on the amendment stay on the structure that serves them, the own estimate
of the rewiring risk (structure 204, which receives the first example of each operation): the
paste of an unknown category, the paste of a block too wide, and the provision line, which
the amendment does not carry. A path that writes on another differential awaits its examples, at
EP-16.
Nothing else changes. The contract keeps the `bearer` scheme, and the front sends it all the same:
in `WATERFALL_AUTH=mock` mode, `serverClient()` sets `Authorization: Bearer` with a fixed token
(`MOCK_TOKEN`, `src/api/server.ts`, with no secret value), which only the Next server holds — the
browser holds none. This mode is refused when `NODE_ENV` is `production`, unless
`WATERFALL_E2E=1`: the Playwright harness plays its paths against the production front, and
sets both variables on its front (`playwright.config.ts`); `make dev` sets
`WATERFALL_AUTH=mock` on the front (`compose.dev.yaml`), `make build-front` does not need it. Against
an API the environment names (`WATERFALL_API_ADDRESS`), the harness sets only
`WATERFALL_E2E=1`, which admits no fixed token there (#1265).

- `make mock`: the fake back alone, on `http://localhost:4010`.
- `make dev`: the front (`http://localhost:3000`) against the fake back, through
  `deploy/compose/compose.dev.yaml`. The front knows only the address of the API,
  `WATERFALL_API_ADDRESS`: from EP-03 on, the same variable designates the real service.
  `make dev-down` stops it. The fake back keeps the npm cache, where `npx` put prism, in
  the named volume `mock-npm`, mounted on the directory of user 1000 of the image, who
  owns it: prism is downloaded only at the first start.
  `docker volume rm waterfall-dev_mock-npm`, the platform stopped, forgets it.
- The front opens at `localhost` and at `127.0.0.1`. To open it from another workstation, at
  the address of this one on the network, declare it in `WATERFALL_DEV_ORIGINS` (hosts
  separated by commas), on the call or in `deploy/compose/.env`, which git ignores:
  `WATERFALL_DEV_ORIGINS=127.0.0.1,192.168.1.210 make dev`. Without it, `next dev` refuses its
  resources to that origin, and the page displays without hydrating (#481).

The fake back serves readings. It keeps no state: a created project does not appear in
the next list. It serves the front lots that precede their back lot and the tests of the
front that only read, never to put a write to the proof.

_Checks_: `make lint-openapi` (examples conforming to the schemas, volumes included),
`make mock-data-up-to-date` (the versioned volumes are those the tool writes, in the
contract family, which `fixtures/api/` wakes like the contract), `make lint-compose`.

## Commands

Everything is launched through the Makefile, on a workstation as in the chain: `make help` lists them.
A command the chain executes exists in the Makefile, and a workflow writes no control
logic on its side; a failure of the chain is therefore reproduced by the same
command.

| Command                                                                 | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make check BASE=origin/epic/EP-nn`                                     | the checks of what the change touches, uncommitted files included: to run before pushing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `make check-all`                                                        | every family of checks                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `make check-<famille>`                                                  | one family: `repo`, `spec`, `contract`, `back`, `front`, `front-image`, `roadmap`, `keycloak`, `service`, `production`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `make changes BASE=…`                                                 | the families a change touches                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `make test-back TESTS=…`, `make test-front TESTS=…`, `make e2e TESTS=…` | one single test file, during development; without `TESTS`, all of them, as in the chain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `make service-install`                                                  | bootstraps the started service platform, its realm applied (`waterfall-api install`, US-0420): applies the migrations under the owner of the tables, creates the installation, its three predefined roles and its local administrator, `WATERFALL_ADMIN_EMAIL` (`administrateur@waterfall.test` by default), in the language `WATERFALL_DEFAULT_LANGUAGE` (`fr` by default), and writes on its output only the link that sets its password, valid until it is used; run again, it creates nothing, and writes a new link, which replaces the previous one, as long as the administrator has no password, none afterwards                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `make service-up`, `make service-down`                                  | starts, stops the service platform (`deploy/compose/compose.service.yaml`: PostgreSQL, Redis, the Garage object storage and its buckets, the migrations, the API, the worker and the scheduler of its tasks, the restoration service, Keycloak behind its HTTPS front end and its realm, applied again at each start by `keycloak-realm`, which stays started to reapply it after a restoration, OpenLDAP, Mailpit); it requires its secrets in the environment (below), and `service-down WATERFALL_RESET_DATA=yes` also deletes its databases, its storage, its directory and the authority of its front end                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `make keycloak-authority`                                               | copies out of the platform the root of the authority of Keycloak's front end, into `deploy/compose/.authority/root.crt`, which git ignores; `service-up` and `test-keycloak` do it at each start                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `make e2e-service`                                                      | the paths of the Playwright project `service` (`frontend/e2e/service/`) against the real service, through Prism as a proxy (« An end-to-end path »); same secrets as `service-up`, and the browser of `make e2e-browsers`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `make service-logs`                                                     | the logs of the services of the platform, those of `SERVICES` (`SERVICES="keycloak openldap"`), all by default                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `make migrate`                                                          | applies the migrations to the database `WATERFALL_DATABASE_URL` designates                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `make build-keycloak`                                                   | builds the image of Keycloak (`deploy/keycloak/`): the extension compiled and its JUnit tests passed, the themes, the realm; no JVM is asked of the workstation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `make test-keycloak`                                                    | starts Keycloak on the platform — and Mailpit, where it sends its emails and where its tests read them —, applies its realm and runs the tests of the `keycloak` marker (`backend/tests/test_keycloak_*.py`), which the other tests of the back leave aside: the realm and the extension, and the API that validates its tokens, served in the process of the tests on a database they create on the PostgreSQL of the platform, unless `WATERFALL_TEST_DATABASE_URL` names another one; it measures the coverage of the client of Keycloak's administration API and of the bootstrap, `waterfall-api install` (« Code coverage »); same secrets as `service-up`. Its tests change the realm for the time of a test — the duration of an idle session, that of the links, the lockout, the directory and the provider disabled, the directory not synchronised (`UNSYNCED`) —, and one of them restarts Keycloak (#852): it is never run at the same time as another use of the platform, `make e2e-service` or the tests of another agent, no more than `make check-keycloak` or `make check` when it puts the `keycloak` or `service` family to the proof                                                                           |
| `make check-keycloak`                                                   | the `keycloak` family: `build-keycloak`, then `test-keycloak`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `make images`                                                           | builds the three images the chain publishes — `front`, `waterfall`, `keycloak` —, each the `production` stage of its Dockerfile, under `ghcr.io/waterfall-project/<image>`, tagged by the commit (its whole digest), by the branch shaped as a tag (`epic/EP-03` gives `epic-EP-03`) and, on `main`, by the version of the distribution of the back (`backend/pyproject.toml`), which the front carries too, once only and for the three together: the version tag is immutable; the branch and the commit are those of the repository, unless `IMAGE_BRANCH` and `IMAGE_COMMIT` name them; `PUSH=yes` publishes them, from `main` or an `epic/…` branch only, from a clean repository at the named commit, once the three are built and searched (`wftools.images`, « The chain »)                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `make prerendered-front`                                                | reads the manifest the last production build of the front wrote (`frontend/.next/prerender-manifest.json`) and asserts that it prerendered only `/_global-error` and `/icon.svg`, without Docker: the `front` family chains it after `build-front` at the fast tier, after the paths at the full tier (`wftools.frontimage --manifest`, « The chain »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `make check-front-image`                                                | the `front-image` family: builds the `production` stage of the front (`frontend/Dockerfile`), starts it, and asserts that `/` answers with the settings of the `front` service of the production Compose, that the front stops without each of the variables it cannot do without, naming it (#825), that `WATERFALL_AUTH=mock` without `WATERFALL_E2E` is refused, and that `next build` prerendered only `/_global-error` and `/icon.svg` (`wftools.frontimage`, « The chain »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `make production-trial`                                                 | starts the production platform (`deploy/compose/compose.prod.yaml`, US-0430) on the images of the tag `WATERFALL_IMAGE_TAG` — the commit of the repository by default —, under a local name (`WATERFALL_DOMAIN`, `waterfall.localhost` by default, with `compose.prod.local.yaml`), bootstraps it, asserts the liveness probe of the API, that the owner of the tables, `waterfall`, is not a superuser, the redirect from HTTP to the same page on the published address, port included, Caddy's headers in HTTPS, HSTS first, that Keycloak's console and the `master` realm answer 404, and that the first administrator sets their password through the link, signs in through the front and Keycloak and that the front names them; with `WATERFALL_TRIAL_RESTORATION=1`, a backup then its restoration requested through the API, the restoration followed through the liveness probe until `ok` (`wftools.restoration_trial`, US-0440, #948), which the chain requests (`production.yml`, `images.yml`); then removes it with its volumes (`wftools.production`); its secrets come from the environment, as `deploy/compose/production.env.example` names them; its Compose project is `WATERFALL_PRODUCTION_PROJECT` (`waterfall-production-trial`) |
| `make check-production`                                                 | the `production` family, at the full tier only: `make images`, without a push, then `make production-trial` on the built images                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

The service platform refuses to start without its secrets, which no file carries:

| Variable                               | What it protects                                                                                                                                                                                                                                                                                    |
| Variable                               | Ce qu'elle protège                                                                                                                                                                                                                                                                                  |
| `WATERFALL_POSTGRES_PASSWORD`          | the PostgreSQL role `waterfall`, owner of the tables, through which the migrations pass; in letters and digits only, since it is written in a URL                                                                                                                                                   |
| `WATERFALL_SERVICE_DATABASE_PASSWORD`  | the role `waterfall_service`, named after the database, through which the API and the worker connect, which holds only what the tables grant it (sql.md, « Le rôle du service »); in letters and digits only                                                                                     |
| `WATERFALL_BACKUP_DATABASE_PASSWORD`   | the role `waterfall_backup`, member of `pg_read_all_data`, through which the worker backs up the two databases, which reads every table and can neither write nor cut a trigger (#895); in letters and digits only                                                                                  |
| `WATERFALL_REDIS_PASSWORD`             | Redis                                                                                                                                                                                                                                                                                               |
| `WATERFALL_KEYCLOAK_DATABASE_PASSWORD` | the role `keycloak`, owner of Keycloak's database, distinct on the same server                                                                                                                                                                                                                      |
| `WATERFALL_STORAGE_SECRET`             | the key of the platform on its object storage, Garage, whose identifier, which is not a secret, is `WATERFALL_STORAGE_ACCESS_KEY` (`GK000000000000000000000001` by default)                                                                                                                         |
| `WATERFALL_STORAGE_RPC_SECRET`         | the internal channel of Garage; 64 hexadecimal digits (`openssl rand -hex 32`), Garage refusing any other form                                                                                                                                                                                      |
| `WATERFALL_KEYCLOAK_ADMIN_PASSWORD`    | the `admin` administrator of the `master` realm, through which keycloak-config-cli applies the `waterfall` realm, and which the tests of `make test-keycloak` read; it is read only at the first start, which creates the `master` realm: changing it requires `make service-down WATERFALL_RESET_DATA=yes` |
| `WATERFALL_FRONT_CLIENT_SECRET`        | the `waterfall-front` client of the realm                                                                                                                                                                                                                                                           |
| `WATERFALL_SERVICE_CLIENT_SECRET`      | the `waterfall-service` client, the service account of the API and of the worker                                                                                                                                                                                                                    |
| `WATERFALL_INSTALLATION_CLIENT_SECRET` | the `waterfall-installation` client, that of the bootstrap alone, whose links are valid until they are used (#652), and which gives the realm the language of the installation (`manage-realm`, #873): neither the API nor the worker holds it                                                      |

On a workstation, workstation values are enough — those of `.github/workflows/keycloak.yml` for
example. Keycloak answers in HTTPS on `https://localhost:8443/auth`, its administration console
under `/auth/admin`, through a Caddy front end (`deploy/compose/Caddyfile.service`) that the browser
and the Next server both reach, and which also serves it on `https://127.0.0.1:8443/auth`,
a second address for the tests of the platform (#680); its address,
`WATERFALL_KEYCLOAK_ADDRESS`, is `https://localhost:<port>/auth`: the front end serves only the
hosts `localhost` and `127.0.0.1`, and only the port moves, through `WATERFALL_KEYCLOAK_PORT`:
the Makefile and Compose deduce it from it, and read no exported address (#735).
The certificates come from Caddy's own authority (`tls internal`): its root, kept
in the volume of the front end, is copied at each start into
`deploy/compose/.authority/root.crt`; the front trusts it through `NODE_EXTRA_CA_CERTS`, which adds it
to the authorities it knows, the tests of `make test-keycloak` through `SSL_CERT_FILE`, which makes it
their only authority, a browser by importing it, or by accepting the warning. uv also reads
`SSL_CERT_FILE`: `make test-keycloak` synchronises the environment of the back without it, then runs
the tests without resynchronising it (`uv run --no-sync`) — otherwise, on a workstation or a runner without
a cache, uv would no longer trust GitHub to download Python or the packages (#737). The API, inside
the network of the platform, reaches Keycloak in HTTP on `keycloak:8080`; the encryption of that
link belongs to EP-13 (WF-SEC-0010).
Redis is published on `127.0.0.1:6379` (`WATERFALL_REDIS_PORT`), for a front launched on the workstation
(#681), which reaches it through `redis://:<mot de passe>@127.0.0.1:6379/0`. Keycloak notifies the
closing of the sessions to that front through the back channel, at the address
`WATERFALL_FRONT_BACKCHANNEL` (`http://host.docker.internal:3000` by default, the host as seen from its
container), distinct from `WATERFALL_FRONT_ADDRESS`, that of the browser: the front then listens
on every interface of the workstation, not on the loopback alone. Both addresses are written
into the realm when it is applied, and `make e2e-service` replaces them with those of the front of its
paths, until the next `service-up`. Mailpit
shows the emails on `http://127.0.0.1:8025`. The development realm adds a test OpenLDAP
directory and a second realm, `external`, which plays the external provider: their accounts
and their passwords, development values, are in `deploy/keycloak/development/`. It
also adds `waterfall-test`, a public client that accepts a password outside the page of the
realm, for the tokens the tests of the platform need: `admin-cli`, which Keycloak
creates in each realm, no longer accepts one (#644), and its tokens are not for the API, for lack of
the `waterfall-api` audience. These files are applied after the realm, under a remote state of their own
(`--import.cache.key=development`, service `keycloak-realm`): keycloak-config-cli deletes the
clients its state names and that the files it applies do not declare, and without that the
test client would take those of the realm with it.
The directory keeps its data in a volume, like the databases: bootstrapped again, it would give its
people other identifiers than those Keycloak keeps; `WATERFALL_RESET_DATA=yes` deletes it
with them.

`BASE` is `origin/main` by default; a lot is compared with the branch of its epic.

`make lot-size BASE=origin/epic/EP-nn` measures a lot: the lines of its diff, separated into
production code, tests and the rest (documentation, configuration, contract), the generated
files set apart. The pull request puts that number next to the estimate of its issue; an
overrun makes nothing fail (README of the roadmap, section « Lots »).

## The chain

The chain is made of GitHub Actions workflows (`.github/workflows/`):

- `ci.yml` decides the families a pull request touches (`make changes`), calls the
  workflow of each, and ends with the **gate** (`gate`), which judges the whole
  (`make gate`): it fails if a job failed or was cancelled, and a job skipped
  because its family is not touched is not a failure. The gate is the only check
  that the branch protection requires: a required check that does not run for lack of a
  touched file would stay « pending » and would block the merge.
- one workflow per family — `repo.yml`, `spec.yml`, `contract.yml`… —, which installs its
  tools and calls `make check-<famille>`. `repo` runs on every change. The
  front has two, which run side by side (#492): `front.yml`, everything except the end-to-end
  paths (`make check-front-code`), and `e2e.yml`, the paths and the measure of §4.6.2,
  at the full tier only (`make e2e`, `make e2e-measure` and `make prerendered-front`, on
  the build the `front-build` job of `ci.yml` made, « on one single build of the front »); on
  a workstation, `make check-front` chains the two
  halves, `check-front-code` then `check-front-e2e`.
  `front.yml` spreads its work over several runners. One holds the client, the lint, the
  types, the catalogues and, at the fast tier, the production build
  (`make check-front-static`). Three play the unit tests, which occupy every core
  of a runner (`make check-front-tests`): the guards that run ESLint, a minute or more
  each, on one (`SHARD=lint`, the `lint` project of `frontend/vitest.config.ts`), the other
  tests in two halves on the other two (`SHARD=1/2`, `SHARD=2/2`). Vitest spreads whole
  files by the digest of their path, and the three guards fell into the same
  shard. Vitest takes there one worker per processor minus one, as it does by itself outside
  watch mode, four at most (`workers`, `frontend/vitest.config.ts`, #1474): the processor
  left is that of the main process, which gathers the results and the coverage of the
  workers; a runner, four processors, therefore plays on three. The workstation, twelve processors,
  gained nothing beyond four, and every test ran slower there, a test of the grid,
  under one second alone, beyond its five seconds under coverage. On four cores of the
  workstation, the coverage of the `2/2` half took 121 s on four workers and 131 s on three,
  but 29 of its tests exceeded one second on four, 11 on three. `structure-busy.dom.test.tsx`
  and `planning-entry.dom.test.tsx` hide the columns they do not put to the proof, the Gantt first:
  the whole grid, rendered two or three times at each gesture, doubled their duration. At the
  full tier, one last runner gathers the coverage of the three shards and
  holds it to its thresholds (`make coverage-front-merge`). ESLint keeps its cache, by the content
  of each file (`pnpm lint`, `actions/cache`): without it, it takes a minute.
  `front-cache.yml` writes that cache and the pnpm store after each merge, on the branch
  whose caches the pull requests and the merge queue read: without it, they would
  find nothing.
  `keycloak.yml` builds the image of Keycloak and puts it to the proof on the service platform, its
  realm applied (`make check-keycloak`), at both tiers: the `keycloak` family wakes
  on `deploy/keycloak/`, on the files of the platform that start it, on
  its tests, on all the code of the back, of which its tests serve the API, and on the contract, against which
  they confront its responses (#671); on failure, the job prints the logs of Keycloak
  (`make service-logs`). `service.yml` plays the paths against the real service, at the full
  tier only (`make check-service`, that is `make e2e-service`, on the build of the front that
  the paths of `e2e.yml` share): the `service` family wakes
  on the front, the back, the contract and the files of the platform. It runs on the
  runner itself, not in the Playwright image: the paths reach the platform on the ports
  that Docker publishes on the runner, which a job container does not see; the browser is
  installed there with its system packages (`make e2e-browsers PLAYWRIGHT_INSTALL=--with-deps`).
  `front-image.yml` builds and starts the production image of the front, which `images.yml`
  publishes only after the merge, at both tiers (`make check-front-image`): the
  `front-image` family wakes on what makes it — `frontend/Dockerfile` and its `.dockerignore`,
  `next.config.ts`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and what its server
  checks at start, `src/instrumentation.ts`, `src/startup.ts`, `src/session/settings.ts`,
  `src/api/server.ts` —, and not on the
  code of the front, which the `front` family already builds; it costs a build of about
  a minute and a half. What is prerendered, the code of the pages decides it — a
  `layout.tsx` that would stop reading the cookies, a page that would read no value of the
  request —: the `front` family therefore asserts it itself, without Docker, on the manifest of its
  own build (`make prerendered-front`), after `make build-front` at the fast tier and
  after the build of the measure at the full tier; that build prerenders like that
  of the image, whose standalone output (`WATERFALL_STANDALONE=1`) changes only the packaging.
  The `front-image` family asserts that `/` answers with the settings of the `front` service of
  `compose.prod.yaml`, placeholder values for its secrets; that the front, started without
  one of the variables it cannot do without, stops naming it in its logs (#825);
  that the fake back of the mockup (`WATERFALL_AUTH=mock`) is refused without `WATERFALL_E2E` — the
  server stops at start, and says why —, and that `next build` prerendered
  (`.next/prerender-manifest.json`) only `/_global-error` and `/icon.svg`: no page that would read
  the environment is frozen at build.

Outside the pull requests, `images.yml` publishes the images (US-0430): at each push on `main` or
on an `epic/**` branch — at each merge, which the queue has already put to the proof —, it builds `front`,
`waterfall` (the API, the worker, its scheduling and the migrations, commands of one same
distribution) and `keycloak` (the extension, the themes and the realm, with nothing of
`deploy/keycloak/development/`), and pushes them to `ghcr.io/waterfall-project/…` (`make images
PUSH=yes`). Its only job asks for `packages: write`; the token goes only to the login to the
registry, and no build receives an argument or a secret (WF-SEC-0010):
`tools/tests/test_images.py` guards it, with the triggers and the tags.

- **The three first.** The three images are built before any push, and nothing is
  pushed if one fails; then every tag of the commit, and only afterwards those that
  move — the branch, the version —, so that a moving tag never designates images
  of two commits.
- **The version tag is immutable.** It is set only from `main`, once only, and
  for the three images together, which then come from one same commit: before setting it,
  the tool asks the registry, image by image, whether it already has `<image>:<version>`
  (`docker buildx imagetools inspect`). If it has it for none, the three take it; if it
  has it for the three, none takes it again, and the tags of the commit and of the branch are
  published alone: a merge into `main` that does not raise the version therefore does not republish it,
  and it is by raising `version` of `backend/pyproject.toml` (and of the front) that a publication
  sets a new one. Any other case — the registry has it for some only, after an
  interrupted publication, or does not answer clearly that it does not have it, like the `403` of ghcr
  for an absent or unreadable package — sets it on none: the tool publishes the tags of the
  commit and of the branch, then fails naming each image and what the registry said of it;
  the version is then settled by hand, or by raising it. An epic branch, which carries the same
  version, never sets it; the label `org.opencontainers.image.version` of an image that does not
  take the version tag says so (`0.1.0+epic-EP-03` outside `main`, `0.1.0+main` on
  `main` once the version is published). Each image also carries its own `title` and its `url`,
  which replace those of its base image.
- **What refuses a push.** A branch other than `main` or `epic/…`; a repository whose
  commit is not the one `IMAGE_COMMIT` names, or which is not clean in the contexts of the
  images (`git status --porcelain -- frontend backend deploy/keycloak`); a built image
  whose file system (`docker export`) contains a known development value — the
  `development-only` mark, which all those of `deploy/keycloak/development/` carry, and the
  workstation secrets of `.github/workflows/keycloak.yml`. The tool then names the value found,
  never the value itself. The search reads the archive of the container as it is: a value
  in a compressed file escapes it.
- **The last merge wins.** A publication waits for that of the previous merge on its
  branch, without cancelling it; but GitHub keeps only one pending run per group, and a
  third merge cancels the one that waits: the tag of the branch ends up on the last one, and
  an intermediate commit may have no image.
- **The production platform on the published images.** The `trial` job of `images.yml`, after
  the publication, pulls from the registry the images of the commit, by its digest, and plays
  `make production-trial` on them (`packages: read` to pull them): the production platform starts,
  bootstraps itself, and lets its first administrator in (WF-ARC-0050). A failure there says that a
  published image does not make a platform; it does not undo the publication.

The `production` family (`production.yml`) makes the same trial before the merge, at the full tier
only, in the queue: `make check-production` builds the three images like `images.yml`,
without pushing them, then starts the platform on them. It wakes on the files of the
production platform — `compose.prod.yaml`, `compose.prod.local.yaml`, `Caddyfile.prod`,
`production.env.example` —, on those it mounts from `deploy/compose/`, and on the trial itself,
`tools/src/wftools/production.py`; a change of what
the images are made of is put to the proof that way only after the merge, by `images.yml`. It costs the
build of the three images, that of Keycloak and of its extension above all, then the start of
Keycloak and the application of its realm.

The families, the paths that wake them, the generated paths and those of the tests are
declared in `tools/paths.toml`, and nowhere else. A path of `shared` — the
Makefile, `ci.yml`, the declaration itself and the code that reads it — wakes every
family. The rest of the tools wakes the families that use them: each names among its
paths its workflow, the local actions it takes and the modules of `wftools` its
checks run. `tools/tests/test_families.py` holds them against the Makefile, the workflows
and the Playwright harness, imports included: a module run by a family without
waking it makes `make check-repo` fail. The `repo` family, which runs on every change,
tests every tool.

Two tiers: the fast one at each push on a pull request (`pull_request`), the full one
in the merge queue (`merge_group`), on the result of the merge, before it is
accepted. The full tier adds what is slow — code coverage, then the end-to-end
tests; on a workstation, `make check-back TIER=full`. A pull request enters the queue through
the « Merge when ready » button, or through the `enqueuePullRequest` mutation of the GraphQL API:
`gh pr merge` cannot do it as long as auto-merge is disabled on the
repository. A branch without a merge queue runs the full tier by hand on the
branch of a lot, before merging it: `gh workflow run chain --ref <branche>`.

The full tier aims at under eight minutes in the queue for its longest job
(#492). The end-to-end paths, the longest half, go about it this way:

- **in the Playwright image** (`mcr.microsoft.com/playwright`), at the version of
  `@playwright/test` that `frontend/pnpm-lock.yaml` resolves, pinned by its digest
  (`container:` of `e2e.yml`): Chromium and its system packages are there, nothing comes from the
  Ubuntu mirror, whose throughput is not ours (#472). The job calls `make e2e`, which finds
  the browser of the image (`PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`), and not
  `make check-front-e2e`, which would install one. Raising `@playwright/test` raises the image with
  it, tag and digest: otherwise the paths stop at once on a browser
  not found, and `tools/tests/test_playwrightimage.py` fails before them, in `make check-repo`.
  The digest is that of the multi-architecture index of the tag, which the line
  `Digest:` of `docker buildx imagetools inspect mcr.microsoft.com/playwright:v<X>-noble` gives, or
  the `docker-content-digest` header of
  `curl -sI -H 'Accept: application/vnd.oci.image.index.v1+json' https://mcr.microsoft.com/v2/playwright/manifests/v<X>-noble`.
  The image has no `make`: its Ubuntu noble package is downloaded, pinned and
  verified by its digest, like pandoc;
- **spread over three runners** (`make e2e SHARD=i/3`, that is `playwright test --shard=i/3`),
  the measure of §4.6.2 on a fourth, alone (`make e2e-measure`), through a matrix none of whose
  shards cancels the others; the result of `e2e` is a failure as soon as a shard fails or
  is cancelled, and the gate with it. Three, because Playwright spreads whole files
  of paths, at an equal number of tests, and the longest weigh — except a file played test
  by test (`mode: "parallel"`), like `accessibility.spec.ts`, whose tests are spread one
  by one: before that file, in October 2026, the longest of three shards played about 140 s
  of paths on two workers, that of four 130 s, when each shard pays about two
  minutes of image, installation and servers. What the file adds can be read on the chain of
  the pull request of US-0200, and the choice is reconsidered when the paths lengthen: the durations
  per file can be read in the log of each shard;
- **on one single build of the front per run** (US-0590): the `front-build` job of `ci.yml`,
  which runs as soon as `e2e` or `service` runs, launches `make build-front` and uploads
  `frontend/.next` without its cache (`.next/cache`, which only a following build would read). The three
  shards, the measure and the paths of the service wait for it, download it where the build
  wrote it and play with `E2E_BUILT=1`, without rebuilding anything. It lives in `ci.yml` and not in
  one of the two workflows: `e2e.yml` and `service.yml` are two called workflows, and a `needs`
  does not join the jobs of one to those of the other; neither has any other
  trigger than that call, so that none builds the front. A failed build skips the
  two, and the gate, which waits for it too, fails. It builds on the runner, like `front.yml`, in
  Node 24: the shards start it in the Playwright image, in Node 24 too (its
  `NODE_VERSION`), on the same Ubuntu noble in amd64, and at another path of the workspace
  (`/__w/…` instead of `/home/runner/work/…`); `service.yml`, on the runner. The build does not depend
  on that path: only `required-server-files.json`, which the standalone output of the image reads and
  not `next start`, names it, and a build moved elsewhere, its original folder removed, serves its
  pages (checked on 2026-10-25 on the workstation, by moving the build; the proof in the chain
  will come from a run of `chain` on the branch of the lot).

The back follows the same model (#492, lever 5):

- PostgreSQL runs as a service of the job (`services:` of `back.yml`), in the image of the
  version the platform targets — that of `compose.service.yaml` —, pinned by its
  digest, with its health probe: the integration tests reach it on `localhost`, without
  Compose, through `WATERFALL_TEST_DATABASE_URL`; the digest is written in `back.yml` and in
  `compose.service.yaml`, and `tests/test_platform_images.py` fails if they diverge;
- the coverage, slower, runs only at the full tier, in place of the plain tests
  (`full-else` of the Makefile);
- the tests are spread over the cores of the runner, eight processes at most (`PYTEST_WORKERS`
  of the Makefile, pytest-xdist): 7 minutes in series on the chain in October 2026, under two
  on four cores. Each process creates its own database, its role and its bucket, with a unique name,
  and takes the Redis database that follows that of `WATERFALL_TEST_REDIS_URL` according to its rank
  (`tests/conftest.py`). The processes must collect the same tests: a test parameter
  is never drawn at random (a `uuid4()` in `parametrize`), it is fixed. The tests of
  Keycloak stay on one process: one of them restarts Keycloak.

Still to write, when the duration demands it:

- the paths against the real service (`service.yml`), which one single runner plays as long as they are
  short, are spread like those of `e2e.yml`, the platform started in each shard.

The images are built from a GitHub Actions cache (`type=gha`): the extension of
Keycloak compiled by Maven, the dependencies of the front and of the back are not redone at each
job. The `cache` job of `images.yml` writes it after each merge (`make build-cache`), on the
branch whose caches the pull requests read; `keycloak.yml`, `service.yml`,
`production.yml` and `front-image.yml` read it (`build-keycloak`, `wftools.images`,
`wftools.frontimage`). The local action `.github/actions/build-cache` opens it to them: it enables
the containerd image store, without which Docker's builder neither imports nor exports such a
cache, and restarts Docker — never in a job that has `services:`
(`tools/tests/test_images.py`); then it passes to the following steps the address and the token of the
cache, which the runner gives only to an action (`.github/actions/actions-runtime`, without displaying
anything). On a workstation, Docker ignores a `type=gha` cache. The publication (`publish`) reads
none: on the containerd store, an image would be pushed with its attestations, in another
format than the one published today.

Rules of the workflows:

- a third-party action is pinned by the digest of its commit, the version as a comment;
  Dependabot proposes their update every month (`.github/dependabot.yml`);
- each workflow declares `permissions: contents: read`, and asks for no more without
  a written reason;
- `actions/checkout` does not keep the token (`persist-credentials: false`);
- a tool downloaded outside an action is pinned by its version and verified by its
  digest, like pandoc in `spec.yml`.

_Check_: `make lint-workflows` (actionlint); the pinning and the permissions, the review.

The branch protection is a GitHub setting, made by the owner of the repository:
on `epic/*`, no direct push, the gate required, the merge queue; on `main`, the
gate is required only from the delivery of EP-01 on — GitHub reads the workflows in the
branch of a pull request, and a pull request to `main` created from before the chain would not
trigger it.

## Naming

The code, the tables, the columns, the variables, the paths and the console messages
are in English; the documentation is in French, like the specification. The names of the
objects of the domain are those of the correspondence table of §4.4.1 of the specification
(`estimate_line`, `cost_line`, `revision`…), and the conventions of the contract — `snake_case`,
`operationId` in `camelCase`, UUID identifiers — are in `docs/api/README.md`.

_Check_: no tool checks the language of a name; the review does.

## Headers and licences

Every code file begins with two lines, after the `#!` line if it has one:

<!-- REUSE-IgnoreStart -->

```text
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
```

<!-- REUSE-IgnoreEnd -->

in the comment syntax of the language. The name of the file does not appear there: it would become
wrong at the first rename; the first line of the docstring of the module says what it is for.
What cannot carry a comment, or would gain nothing from it — documentation, figures,
contract, templates, images, generated files — is declared in `REUSE.toml`. The
specification is declared there under CC BY-SA 4.0 and the interface contract under Apache-2.0
(`docs/legal/README.md`, « The decisions taken »); the code of conduct keeps its own
licence, CC BY 4.0.

A document that cites these two lines, like this one, frames them with
`REUSE-IgnoreStart` and `REUSE-IgnoreEnd`, failing which the tool would read them as the licence
of the document.

_Check_: `make reuse` fails on a file covered neither by a header nor by
`REUSE.toml`.

## Repository tools

The tools live in `tools/`, in Python, with their tests (`make test-tools`). Every tool
that needs the requirements reads them through `wftools.projection`, which reads the projection
`docs/spec/waterfall-spec.md`: one single reader, so that two tools cannot
diverge on what a requirement says. It compares the texts after normalisation — apostrophes
and typographic spaces made plain —, and splits a Vérif into sentences. The example of
§1.3.1, `WF-EXA-0010-A`, is not a requirement of the product: the tools exclude it.

_Check_: `make test-tools`.

## The roadmap and the requirements

The stories of `docs/roadmap` cite the requirements they implement, and their acceptance
criteria take up the Vérif of each **word for word**, as a criterion or as a deviation: they
are the test cases to come. `make roadmap` confronts the roadmap with the document, and fails:

- on an unknown identifier, or one with a revision index the document has gone past, in an
  epic table as in a story;
- on a sentence of the Vérif of a cited requirement, absent from the story or truncated — a sentence is
  cited whole, full stop included; apostrophes and typographic spaces do not
  count;
- on a requirement of the table of an epic that none of its stories cites, unless the epic is
  `à planifier`;
- on a requirement that no epic closes, or that several close.

It lists, without failing, the F0 requirements that no story cites yet: their number decreases as
the stories of the following epics are written. The tool reads only the repository: the state of the
issues is not its business.

It also fails on a `make` command that an agent cites (`.claude/agents/`,
`docs/dev/agents.md`) and that the Makefile does not have: a renamed target does not let an agent
call a command that has disappeared.

_Check_: `make roadmap`, `roadmap` family of the chain, woken also by a
change of the projection or of the agents.

## Comments

A comment says why, not what the code does: the reason for a choice, an invariant,
an edge case. It is in English, like the code.

_Check_: no tool judges what a comment says; the review does. The form of the
docstrings, commented-out code and the `TODO`s — always `TODO(#12): …`, with the number of
the issue — are checked: see « Lint, types and format ».

## Lint, types and format

What the specification calls static analysis (WF-QUA-0030): everything is blocking, and no
warning is tolerated; what does not deserve to block is removed from the rule set.

**Python** — the back and the repository tools share one single rule set,
`ruff.toml`, at the root:

- every rule of Ruff is active; those that are removed are listed, each
  with its reason, and the history of the file shows each removal;
- cyclomatic complexity under 15 per function (`C901`, maximum 14);
- the SPDX header (`CPY001`), a one-line docstring for what is public (`D1`,
  PEP 257 convention; neither the tests nor the special methods ask for one), no commented-out
  code (`ERA001`), a `TODO` that cites its issue (`TD003`);
- Pyright in strict mode (`[tool.pyright]` of each project), `# type: ignore` not honoured.

**No rule is waived by a comment in the code.** An exception, if one is needed,
is written in the configuration of the tool — `per-file-ignores` of `ruff.toml` —, with its
reason. No source file exceeds 1,000 lines, blank lines and comments included;
generated files are excluded from it.

_Checks_: `make lint-back`, `make typecheck-back`, `make lint-tools`,
`make typecheck-tools`; `make sources` for the exemption comments and the size of the
files, over the whole repository. The tools of `docs/spec/tools` and `docs/api/tools` follow
the same rules as those of `tools/`; an exception, if one is needed, is declared in
`tools/paths.toml`, with its reason and what will lift it.

**TypeScript** — the front has its rule set in `frontend/eslint.config.mjs`:

- the recommended configurations of ESLint, of Next.js (`core-web-vitals`) and of
  typescript-eslint in strict mode, with type information; what is added to them
  or removed from them is written in the file, with its reason;
- cyclomatic complexity under 15 (`complexity`, maximum 14); 1,000 lines at most
  per file (`max-lines`);
- a JSDoc docstring for what is exported, without a type — TypeScript carries them
  (`jsdoc/no-types`) — and without a section per parameter, which would repeat the signature;
- none of the known means of calling the network outside `src/api/client.ts` — `fetch`,
  `XMLHttpRequest`, `WebSocket`, `EventSource`, nor an imported http client —, and no
  import of `src/api/` in a client component outside the server actions: the API is
  called only through the generated client, from the server
  (WF-ARC-0020);
- no text meant for the user written in the code (WF-QUA-0070): see « Translation
  keys »;
- Prettier for the format (`frontend/.prettierrc.json`); ESLint runs with
  `--max-warnings 0`.

The configuration comments in the code are not honoured (`noInlineConfig`) and
`make sources` refuses them. A `TODO` cites its issue, in the same form as in Python:
`TODO(#12): …`; the other waiting labels are refused — it is `make sources` that
checks it, ESLint having no equivalent of the `TD` and `FIX` rules of Ruff.

_Checks_: `make lint-front` (ESLint, Prettier), `make typecheck-front`, `make sources`.

**Contract** — `docs/api/redocly.yaml` extends `recommended-strict`: every rule of Redocly
blocks. An operation to which a rule does not apply — a probe without a 4xx response,
an OIDC redirect without a 2xx response — is declared in `docs/api/.redocly.lint-ignore.yaml`,
with its reason.

_Check_: `make lint-openapi`.

## Coding rules

How each language is written: [Python](python.md), for the back and the tools,
[TypeScript](typescript.md), for the front, and [Java](java.md), for the Keycloak extension.
Each first names the rule sets of the tools, by reference, then the design rules
that no tool checks, each with its reason, and ends with the defects already met,
which the review looks for by name. The
SQL and the migrations have their own: [SQL](sql.md), for the tables, the types, the constraints,
the migrations and the locks.

## Tests

- **A test that cites its requirement** — see below.
- **A test that takes up a numeric example** — see below.
- **An end-to-end path** — see below.
- **A test against PostgreSQL** — see below.
- **A test against Redis** — see below.
- **A test against the object storage** — see below.

The responses of the fake back are the examples of the contract, as they are. Two exceptions, and
only those. A test may remove a permission from an example session to exercise a combination
that no account of the witness carries (author's decision, 2026-10-09); it adds and rewrites
nothing else. It removes it from the session the page reads (`requestSession` doubled, as L43c does
for the backups, `app/reference/costs/page.test.tsx`), never by rewriting a response of the
client. And a test may render a component on a counterfactual variant of an example line
— one value changed, the rest of the line kept —, when no example of the contract carries the case
it exercises: the variant is passed to the component as a prop, never served as a response of the
client, and the test says which example it comes from and what it changes (EP-14/L45a). Precedents: « SP-REC », the
created sub-project, which no marked revision cites, relieved of its actual costs, its deletion
listed as available as the server would list it then, for the deletion of a sub-project, the two
of the witness being cited and loaded (EP-14/L42l); the sub-project commands removed from a line
(EP-14/L44e, `subproject-commands.dom.test.tsx`) — those of a closed project, none since US-0702/L3,
have their example since L42o (`subprojects_completed`), which replaces the variant (EP-14/L52) —; and the gap to the previous review absent from the remaining to commit
(`remaining-summary.test.tsx`).

### A test that cites its requirement

Every F0 requirement is covered by at least one test that cites it by its full identifier,
revision index included (WF-QUA-0010).

- **Python**: the marker `@pytest.mark.requirement("WF-ARC-0010-A")`, on the test, on its
  class, or on the module (`pytestmark = pytest.mark.requirement(...)`) when the whole
  file carries the same requirement. The marker is declared: a typo in its name
  makes Pytest fail.
- **TypeScript** — Vitest or Playwright: the identifier between square brackets in the title,
  `it("lit une grille [WF-QUA-0050-A]", …)`.

A test cites the requirement whose Vérif it exercises, not the one it talks about. A test that
covers no requirement — a tool, an implementation detail — cites none.

_Checks_: `make requirements` reads the citations in the test files, without running
them, and publishes the report — each F0 requirement with the tests that cover it and their
family, the one `tools/paths.toml` declares for their path in its `[tests]` table:
end to end against the service (`frontend/e2e/service/**`, which takes precedence over the other paths),
end to end (`frontend/e2e/**`, which takes precedence over the rest of `frontend/`), front, back,
keycloak (the JUnit tests of the extension, which cite no requirement), tools — in the summary
of the chain's job; a citation of an unknown identifier, or
of a revision index the document has moved past, makes it fail. The tests of the front
cite requirements that other epics close, by the sentence of the Vérif they exercise;
a requirement that only the front and the end-to-end tests cite, and that an epic closes without having
`front` as its only family — according to the « Exigences réalisées » table of the roadmap and the
`famille` field of its front matter —, is counted apart, « covered by the front alone »,
and does not count as covered. A path played against the service, for its part, goes through the back: it
proves what the back closes, like the back's own tests (US-0340). `make requirements-release` fails in addition on any F0 requirement
not covered, or covered by the front alone, naming it: it is the command of the
release of a version. A requirement whose Vérif opens with « Vérifiée en recette »
expects an acceptance report, whose form is not yet defined: the report says so.

### A test against PostgreSQL

An integration test of the back joins the real database, PostgreSQL, never another in its place
(`python.md`, « Les tests »). The variable `WATERFALL_TEST_DATABASE_URL` names a server and a
role that can create databases and roles, a superuser
(`postgresql://rôle@hôte:5432/postgres`): at each test session, the `database_url` fixture
(`backend/tests/conftest.py`) creates there a database with a unique name, applies the migrations to it, and
drops it at the end, with the service role the migrations created for it. The `database`
fixture returns this database as the service sees it — through a login role that is a member of the
service role of this database, created for the session (sql.md, « Le rôle du service ») —, and
deletes after each test the rows of every table the `Base` declares, as
owner, audit log included, which its trigger does not protect from a superuser
who disables the triggers — except those a migration writes, the catalogue of permissions,
which its table marks (`WRITTEN_BY_MIGRATION` in its `info`); `session` returns a session the
test rolls back.

- **In the chain**, `back.yml` starts PostgreSQL as a service of the job and sets the variable.
- **On a workstation**, two ways: `make service-up` (with the secrets of the platform in
  the environment, « Commands »), whose PostgreSQL listens on `127.0.0.1:5432` — the variable
  is then
  `postgresql://waterfall:<mot de passe>@127.0.0.1:5432/postgres` —; or a local server,
  created for the occasion (`initdb -E UTF8`, `pg_ctl start`) and deleted afterwards.
- **Without the variable**, a test that needs the database **fails** saying so, and does not pass
  silently. The tests of `examples/`, sockets closed, do not need it.
- A test that needs two instances of the service starts two processes (`subprocess`), each
  on its own connection: Alembic's environment, for its part, is not re-entrant, and runs in one
  process at a time.

### A test against the object storage

A backup is tested against a real object storage, Garage, the image of the service platform
(PBS-3.3): the variable `WATERFALL_TEST_STORAGE_URL` names it with a key that can create a
bucket, `http://<clé>:<secret>@127.0.0.1:3900`. The `backups_bucket` fixture
(`backend/tests/conftest.py`) creates a bucket there for the test session, and empties then
deletes it at the end. The backups call `pg_dump` and `pg_restore` in `/usr/bin`, those of
Debian and Ubuntu, of a version at least equal to the server's. They dump the databases like
the worker of the platform, through a backup role that the `backup_role` fixture
(`backend/tests/conftest.py`) creates for the session, a member of `pg_read_all_data` (#895).

- **In the chain**, `back.yml` starts Garage by `docker run` — a service of the job does not
  receive the arguments it asks for — and sets the variable.
- **On a workstation**, a throwaway Garage is enough, with the settings of the platform:
  `docker run -d --rm --name wf-test-storage -p 127.0.0.1:3900:3900 -v "$PWD/deploy/compose/garage.toml:/etc/garage.toml:ro" -e GARAGE_RPC_SECRET=<64 chiffres hexadécimaux> -e GARAGE_DEFAULT_ACCESS_KEY=GK000000000000000000000001 -e GARAGE_DEFAULT_SECRET_KEY=<secret> dxflrs/garage:v2.4.1 /garage server --single-node --default-access-key`.
- **Without the variable**, a test that needs the storage **fails** saying so.

### A test against Redis

The session of the front and the task queue of the back are tested against a real Redis, never a
double: the variable `WATERFALL_TEST_REDIS_URL` names it (`redis://127.0.0.1:6379/0`), a database
that the tests alone use. On the front side, `withTestRedis()` (`frontend/src/test/session.ts`)
points the session store at it for the duration of a test file; each key is drawn at
random: the files that run together do not meet, and the keys expire
by themselves. On the back side, the `queue` fixture (`backend/tests/conftest.py`) opens the queue on a stream
of its own, deleted after the test, and `platform_queue` on the one of the whole installation, which the
commands of the platform use, emptied before and after. The tests of the back running on
several processes, each takes the database that follows the variable's according to its rank (`gw0` its
own, `gw7` the seventh after): the stream of the whole installation is never emptied from under
another's feet. No test flushes the server.

- **In the chain**, `front.yml` and `back.yml` start Redis as a service of the job and set the
  variable.
- **On a workstation**, a throwaway Redis is enough:
  `docker run -d --rm --name wf-test-redis -p 127.0.0.1:6379:6379 redis:7-alpine`.
- **Without the variable**, a test that needs Redis **fails** saying so, and does not pass
  silently.

Keycloak, for its part, is not in the tests of the front: `frontend/src/test/identity-provider.ts` answers
Next's server like the `waterfall` realm — single-use code for its verifier, refresh token
rotated at each use and refused at the second, tokens signed with a key of its own.
`make test-keycloak` proves against the real realm the exchange of the code with its verifier, the
refusal of a refresh token already used and the closing of an account's sessions; the
logout token that Keycloak posts to the front, the path against the service of US-0340
(`frontend/e2e/service/session.spec.ts`); `refresh_expires_in`, the two hours of an inactive
session, and whatever else US-0350 asks of the realm — each kind of account, the password,
the lockout, the link —, `backend/tests/test_keycloak_sign_in.py`; the return to the intended screen,
the paths against the service of US-0350/L5b (#849).

### An end-to-end path

A path is written under `frontend/e2e/`, in Playwright, and cites in its title the requirement
it covers: `test("… [WF-QUA-0050-A]", …)`. It finds the elements by their role and their
accessible name (`getByRole`), as a user sees them, never by a CSS class.

A page opened by its address is displayed before React has hydrated it: a link followed then
loads its screen as a whole document, but a click on a button, a key in a cell, get
lost (#471). A path therefore opens a project screen with `openHydrated`
(`frontend/e2e/hydration.ts`), which waits for the witness of hydration: the cookie `wf_last_project`,
which the shell writes only in an effect. Outside a project, nothing witnesses it: the gesture is repeated
until React answers it, without undoing the one it has already received (`setExpanded`, `openMenu`, and
`sortUntilAddress` for a sort, which never hurries blindly). A grid screen is waited for up to
the bound of grid screens, fifteen seconds (`WORKING`, #315, #419), whether a click reaches it or
reloads it (a sort, a filter, a search, the detail of a line). A grid screen is a dense
grid — estimate, planning, remaining to commit, risks, actual costs, portfolio —, or a screen that reads
the structure of a thousand tasks (`listNodes`): the Kanban, the tree, the timelines. The
comparison of two revisions joins them, for the time of a decision: it renders its 2,770
modifications in a plain table, rendered on the server, which exceeds five seconds in development
(finding #624 of EP-14/L45a, to be decided — accepted, or moved onto the dense grid): from the click to
the address, for five megabytes of response, about four seconds on the server, up to ten when another
path loads it, and three or four in the browser, the fake back answering in a few
tens of milliseconds (#729). A path that renders thousands of lines this way outside a
virtualised grid may keep its trace without DOM snapshots (`snapshots: false`), and only
after a measurement that shows what they cost within the bound — for the comparison, about two
seconds, which took it up to eleven seconds out of fifteen on an idle workstation. The trace loses the
DOM, the network, the accessibility tree and the screenshot of each action, and keeps only the actions,
their sources and the film of the screen: the path itself says, in an annotation, the duration of what it
waits for (`test.info().annotations`). The remedy mitigates, it settles nothing: the rest lies with the screen.
The risks and the actual costs, reloaded, have exceeded five seconds under load: the measurements are
recorded in #500, which remains to be decided. Every other screen keeps the five seconds of an
assertion. A path that chains three of these bounds, opening included, exceeds the thirty
seconds of a test, and takes `test.slow()`. A grid line that is checked is in the viewport:
beyond the lines in view at opening, the path scrolls to it (`scrollToPosition`,
`frontend/e2e/scroll.ts`) rather than counting on the margin the grid renders around the
viewport.

`make e2e`: Playwright starts the fake back (`make mock`) and the front, plays the paths
in Chromium, then stops both — it signals their whole process group, without which
the servers that `make` and `pnpm` start would survive. It always starts its own
servers, on ports of its own — 4110 for the fake back, 3100 for the front —, never those of
`make dev`, and its fake back serves a variant of the contract written under `frontend/.e2e/`, which
`make dev` does not read: a port already taken makes the launch fail saying so. `E2E_API_PORT`
and `E2E_FRONT_PORT` move the ports, for two copies of the repository on the same workstation — the front of the
paths takes as many as it has workers, starting from it (below); a port
that is not an integer from 1 to 65535 is refused. `make e2e-browsers` installs the
browser. `make e2e SHARD=i/N` plays only the i-th of N shards of the paths, like
each of the chain's runners (« The chain »), and `make e2e WORKERS=<n>` plays them on `n` workers
(`E2E_WORKERS`, which `playwright.config.ts` reads; an integer of at least 1, nothing else), fewer than
Playwright takes on its own — half the processors — on a loaded workstation, where
paths fail by timeout (#736). With `WATERFALL_API_ADDRESS`, the harness plays
against the API it names and starts no fake back.

**The paths are played against the front built for production** (US-0590), the one
users open: one `next start` server per worker of the paths, on `E2E_FRONT_PORT`
and the ports that follow it, each worker playing against the one of its place among the workers
(`TEST_PARALLEL_INDEX`); a single one for the measurement of the second, played on one worker, for the
paths of the service, whose realm knows the address of only one front, and for the development
server. The development server rendered the pages of the four workers in series, beyond
the five seconds of an assertion (#1262), and rose above 9 GB after compiling every
route (#1309). A single built front, one process, rendered them in series too, faster:
busy three quarters of the time under six workers, it left the risks screen loading
five seconds after the click, three times out of sixty (#1477); one front per worker, none out of
sixty. Playwright starts the fronts one after the other, and the first builds the front when
it is not built. It starts as many as there are workers even for a single file
(`make e2e TESTS=…`) or a shard: each answers in about a second on the workstation, so
that a replay under four workers waits three or four seconds longer for its first path. The
harness does not know, when reading its configuration, how many workers the replay will occupy: a cap
at the number of files would give a single front to the four workers of a file played test by test
(`mode: "parallel"`, `accessibility.spec.ts`), the congestion of #1477; `WORKERS=1` starts a
single one. `make e2e`, `make e2e-measure` and
`make e2e-service` first build the front like `make build-front`, with no reachable API
(#131) — the same build therefore serves the fake back and the real service —, then launch Playwright, which
starts it; locally, Next's cache (`frontend/.next/cache`) shortens the following builds.
`E2E_BUILT=1` says the front is already built: neither the target nor the harness rebuild it, which is what
the chain does, building it once per run for all its parts — the shards of the
paths, the measurement and the paths of the service (`front-build`, « The chain »). Without it, the
harness launched outside the Makefile (`pnpm exec playwright test`) builds the front itself before
starting it.

`E2E_DEV_SERVER=1` replays locally the paths against the development server (`next dev`),
without rebuilding the front at each replay: `make e2e E2E_DEV_SERVER=1 TESTS=e2e/<fichier>`, or
`make e2e-service E2E_DEV_SERVER=1`. The measurement never follows it: it is always played against the
built front, so that `make e2e E2E_DEV_SERVER=1` leaves it aside, and that
`make e2e-measure` builds the front anyway. Set in the chain (`CI` defined), it makes
the launch fail, with a message that says so. Nothing warms up the routes for it: a
local replay is played on few files, and the development server compiles a route at its
first request, which the first assertion that waits for it may exceed. `compile`
(`frontend/e2e/compile.ts`) remains for a path that first compiles what it reaches.

The warm-up of the routes (`e2e/warm-up.ts`, #1145), which requested each route from the development
server before the first path, is removed with its tests: the built front compiles
nothing on demand. A failure of the API, of the realm or of Redis is therefore read at the first path that
reaches it, and no longer before it (#1265).

**No failure is tolerated** (US-0590b, #1460): at the local full tier as in the chain, the
failure of a path is a failure, even if it passes replayed alone. The provisional rule of #1145, which
let a lot merge whose paths of #1145 and #1263 fell at the local tier then
passed replayed alone, disappeared with US-0590b, which fixed these failures at their cause: the built
front, one per worker (above), and the lightened keyboard walk (below). A path
that falls is fixed at its cause, never by a longer wait, a `retries`, a `fixme` or a
`skip`.

The front of the harness opens a connection of its own for each request to the API
(`WATERFALL_API_CONNECTIONS=closed`, « The API client »): the API there is always Prism, fake
back or proxy of the contract, which closes a connection idle for five seconds, and the loaded
development server sent a request on a connection Prism had just closed
(`UND_ERR_SOCKET: other side closed`, then `Unreachable` in `readOrFail`, #1145). The harness also
sets `WATERFALL_E2E=1` on the front, against the fake back as against the service: the built front
admits the fixed token of the fake back only on that condition, and does not report the `closed` connections
(#1265).

`make e2e-service` plays against the real service the paths of the Playwright project `service`
(`frontend/e2e/service/`, US-0340), alongside those of the fake back, which remain. It starts the
service platform (`make service-up`), its realm applied with the address of the front of the
paths, `http://127.0.0.1:3100` (`WATERFALL_FRONT_ADDRESS`, which follows `E2E_FRONT_PORT`), and
the one through which Keycloak reaches it from its container, `http://host.docker.internal:3100`
(`WATERFALL_FRONT_BACKCHANNEL`), whatever the ones the environment exports; then
Prism as a proxy between the front and the API
(`prism proxy --errors`, service `contract-proxy`, on `127.0.0.1:4210`, which
`WATERFALL_PROXY_PORT` moves), which serves the variant of the fake back written in
`docs/api/waterfall.proxy.json`: a response outside its schema becomes a 500 error
(`VIOLATIONS`), an address outside the contract a 404 (`NO_PATH_MATCHED_ERROR`), a request outside
the contract a 422, and Prism writes each one to its log under its request. Prism requires no
token there: the service authenticates, and its refusal passes as it is, checked against the contract. It finally launches
Playwright with, in its environment — never on the command line, where the password of
Redis could be read —, `E2E_PART=service`, `WATERFALL_API_ADDRESS` (the proxy),
`E2E_CONTRACT_PROXY` (its container), `E2E_SERVICE_DATABASE` (PostgreSQL's),
`WATERFALL_KEYCLOAK_ADDRESS`, `WATERFALL_FRONT_ADDRESS`,
`WATERFALL_REDIS_URL` (the Redis of the platform) and `NODE_EXTRA_CA_CERTS` (the root of the
authority of Keycloak's front end); the secret of the front's client, and that of Keycloak's
administrator, come from the environment. The platform stays up: `make service-down`
stops it. Before Playwright, it bootstraps the platform (`waterfall-api install`, service `install`,
US-0420): the first administrator, `administrateur@waterfall.test` (`E2E_ADMIN_EMAIL`), carries the
role « Administrateur », and the link that sets their password, valid until it is used, is
in `E2E_INSTALLATION_LINK` — empty as soon as a path has used it, the administrator
signing in afterwards with the constant password of the paths (`LOCAL_PASSWORD`,
`frontend/e2e/service/realm.ts`). A precondition:
`E2E_ADMIN_EMAIL` must be the address with which the platform was bootstrapped the first time.
A relaunch installs nothing new and ignores another address (`installation.admin_email_ignored`
in its logs): on a platform bootstrapped with another one, by `make service-install` and another
`WATERFALL_ADMIN_EMAIL`, the paths would look for an administrator who does not exist. One must then
give the first address to `E2E_ADMIN_EMAIL`, or start again from an empty platform
(`make service-down WATERFALL_RESET_DATA=yes`).

The paths are played in five Playwright projects. `installation` first
(`installation.setup.ts`, WF-EXP-0020): the link serves only once, and this path sets the
administrator's password, signs in, and observes their role, the three predefined roles and the
catalogue. `service` next, on several workers (#730): each path signs in with a
local account of its own, which the administrator creates through the API (`createUser`, `createPasswordSetupLink`) and
whose password it sets through the returned link, or with an account whose sessions no other path
closes — the administrator themselves, for the accounts and roles screens and for the
audit log (`accounts.spec.ts`, `roles.spec.ts`, `audit.spec.ts`). The administrator gives the local accounts their
roles through the API; the person of the test directory,
`dominique.annuaire@waterfall.test`, and the one of the external provider, `camille.externe`
(`deploy/keycloak/development/`), whom the API admits without a role at their first request (WF-ADM-0180) and
whom only `sign-in.spec.ts` uses, receive theirs by a write into the platform's database
(`grantRole`), once admitted. No path gives any account other than the administrator the
two administration permissions — `give` refuses it —, and none renames or changes a predefined
role: the `LAST_ADMINISTRATOR` refusals of the roles screen and of the accounts screen depend on it
(`roles.spec.ts`). The administrator's token, which lives five minutes, is requested again when it is
more than four minutes old.

All the workers sign the administrator in, and the realm refuses the credentials of an account
it is already verifying, as if it were locked (`user_temporarily_disabled`, with no
failure counted): a sign-in waits its turn (`oneAtATime`, `realm.ts`), under a lock — a
directory of the system's temporary folder, named after the run and the account —, which it holds
until the realm's answer, awaited for fifteen seconds at most, well below the thirty that the
other workers wait for the lock. A table screen of the administration is opened by an address
that states its search, empty if need be (`?search=`): a silent address would restore the search or
the filters the administrator kept on another path, since they are the same on all of them.
`realm` next, on a single worker, once the others are finished: the paths marked `@realm-wide`,
which shorten a duration of the realm, which every account reads. `restoration` after them, alone: the
paths marked `@platform-wide`, which restore the whole platform and close all its
sessions (US-0440, `backups.spec.ts`). `contract` last, the teardown of `installation`: the guard
of the contract of the whole run.

The project `service` plays only `frontend/e2e/service/`, which the other projects leave alone: against
the built front, like the others, without `WATERFALL_AUTH=mock` — the real sign-in, through the
realm —, listening on every interface of the workstation, from where Keycloak reaches its back
channel (#681), and with the server actions key without which the built front does not start
outside the fake back (`NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, drawn for the run if the environment
does not give one); the browser accepts the certificate of Keycloak's front end
(`ignoreHTTPSErrors`), which Next's server gets from `NODE_EXTRA_CA_CERTS`. These requests to
the API, Next's server makes them, out of the browser's sight, and a screen can survive
one of them: a file of these paths is held to the contract by `heldToTheContract()`
(`frontend/e2e/service/contract.ts`), which reads the proxy's log through Docker and fails on
every line where Prism writes `Request terminated with error:` — its own errors as well as those of the
proxy, unreadable body or unreachable API (WF-ARC-0060). Prism writes its line once the
response is returned, and Next's server still reads the API after the last assertion: each worker
reads each line once — by `docker logs --since`, from the moment where it had stopped, and
from the start of its first file —; a path fails on the errors written up to its end, a
later error makes the worker's next one fail. The log does not say which worker requested
what: an error makes the path of every worker that reads it fail, the one that caused it among
them. The project `contract` (`contract.teardown.ts`) finally re-reads the whole log of the run, from
its start (`E2E_SERVICE_STARTED`, which `playwright.config.ts` sets), once the proxy has gone quiet —
nothing but the health check for two seconds, the last line of a response, which
does not name its request, being one only if it follows that of a health check's response (#735) —:
the errors after a worker's last path make it fail, and those a path has
already reported, again. This start is the last line the proxy wrote before the run
(`docker logs --timestamps --tail 1`, `frontend/e2e/service/proxy-log.ts`), and every moment the
paths compare is the one Docker gave to a line, never the workstation's clock, which a
virtual machine lets drift from its own; the guard proves its window: at least one line read
— the health check writes one every two seconds —, and the refusal of the address outside the
contract when its path has played. A path shows it (`contract.spec.ts`): an address outside the
contract (`OUTSIDE`), which the guard alone reads, refused; every other reader leaves it to the guard. A status
the operation does not declare is not one for Prism: the response passes, with the header
`sl-violations` of severity `Warning`, which its log does not tie to its request — today these are
the 404s of the operations the shell reads and the service does not serve yet. The
tests of the service hold its statuses to the contract (`ContractClient`), the paths its bodies
(#726). The sign-in paths are played there (US-0350): signing in, signing out on all
one's workstations, the lost session of the front included, no token in the browser, the closing of the
sessions by the realm (`session.spec.ts`); each kind of account acting according to its roles, the
inactive session that brings back to the sign-in then to the intended screen, the account not admitted
(`sign-in.spec.ts`); the local account created, its setup link, the password rules and the
lockout (`password.spec.ts`); the language decided by the browser until the account
chooses one, then found again from one workstation to another, applied without signing in again, the avatar uploaded,
replaced and removed, the hidden columns, the widths and the filters of the tables found again on
reopening, each account seeing its own (`account.spec.ts`, US-0400) — these settings read in the
database (`gridPreferences`), where the front writes them after a pause; a role assignment made by
the service, which the audit log, filtered on its author and its action, presents to each reader
in their language (`audit.spec.ts`); the bootstrap (`installation.setup.ts`), the accounts screen
(`accounts.spec.ts`) and the roles screen (`roles.spec.ts`). They set the realm through its
administration API, as administrator of the `master` realm (`WATERFALL_KEYCLOAK_ADMIN_PASSWORD`) — a
duration shortened for the time of a path, which `service-up` gives back to the realm anyway next time —,
and request a token for the API through the flow of the front's client (`WATERFALL_FRONT_CLIENT_SECRET`).

A limit of the paths against the service: Prism, as a proxy of the contract, reads every body as
text and alters binary bodies — every byte beyond `0x7f` of an `application/octet-stream` request or
response becomes U+FFFD (#973, #1025). The paths therefore exercise neither
the download nor the upload of an archive byte for byte: `backups.spec.ts` checks of
the downloaded archive only its name and its non-zero size, and restores the backup of the list,
not an upload. The restoration of an upload is proven by the tests of the service
(`backend/tests/test_uploads.py`). Moving the binary operations out of Prism is deferred to
EP-13.

The second of §4.6.2 — opening a grid of a thousand tasks — is measured in
`frontend/e2e/opening.spec.ts` (US-0110, US-0220), on the volume structure the fake
back serves, for the estimate grid and for the planning grid; the fake back serves the planning without
taking `kinds=task` into account, and its measurement is pessimistic: it bears on six thousand lines, and
not on the thousand tasks the service will return. An opening goes from its start — the start of
the navigation for a grid opened by its address, the click for a grid opened from
the sidebar — to the usable grid, that is, drawn and hydrated: drawn,
the first frame where the header of its columns, the legend of its totals and the first line
of the response are entirely within the viewport; hydrated, the first frame where the whole
grid is rendered by React — the server renders its first screen, which may be displayed before
a click does anything there —, which the path recognises by the keys React sets, while hydrating it,
on the last element of the grid, the last cell of its totals (`__reactProps$…`): an
internal detail of React, read by the test alone. The later of the two
instants is compared to the second. A script handed to each document watches each frame and notes
the instants on the system clock (`performance.timeOrigin`), which a replaced document does not
lose: neither Playwright's round trips nor its waiting count there. It is played against
the front built for production, the one of the paths, and never against the development
server, even under `E2E_DEV_SERVER=1`: the latter compiles a route at its first request and
renders with React's development checks — it would tell the speed of the developer's
workstation. Before each series of five
openings — five by the address, five from the sidebar, for each grid —, one
opening is not measured: the first loading of the server's modules does not count, and
the browser's cache is warm, as for a user who has already opened the application.
Each opening starts only once the previous one is entirely served, prefetches
included — the grid hydrated, its sidebar links still request from the server the
screens they lead to, and a navigation started before their response would cut them off while the
server renders them, within the time of the next opening —: the path follows the requests of the
page, whether they leave from a new document or from a navigation within the same page, and waits,
outside the measurement, until none has been in flight for half a second, within fifteen seconds at
most; the log writes how many were in flight at the start of each measured opening, and there
must be none.
Each opening is compared to the second, without rounding; the log of the path, and the summary
of the job in the chain, under the title « The second of §4.6.2 », write the median and the
worst, usable, drawn and hydrated, and, for the opening by the address, where the time goes:
the median instants where the server finished sending the document and where the browser read it. **The measurement fails nothing on the
second**: an opening that exceeds it is a warning — of the test, and of the chain —,
never a failure, neither of `make e2e`, nor of the chain, nor of the merge queue. Against the fake
back, for a single user, on a shared machine of the chain, it does not tell what
the service will hold: its figures varied from one run to the next by a factor of two on the
same revision. It is a declared deviation of US-0110 and US-0220; the second is held, blocking,
in EP-13, on the reference data set, with fifty users, against the real service. The
path keeps only operating bounds, far from the second, which measure
nothing: fifteen seconds for a grid to become usable and for a page to settle
(`WORKING`), Playwright's five seconds for each assertion: the address after a click,
then what the grid shows; three minutes for each test. Past one of them, the path no longer works — a grid never
usable, a page that never settles — and it fails, whatever the second. The
path finally checks that the document carries no field of a node that the grid
does not read (`lineage_id`). Its Playwright project, `measure`, depends on the `chromium` project:
it runs after all the other paths, alone on the machine — and does not run when one
of them fails —, and without a trace. In the chain, at the full tier, it runs alone on a
runner of its own, alongside the shards of the paths (« The chain »): `make e2e-measure`, which
starts only the fake back and the built front — the harness reuses none of them —, and which
the failure of a path no longer prevents. On a workstation, `make e2e` plays it after the paths, and
`make e2e-measure` alone. `E2E_PART` tells the harness what it plays: `paths`, the paths without
the measurement, which `make e2e SHARD=i/N` sets; `measure`, the measurement alone, which
`make e2e-measure` sets; `service`, the paths against the service alone, which `make e2e-service` sets
and which requires `WATERFALL_API_ADDRESS`; absent, everything, without the paths against the service. Without
it, Playwright would not know how to distribute the paths: the measurement, which waits for all of them, would
drag them all into each shard.

The witness path — list of projects, project, grid — goes through three minimal pages,
with no text of their own, which EP-02 replaces while keeping the path. They read the API on the
server side (`frontend/src/api/server.ts`); their unit tests receive the examples of the
contract through `frontend/src/test/fixtures.ts`, the same data the fake back serves.

The minimal accessibility of each screen (US-0200, WF-IHM-0100) is checked in
`frontend/e2e/accessibility.spec.ts`, on the screens of `frontend/e2e/routes.ts`: those of the table
of `functions.json`, which `screens.spec.ts` also reads, and those no table names — the project
itself, the account pages, the sign-in and the forgotten password, the « not found » screen.
`frontend/src/app/screens.test.ts` (`make test-front`) confronts each page of `frontend/src/app`
with these screens and with the pages that only redirect (`REDIRECTS`): a page added without its screen
makes it fail, as does a page of `REDIRECTS` that does not only redirect, or a route that
intercepts another. Each screen is opened by its address in a 1366 × 768 point window,
hydrated (`untilHydrated`, which waits for the keys React sets on each element the
keyboard reaches), then shrinks to 911 × 512 — what a 150 % zoom leaves of 1366 points, the
page laid out again as the browser lays it out again when zooming; a device scale
factor would change the pixels, not the layout. Three tests per screen each check the
two widths:

- the axe rules for WCAG A and AA (`axeAudit`, `frontend/e2e/axe.ts`) — axe is not WCAG —,
  contrast included, once in light mode and once in dark mode (`colorScheme`), each test
  first observing the painted mode — no `data-theme`, the background of the visual identity. A text that axe leaves
  « incomplete » with its two colours measured and a measurement that fails — a single character under the
  expected ratio, which it does not want to call a text, or a text of the colour of its background — is a
  deviation, its colours stated; what axe leaves unmeasured (`unmeasured`), the test notes in an
  annotation, reason by reason (`elmPartiallyObscured`, `bgOverlap`…), the curve figures apart — a lone character
  whose colours axe did not measure counts there under its brevity, axe writing it over the reason
  that prevented it from measuring. In light mode, the
  rules of field labels and image descriptions — `label`, `image-alt` and their
  relatives — are stated apart;
- the keyboard walk (`walkByTab`, `frontend/e2e/tab-walk.ts`, the in-page measurement by
  `frontend/e2e/focus-probe.ts`): at 1366 points, Tab from the top of the page, at 911 points from
  where the first walk stopped, each time until the return to the first element reached.
  Each element reached is seen — displayed, not transparent, and the middle of what remains of it, clipped
  by the viewport and by the padding box of each box that clips it along its containing
  blocks, is the element itself: nothing that paints is drawn over it, a layer the
  pointer passes through included —, and nothing else takes the pointer there, a transparent layer that
  captures clicks included (`covered`). It carries a focus indicator: an outline or a shadow
  it did not carry before the walk, when nothing had the focus — or, for an element born
  since, that it no longer carries once left; an element born since and gone once left is
  not judged, and is reported (`unjudged`) —, not transparent, at least one side outside what the boxes that
  clip it cut off and, inside, not under what covers it: what the element contains for an inner shadow, a
  positioned element for an outline. An element reached twice before the return to the first is
  a trap, like an element that keeps the focus from one Tab to the next longer than a field made
  of fields — the day, the month and the year of a date. Each element Tab can reach —
  displayed, enabled, of non-negative keyboard order — must be reached itself, or, for a widget that
  moves the focus itself (grid, tree, menu, list, radio group, tabs, toolbar),
  the focus must enter it; each of these widgets must be entered (`stopless`); no element
  may lie entirely beyond the edge of a box that hides what overflows it, which the
  browser scrolls on focus but the pointer does not reach — a box the user
  scrolls is never an edge: what it hides, it shows by scrolling, and it is the box that
  must be within the boxes around it; what it shows is still judged against them; no link or button is taken out of
  the keyboard order outside such a widget. Finally, everything Tab reaches at 1366 points, it
  still reaches at 911 (`lost`). To see what paints over an element, the walk makes
  only the elements that do not take the pointer, and whose box touches that of the element or of one of its
  children, take it for the time of the measurement — each point the measurement asks the
  browser for is in one of them —, then puts them back as they were; it reads all the elements
  first, then writes the ones it found, never one after the other, `pointer-events` being
  inherited. A sheet laid on all (`* { pointer-events: auto }`) and removed at each Tab
  made the style of the whole page be recomputed twice — three fifths of the time of a
  Tab on a page of two thousand elements, and the walk of the access roles, more than 350
  Tabs at each width, at 84 of the 90 seconds of its timeout under four workers, 69 once only the
  elements without pointer were changed, all of them, at each Tab, 54 once those that touch
  the element were changed (#1263). The rest is that of the page and of the round trips: alone, each width of the
  walk occupies the browser 12 of its 16 seconds, 10 without any pointer measurement.
  The walk presses Tab in batches (`BATCH`, sixteen keys) and reads in a single `evaluate`, after
  each batch, what the page measured for each key: only one round trip per element remains,
  that of the key, which the keyboard imposes; a read after each key made a second one, and the
  loaded workstation pushed the walk of the roles past its 90 seconds with it (#1540). The probe
  hears each Tab at its `keyup` — the focus moved, or it stayed, the trap the walk must see — and
  takes the measurement, by the same code, at the moment the walk used to take it: when the page
  hears the walk again, the next key before anything of the page sees it, or the read of the
  batch. `focusin` is not enough: it fires neither when the focus stays, nor when it leaves the
  document. Back at the first element, the page stops measuring, and the keys left in the batch
  reach neither the page nor the focus: the second walk always starts from where the first one
  stopped; what the page measured beyond a trap is not read, nor counted in what Tab did not
  reach. The count of reached elements and of traps stays on the test's side. The walk, and it
  alone, keeps its trace without DOM snapshots (`withoutSnapshots`): a snapshot per key weighed
  more than the walk itself under load (#1540), and its faults are read in its findings.
  `test.use({ trace })` does not apply to a single test — a group refuses an option that forces a
  new worker: the test restarts the trace the harness opened, with the same options, without the
  snapshots.

`frontend/e2e/tab-walk.spec.ts` and `frontend/e2e/axe.spec.ts` exercise the walk and the axe audit
themselves, on pages written for them (`page.setContent`): each defect they must
name is named there, and what they must let pass passes. The tools of Next's development
server (`nextjs-portal`), which the built front does not have, are set aside from axe and from the
walk. The file is played test by test (`mode: "parallel"`): Playwright distributes its tests one by
one among the workers and the shards of the chain, and not the file as a block; each takes
`test.slow()`, because it opens a screen then checks it twice, which exceeds the default timeout
on a loaded workstation; the cold compilation of a screen adds to this time only under
`E2E_DEV_SERVER=1`, the built front having none. A reported deviation is fixed in the screen, never by setting aside a
rule.

The harness checks only the screens as they open: what a gesture opens — a dialog,
a menu, the refusal of a cell, the editor of a cell — is not walked, nor what a
closed `details` contains, nor a state a gesture reaches (a refusal, `?import=`); axe does not judge the
contrast of a text laid on the drawing of a curve, and the contrast of the focus indicator
(WCAG 1.4.11) is measured only by the tokens of `contrast.test.ts`. What covers them elsewhere, and
what remains, is stated in the note of US-0200 (EP-14) and in #782.

_Check_: `make e2e`, at the full tier of the chain; the failure of a path makes it
fail, a grid opening that exceeds the second is only a warning there.

### Code coverage

The specification asks only for the coverage of the requirements; code coverage is a
rule of the repository, which finds what the former does not see — an error path never
executed, dead code. The back and the front must each cover **90 % of the lines and 85 %
of the branches**: the branches count, because an `if` without its `else` covers all its
lines and half of the cases. Generated code is excluded from it. The client of Keycloak's administration
API (`waterfall.platform.keycloak_admin`), which only Keycloak serves, the reading of the
accounts by the worker (`waterfall.worker.identity_sync`), which requests it at each step, and the bootstrap
(`waterfall.bootstrap`), which creates the first administrator in it, are measured by
`make test-keycloak`, at the same thresholds (`backend/coverage-keycloak.toml`), and set aside by their path
from the measurement of the back, `make coverage-back`, which measures all the rest of the back. No line excludes itself from the
measurement by a comment; an exclusion is written in the configuration, with its reason
(`[tool.coverage.report]` of `backend/pyproject.toml`, `coverage` of
`frontend/vitest.config.ts`). A test that passes over lines without checking anything is a
defect, which the review reports.

_Checks_: `make coverage-back`, `make coverage-front`, at the full tier: they name
the least covered files when a threshold is not reached.

### A test that takes up a numeric example

Each numeric sentence of a Vérif field is a test case of the core, with the same inputs
and the same expected value (WF-QUA-0020). `make fixtures` lists them in
`fixtures/examples.json` — a generated file, which is not touched by hand —, each under a key
made of the requirement and the fingerprint of its text: `WF-PTF-0020-A#ab12cd34ef56`.

To exercise an example:

1. write a fixture under `fixtures/`, a JSON file that cites in `examples` the key of
   the sentence, and carries its data, copied from the sentence;
2. write the test under `backend/tests/examples/`: the `example` fixture loads it by the
   key, the test calls the core and compares to the value of the sentence.

The sockets are closed there: an example that passes needs neither database, nor service, nor
browser. A sentence modified in the document changes key; the fixture of the old one
then makes the chain fail, and it is rewritten from the new sentence.

_Checks_: `make check-fixtures` — the report is up to date, each cited key exists, and the
examples that no fixture cites yet are listed, without failure: their number decreases with
the computation epics (EP-06 to EP-11).

## Error envelope and error codes

The envelope is fixed by the contract (`docs/api/README.md`, WF-ARC-0110): a machine code and
its parameters, never a sentence.

- **Adding a code on the front side** — a new code is first a change to the contract
  (`ErrorCode`, `docs/api/components/common.yaml`), followed by `make generate-client`. The
  front gives it its sentence, `errors.<CODE>`, in both catalogues: what is refused,
  without anything of what the parameters name. A new parameter a reader has to
  know receives its own, `problemDetails.<param>`, and its reading in `DETAILS` of
  `frontend/src/i18n/problem.ts`, which names a coded value — a permission, a
  condition — by its label from the catalogue; a parameter that tells a reader nothing —
  an identifier, a write counter — receives none. A component renders a refusal by
  `problemMessage(problem, { locale, messages })`, never by writing the sentence.

  _Checks_: `make typecheck-front` fails on a code of `ErrorCode` without a key in the
  French catalogue, which `problem.ts` reads by `errors.${code}`; `make catalogs`, on a
  code without a key in one of the two, or on an `errors.` key the contract no longer has.

- **Reacting to a refusal on the front side** — a server action never returns the raw response
  of the API: it calls the client through `decode` of `frontend/src/api/problem.ts`, the only
  decoder, and returns its `Outcome` — `done`; `refused`, a `Problem` to say as it is;
  `stale` (412); `conflict` (409); `signed_out` (401); `unreachable`, the API that did not
  answer at all, distinct from any `Problem` — the rejection of `fetch` itself, which
  `client.ts` marks `Unreachable` (another `TypeError` is a defect and propagates), or a
  502, 503 or 504 without a `Problem` envelope, which a gateway returns when the service is
  down. An error response without an envelope, or whose `code` is missing from the catalogue — a
  service more recent than the front —, counts as `INTERNAL_ERROR`, « unexpected error », at
  the status received: the screen never displays a raw key. The component says it through
  `OutcomeNotice` (`frontend/src/components/commands/`), as an alert: the sentence of
  `problemMessage`, which also names the objects the refusal gives only by their identifiers
  when the screen has read them (`names`, and `KnownNames` for all the notices of a screen); the lines
  or the projects named beyond the sentence, outside the alert and described by its sentence (#765); on 412, the offer to reload the screen; the conflicting object
  (`params.conflicting_object_id`, or failing that the one of the first refusal by field that names one,
  `fields[].params.conflicting_object_id` of a 409 `ALREADY_EXISTS` — `conflictingOf` of
  `frontend/src/api/problem.ts`) named when the screen knows it, through `names`, or failing that by the
  label the refusal gives it (`conflicting_object_label`) — a project, a sub-project the
  screen does not show, whose taken code comes back once the dialog is closed (#714); on 401, the
  link to the login; the unreachable API announced, never a blank screen; the unexpected
  error with its reference (`correlation_id`), like the failure screen. A server action
  whose promise is rejected has returned no `Outcome`: the component holds it through `rejected`
  (`frontend/src/components/commands/rejection.ts`), one rule for every screen (#330) —
  a `TypeError` is the unreachable API: that is what the browser's rejected `fetch` throws, and
  the browser does not distinguish it from a `TypeError` thrown elsewhere, which therefore also passes for
  « unreachable »; any other rejection is classified by its `digest`, as the failure screen classifies it
  (`failureOf`) — the unreachable API, the lost session with the link to the login, or
  the unexpected error with its reference, the latter kept only if it has the form of a
  `correlation_id` of the contract. The login
  is `/login?next=<chemin et requête de l'écran visé>` (`loginHref`,
  `frontend/src/navigation/login.ts`): the login route (US-0320), once the session is reopened,
  leads to `returnTarget(next)`, which follows only a path of the front — neither `//hôte`, nor an
  address of another site — and otherwise brings back to the home page. A 401 `ACCOUNT_DEACTIVATED` does not lead
  there, it would loop: `kindOf` files it under `refused`, and a read throws `AccountDeactivated`.

  _Checks_: `make test-front` (`problem.test.ts`, `login.test.ts`, `rejection.test.ts`);
  that a server action goes through `decode`, and that a rejection goes through `rejected`, the review.

- **Adding a code on the service side** — the code exists first in the contract (`ErrorCode`), then in
  the models of the service that `make generate-server-models` generates from it
  (`backend/src/waterfall/api/contract/models.py`, versioned; `make server-models-up-to-date`,
  in `make check-contract`, fails if they are no longer those of the contract). An address there is a
  plain text (`--type-mappings email=string`): the service returns it as it holds it, and the
  models do not validate addresses; the core validates them by the rule of the contract (#665,
  `is_address` of `waterfall.core.users.identity`). The core then raises
  the exception of `waterfall.platform.errors` that carries the status of the contract — `NotFoundError`
  404, `ForbiddenError` 403, `ConflictError` 409, `PreconditionFailedError` 412,
  `UnprocessableError` 422, `UnavailableError` 503… — with the code, as a string, and its parameters;
  a refusal by field is said by `FieldError(pointer, code, params)`, the pointer being that
  of the contract (`/label` in the body, `/query/from` in the query); a key sent by the
  client is escaped there as RFC 6901 wants it, `~` as `~0` and `/` as `~1` (`json_pointer` of
  `waterfall.platform.errors`, #750). It never builds
  a `Problem` nor a response: a single handler (`waterfall.api.problems`) renders every
  error in the envelope, with the correlation identifier of the request, in the body and
  in the `X-Correlation-ID` header. The handler likewise files, without the route thinking about it:
  an unreadable request (body absent, `null`, not JSON or not an object, unreadable header
  or cookie) as 400 `MALFORMED_REQUEST`; a refused value as 422
  `VALIDATION_FAILED`, one field per fault — a `model_validator` on a readable body is
  one, at the pointer `""` — (`VALUE_REQUIRED` for an empty value when at least one is
  required, `VALUE_TOO_LONG`, `VALUE_OUT_OF_RANGE` with `minimum` or `maximum` for an
  inclusive bound, `NUMBER_INVALID`, `DATE_INVALID`, otherwise `VALIDATION_FAILED`: an exclusive bound,
  a minimum length not met by a non-empty value); a path identifier that is not
  a UUID as 404 `NOT_FOUND`, like a non-existent or invisible object, whereas another
  refused path parameter is a 422 by field, at the pointer `/path/<nom>`
  (`docs/api/DECISIONS.md`, « Session et erreurs »); an unknown route, or a method the
  route does not serve, as 404, without redirecting a trailing slash; any unexpected exception
  as 500 `INTERNAL_ERROR`, caught by `CorrelationMiddleware`: logged once with its
  trace, its correlation and the author of the request, without returning any of it.
  A code the contract does not know is a defect: the handler renders it as 500.
  A received text that contains the NUL character, which PostgreSQL refuses in a column as in
  a `jsonb`, is a refused value — 422 `VALIDATION_FAILED` at the pointer of the field —, never a
  500 from the database (#743): every generated model inherits from `ContractModel`
  (`waterfall.api.contract.base`, which `[tool.datamodel-codegen]` of `backend/pyproject.toml`
  gives to the generator), which looks for the NUL in each of its fields, an element of a list, a key or
  value of an object included; a query or path parameter in text is typed `Text`, from the
  same module.

  _Checks_: `make server-models-up-to-date`; `make test-back` (`test_api_problems.py`,
  `test_access_roles_guard.py` for the NUL); that every text parameter is a `Text`, that the
  code and the status are those of the contract for the operation, the review, then the validation of the
  responses of the API tests against the contract.

- **Logs and responses of the API tests** — an API test goes through `ContractClient`
  (`backend/tests/support.py`), which validates every response against the contract with openapi-core:
  a response outside the schema fails the test. The logs are those of structlog in JSON
  (`waterfall.platform.logs`): a record carries `level`, `timestamp`, `actor` and, within
  a request, `correlation_id`; any field whose name contains `password`, `token`,
  `secret`, `authorization` or `cookie` is removed from it. The value of every secret of the
  settings (`Settings.secret_values()`, the password of a URL included) is moreover replaced by
  `***` in the whole rendered text of a record — message, trace, `repr` —, including those
  of the libraries. The limit: a secret the settings do not know (a session
  token, a password received in a request) is neither removed under another name nor masked
  by its value: it is not logged, nor put in the message of an exception. A
  decoded form of the password of a URL is kept only if it is at least four
  characters long, failing which it would mask any text that contains it; the whole URL and the
  encoded form remain masked in every case.

- **Accessing the data of a module** — the tables of a module are classes on the `Base` of
  `waterfall.platform.database`, in its `tables.py`, private; its data access, functions
  of its module that take a `Session`, private too; the `interface` offers the
  others only what it declares, as plain objects and not as rows of the table. A write
  receives as an argument who writes and at what moment (`Stamp(author, at)`, the author being `None` for
  the platform): the core does not read the clock. An identifier is drawn from `new_id()`
  (`waterfall.platform.identifiers`), an instant from `UtcDateTime`, which refuses an instant without
  a time zone. One request, one transaction: `Database.transaction()` commits it at the end of the block and
  rolls it back if an exception passes through, the response being built before. A change that
  carries a `lock_version` tests it in the write itself and raises `PreconditionFailedError` if the
  version is no longer the right one.

  _Checks_: `make test-back` (`tests/test_users_data_access.py`); `make imports-back` for
  the boundaries; that the write tests its `lock_version` in the query, the review.

- **Knowing the caller** — a guarded route takes `Caller` and, if it reads or writes the database,
  `Transaction` (`waterfall.api.authentication`): the first validates the access token by the
  keys of the realm (`waterfall.platform.keycloak`) and reads the account by `idp_subject` at every
  request, the second opens the transaction of the request, committed when the route has built its
  response and before it leaves. No call to Keycloak is made inside a transaction (#669):
  the caller is read, then admitted if need be, and its permissions read (`Acting`), each in a
  short transaction of its own, and a route that calls Keycloak — `closeMySessions`, `createUser`,
  `setUserActivation` and `setUserAccessRoles`, which close the sessions of an account deactivated or
  stripped of all its roles once the write is committed, `createPasswordSetupLink`, which has the
  link made by the extension and records it in the log, without its token, only once done,
  `updateMyPreferences`, which gives the chosen language to the account at Keycloak before writing it and
  writes nothing as long as it does not answer — does not take `Transaction`, but opens its own before
  and after the call. An absent or invalid token is
  a 401 `SESSION_REQUIRED`, an expired token a 401 `SESSION_EXPIRED`, a token whose
  login (`auth_time`, failing that `iat`) precedes the last closing of the sessions of the account, or
  falls within its second, a 401 `SESSION_REVOKED` — `closeMySessions`, the deactivation and the
  removal of all the roles note its time, `sessions_closed_at`, before calling Keycloak
  (#668, #835, #855) —, a deactivated account a 401
  `ACCOUNT_DEACTIVATED`; an account Waterfall does not know yet is created without a role if it
  comes from the directory or from an external provider, refused otherwise by a 401
  `ACCOUNT_NOT_ADMITTED` (#664), its cause written to the log alone. The caller becomes the author
  (`actor`) of every log of the request. The API reads `WATERFALL_KEYCLOAK_ADDRESS`, the address
  of the browser, which names the issuer of the tokens, `WATERFALL_KEYCLOAK_BACKCHANNEL`, the one where it
  reaches Keycloak if it has another, and the secret `WATERFALL_SERVICE_CLIENT_SECRET`. A test
  signs its tokens with keys it generates and serves as the realm serves its own
  (`tests/realm.py`); what requires the administration API of Keycloak
  (`waterfall.platform.keycloak_admin`) is tested against the platform (`make test-keycloak`).

  _Checks_: `make test-back` (`tests/test_api_authentication.py`, which also counts the
  connections taken during the call to Keycloak, `Watching` of `tests/support.py`),
  `make test-keycloak` (`tests/test_keycloak_authentication.py`); that a guarded route takes
  `Caller`, the review.

## Translation keys

The texts of the interface live in two twin catalogues, which next-intl reads:
`frontend/messages/fr.json`, the reference, and `frontend/messages/en.json`. The language
does not appear in the address — a shared link opens for everyone in their own
(WF-INTF-0170) —: the server resolves it at every request (`frontend/src/i18n/request.ts`),
from the preference of the account if it is `fr` or `en`, otherwise the first offered language
that `Accept-Language` asks for, otherwise the default language of the installation
(`getInstallation`). A `*` placed before any offered language in `Accept-Language` lets
the installation decide; an unreadable or unreachable installation gives `fr`, the language of the
reference catalogue. Without an account — no session, or an unreachable API — there is no
preference: the browser decides, and the shell does not offer the account menu, where the
language is chosen.

- **A key is hierarchical, in English.** A text specific to the interface is filed under the
  component or the screen that uses it, in camelCase (`languageSelector.label`). What the
  contract enumerates keeps its names, and each value has its key:
  - `enums.<Schéma>.<valeur>` for a named enumeration (`enums.ProjectState.in_progress`),
    `enums.<Schéma>.<propriété>.<valeur>` for an enumeration declared in a property
    (`enums.BackgroundTaskRef.kind.revision_mark`), the `items` of an array not counting
    (`enums.ReferenceReadiness.missing.active_cost_category`): every enumeration of
    `components.schemas`, except the two following;
  - `errors.<CODE>` for each code of `ErrorCode`, `permissions.<code>` for each
    `PermissionCode`;
  - `enums.<Paramètre>.<valeur>` for an enumeration of a shared parameter of
    `components.parameters` (`enums.Scope.unassigned`): its name shares the level of the
    schemas, and a parameter that enumerates values does not bear the name of a schema;
  - no enumeration is written inline, for want of a name to file its keys under: that of an
    operation parameter becomes a shared parameter of
    `docs/api/components/parameters.yaml`; that of a request or response body, or
    of a header — under `paths` as under `components.responses`, `requestBodies` and
    `headers` —, a named schema of `components.schemas`. Two exceptions, without a key:
    `sort_by`, whose values are columns the header of the grid already labels, and
    the bodies of the probes, `/health` and the paths that stem from it, which no screen displays;
  - a `const` has no key: the contract uses it only for the agreement a request
    gives (`confirmed: true`), which is not displayed;
  - a value that carries a dot reads as a level, next-intl reserving the dot for the
    path: `permissions.users.write`, `enums.ComputedField.task.start`.
- **A value is an ICU message** — `{max_columns, plural, one {…} other {…}}` —, with the
  same arguments in both catalogues, which `make catalogs` checks; the label of an enumeration value or of a
  permission is text without an argument. French follows its typography: a non-breaking space
  before the colon, a thin non-breaking space before the semicolon and the exclamation and
  question marks, a typographic apostrophe; English follows British spelling.
- **Adding a key** means writing it in both catalogues, at the same place, and reading it through
  `useTranslations` — client component, or server component without `await` — or through `createTranslator`
  and `requestLanguage()` in an asynchronous server component. A value added to an
  enumeration of the contract adds its key in the same change.
- **What the user has typed is not translated**: a task label, a project name
  are displayed as they are (WF-INTF-0170).
- **The formats** are those of `frontend/src/i18n/format.ts`, by language: an amount, a
  decimal, hours from the exact string of the contract (`formatMoney`, `formatDecimal`),
  never from a float; a planning date as it is, without a time zone
  (`formatPlanningDate`); a timestamp in the local time of the workstation, written in the browser
  (`LocalTime`); a ratio typed or set — a rate, a probability, a bound — as a
  percentage, from its exact string, every digit kept (`formatPercent`); a share the
  server computes — the share of a cost type or of a position, a progress, a load rate — to the
  hundredth of a percent (`formatShare`): a non-zero share that rounding would call zero is said
  « < 0.01 % », or « > -0.01 % », through the catalogue (`share`); a zero share, whatever the
  number of its zeros, reads « 0 % »; near 100 %, ordinary rounding (EP-14/L51). A share
  the contract gives as zero is zero: a non-zero share is never given as zero, but to its
  first significant digit (EP-14/L42o, #694), and the bridge of L51, which judged a share zero
  by its amount, is removed (EP-14/L52). In French, `Intl` separates thousands with a thin
  non-breaking space (U+202F): « 1 234,56 » does not break at the end of a line. English is formatted in British
  English (`en-GB`), as its catalogues are written: « 31 May 2026, 16:30 », the
  numbers remaining « 1,234.56 ».

_Checks_: `make typecheck-front` — next-intl is typed by the French catalogue, and a
key the code uses without it having it breaks the typing, as does a key missing from the
English catalogue (`frontend/src/i18n/catalogues.ts`); `make lint-front` —
`react/jsx-no-literals` refuses text written in the JSX, and `no-restricted-syntax` a
literal in a read attribute — `aria-label`, `aria-description`, `aria-roledescription`,
`aria-valuetext`, `aria-placeholder`, `title`, `alt`, `placeholder` (except `blur`, `empty` and
a `data:image/` address, the forms of next/image), `label`, the `value` of a button
`input` —, or in a branch or a concatenation of a child or of one of these attributes;
what remains for the review are the other props of our own components, and a string built by a
function or a method (`.join`, `.concat`), in the JSX or outside it;
`frontend/src/i18n/text-guard.test.ts` tests it on trapped extracts, next to the network
guard that shares the rule; `make catalogs`, in `check-front`, which reads the
contract it has just bundled (`wftools.catalogs`) — the two catalogues have the same
keys, each value is a non-empty text, each enumeration value, each error code
and each permission of the contract has its own, and no key under `enums`, `errors` or
`permissions` survives the value the contract has removed; a text uses the same
ICU arguments as that of the French catalogue, a key is written only once per file, and
no enumeration is written inline, apart from `sort_by` and the probes. It requires at least
two catalogues, and names each key that is missing and the catalogue that carries it.

## Visual identity

The visual identity lives in `frontend/src/theme/globals.css`, and nowhere else: the colours,
the typography, the spacings and the radii are tokens there — CSS variables that
Tailwind and the shadcn/ui components read through the theme (`bg-primary`,
`text-muted-foreground`, `rounded-md`). The blues come from the logos of `docs/assets`
(`#027dc6`, `#1195e1`), which reach a component only through measured tokens, the
neutrals from shadcn/ui; the typeface is Geist, that of the logo.

- **Light and dark through the same tokens.** Each colour token carries its two values,
  `light-dark(claire, sombre)`. The document follows the workstation (`color-scheme: light dark`); when
  the account forces a mode (`DisplayPreferences.theme`), the root layout sets
  `data-theme="light"` or `data-theme="dark"` on `<html>`, resolved on the server side like the
  language. No component asks itself which mode is displayed: Tailwind's `dark:`
  variant, which would follow only the workstation and ignore the forced mode, is refused. A state
  that changes colour — hover, current page — has its own token (`--primary-hover`),
  measured like the others.
- **Adding a colour means adding a token**: its light value and its dark value in
  `:root`, its name in `@theme inline` (`--color-<nom>: var(--<nom>)`), and each pair of
  text and background it forms in `frontend/src/theme/contrast.test.ts`; a component then uses
  its class (`bg-<nom>`). Never a colour in a component: neither a class of Tailwind's
  palette, removed from the theme — `bg-blue-500` produces nothing —, nor an arbitrary
  value of a colour utility (`bg-[#027dc6]`, `bg-[red]`) — a length or a
  number pass, `ring-[3px]` —, nor a variable in parentheses (`bg-(--x)`,
  `font-(family-name:--x)`), which nobody has measured, nor an arbitrary property that paints or a variable
  (`[color:…]`, `[--primary:…]`), nor `color-mix(`, nor a colour written in a string,
  in a `style` or in the attribute of an SVG. A typeface is added the same way, through a
  `--font-<nom>` token.
- **The mark of a differential** (US-0500) has three line tokens and three mark tokens,
  `--diff-added`, `--diff-removed`, `--diff-modified` and their `-mark` — a green, a red, a yellow —,
  which `DiffMark` sets (`frontend/src/components/grid/diff-mark.tsx`); the colour doubles the character
  `+`, `-` or `M` and the word, it never replaces them. The text of the page and the mark reach
  4.5:1 on each tint in both modes (`contrast.test.ts`).
- **The contrast** of a text on its background reaches 4.5:1, that of what shows a control —
  border of a field, focus ring — 3:1, in both modes (WCAG AA, §3.6).
- **A signal goes through `Signal`** (`frontend/src/components/signal/`), and only
  through it (WF-IHM-0070): it receives an `AlertZone` of the contract and renders it by a
  Lucide shape, its label from the catalogue (`enums.AlertZone.<zone>`) and its token,
  `--signal-<zone>`, in a single table typed on `AlertZone`. **A zone comes from the
  server**, which classifies by the thresholds of the reference data: the front never derives one
  from a value (WF-ARC-0020). A null or absent zone renders no `Signal`; the value
  says that it is missing (`ComputedIndicator`); never `?? "nominal"`. The signal tokens
  are measured like the others, and moreover in greyscale and as seen by a protanope and a
  deuteranope (`contrast.test.ts`); the alert stands out the most from the page there in both modes —
  the darkest in light, the brightest in dark —, the nominal the least. Outside `src/components/signal/`, a colour utility that names
  a zone token (`bg-signal-alert`, `text-signal-watch`) is refused: `SIGNAL_SYNTAX` of
  `frontend/eslint.config.mjs`, `make lint-front`, tested by `colour-guard.test.ts`.
  That no screen distinguishes two states by colour alone — a dot, a tinted
  line without shape or text —, it is otherwise the review that holds it; the tests of
  `Signal` prove it for the component.
- **The state of a project goes through `ProjectStateBadge`** (`frontend/src/components/projects/`,
  #523), everywhere a screen shows it — the home page, the list of the portfolio, the page, the
  settings and the life cycle of a project: a dot filled with the token of its state,
  `--state-<état>`, its text from the token `--state-<état>-foreground`, in the palette the author
  has validated — light grey for Created, blue for Pricing, green for In progress, dark grey for
  Completed, orange for Lost, muted red for Abandoned —, and always the word of the state and its
  icon, specific to each and distinct from the shapes of `Signal`. `contrast.test.ts` measures the text
  of each state on its dot, and keeps each state token away from the zone tokens:
  a state does not read as an alert.
- **shadcn/ui everywhere a component exists**: a component is added by copying its source
  into `frontend/src/components/ui/` (`frontend/components.json` gives the paths), and
  only when a screen uses it; what it offers and no screen uses — a
  variant, a part — is not copied. Once copied, it is code of the repository, subject to all its
  rules: header, lint, JSDoc, coverage, texts through the catalogue, colours through the tokens
  — its classes are rewritten on the tokens of the visual identity (`bg-popover`, `bg-sidebar-accent`),
  and a token it expects and the visual identity does not have is added there, measured. A CSS variable is not
  set in a `style`: the visual identity declares it (`--sidebar-width`). Radix, its foundation, comes
  from the `radix-ui` package, a single one, examined for the network guard. A component that passes another
  to a client component from a server component passes it an element, never a
  function — an icon is handed over drawn (`commandIcon`).
- **The layout** follows the mockup validated by the user (EP-02, « Charte
  graphique »): the sidebar is the Sidebar of shadcn/ui, collapsible into a rail of icons where
  each entry keeps its name and shows it in a tooltip; the top bar carries the
  breadcrumb, the search, the button of the tasks and messages panel and, on the right, the
  avatar button that drops down the account menu (DropdownMenu). A screen is built on the template of
  `frontend/src/components/shell/page-header.tsx`: `Screen`, its `<main>`, and `PageHeader`,
  the title and the icon of its function, a line below, its commands on the right.
- **Density**: the grids and the lists are dense — the most information before the
  eyes —, the indicator screens airy; each function has its own, in a typed table
  (`FUNCTION_DENSITY`, `function-display.ts`), which `Screen` and `PageHeader` receive.
- **A Lucide icon on every navigation entry, every button and every line
  nature.** For the functions, the blocks, the commands, the account pages, the line natures,
  the scheduling modes and the progress states, it is drawn from a table typed on what it represents — `FUNCTION_ICONS`,
  `GROUP_ICONS`, `PROJECT_COMMAND_ICONS` and `REVISION_COMMAND_ICONS`, `ACCOUNT_ICONS`,
  `ROW_NATURE_ICONS`, `SCHEDULING_MODE_ICONS` and `PROGRESS_ICONS` —, so that a value added without an icon breaks the typing; elsewhere — a
  button of the shell, a notice, a system page —, it is set inline. An icon next to its text is `aria-hidden`; a
  lone icon carries a name — the button that carries it, or the icon itself (`role="img"`), the
  nature of a line in its cell.
- **Sobriety**: no ornament beyond the icons — neither gradient, nor decorative shadow, nor
  transition, nor animation, apart from the pulse of the loading skeleton, which says a state and
  stops when the workstation asks for less motion; a single shadow, `shadow-md`, on what
  floats above the page (a menu), to detach it from it. `src/components/ui/sobriety.test.ts`
  checks it for the copied components. A state is said in words — a badge, a dot —, never by colour
  alone.
- **The logo and the favicon** are the files of `docs/assets`, copied byte for byte into
  `frontend/public/` and `frontend/src/app/icon.svg`; the logo takes its dark variant where
  the dark mode applies.

_Checks_: `make lint-front` — `no-restricted-syntax` (`COLOUR_SYNTAX` of
`frontend/eslint.config.mjs`) refuses, in any string of the code, a colour class of the
palette, an arbitrary value of a colour utility that is neither a length nor a
number, a variable passed to a colour or typeface utility, an arbitrary typeface, an arbitrary property that paints, sets a typeface or a
variable, `color-mix(`, a colour written as a whole string and the `dark:` variant; in a
`style`, whatever its value, a property that paints, borders, shadows or sets a typeface,
and a variable, whether the key is a name or a string; and, for `fill`, `stroke`, `color` and
the colours of an SVG, any literal or template without an expression other than `currentColor`,
`none` or `url(…)`, wherever it is in the value, a branch included.
`frontend/src/theme/colour-guard.test.ts` tests it on trapped extracts, and checks
that no stylesheet lives outside `src/theme/`. `make test-front` —
`contrast.test.ts` measures each pair of tokens in both modes, `brand.test.ts`
compares the logos and the icon with those of `docs/assets`. The contrast of the rendered screens is
checked in the browser, on each screen of the table, in light and in dark
(`frontend/e2e/accessibility.spec.ts`, US-0200); the rest of the accessibility of a component, in its
tests, through `expectAccessible` (`frontend/src/test/axe.ts`, axe-core under happy-dom, which does not
compute colours). Left to the review: a colour built by a template with expressions
or by a function, and a `style` or an SVG attribute that receives a variable rather than an
object or a literal written in place; and, for the layout, that a button or an entry
carries its icon outside the typed tables — a hand-written button —, that no shadow, no
gradient and no animation adorns a copied component, that a screen takes the template and the
density of its function, and that a copied component enters only with the screen that uses it.

## Migrations

The schema of the database is the history of its migrations: Alembic, in
`backend/src/waterfall/migrations/` (`versions/0001_….py`, `0002_….py`…), a chain of
numbered revisions, **written by hand** and reviewed like the code. The rules — naming, types,
constraints, two steps, locks — are in [sql.md](sql.md); this section says how one
is written.

**Writing a migration.**

1. Declare the table or the column in the tables of the module that owns it
   (`waterfall/core/<module>/tables.py`), on the `Base` of `waterfall.platform.database`: its
   `MetaData` carries the naming convention of the constraints, declared once. Do not describe it
   anywhere else.
2. Create the file of the revision, with the next number:
   `cd backend && uv run alembic revision --rev-id 0002 -m "ce qui change"`. Alembic's
   environment (`waterfall/migrations/env.py`) reads `WATERFALL_DATABASE_URL`, like the service;
   no database is needed to create the empty file.
3. Write `upgrade()` and `downgrade()` by hand with `op.create_table`, `op.add_column`…: the
   constraints are declared **without a name**, except the `<nom>` part of a check constraint
   and an expression index (sql.md, « Nommage »). An autogenerated draft is reviewed line by
   line; it is never committed as it is. The created file is a template: `ruff check --fix` and
   `ruff format` (in `backend/`) bring it to the rules of the repository. A new table grants its
   rights to the role of the service in the same migration, the role named by the database where it applies
   (`format('GRANT … ON <table> TO %I', current_database() || '_service')`, in a `DO` block; a
   database name of 55 bytes at most), and declares them, with their reason, in `SERVICE_RIGHTS`
   (`tests/test_migrations.py`) (sql.md, « Le rôle du service »): without them, the API does not read it,
   and neither do the tests of the service; without their declaration, the test of the rights fails.
4. Add or adjust the test: the test of `tests/test_migrations.py` that compares a migrated database
   with a database created by the tables of the code (constraints, indexes, columns and defaults, read from the
   catalogue of PostgreSQL) fails as long as the two do not say the same thing, and
   a test of `tests/test_database_constraints.py` tests each new constraint.
5. Apply: `make migrate` on the database of `WATERFALL_DATABASE_URL`, or
   `make service-up`, whose `migrate` service applies the migrations before the API.

**Applying.** `waterfall-migrate` (the `migrate` service of `compose.service.yaml`, or
`make migrate`) applies, in order, the revisions the database does not have yet; Alembic notes
the last one in the `alembic_version` table. A migration already applied is not replayed
(WF-DAT-0140), and two instances that start together do not apply the same one twice: an
advisory lock queues them. The command stops, with the name of the variable, if
`WATERFALL_DATABASE_URL` is missing (WF-SEC-0010).

**A single head.** Two migrations that start from the same parent form two heads: the second to
be merged is rebased on the first and takes the next number. The test of the chain fails
on two heads.

**The rows the migration writes.** The catalogue of permissions, for instance, is a
data migration, separate from that of the schema. The rows of the installation, for their part, are
those of the installer: the bootstrap writes them, not a migration (US-0420).

**Lot size.** The migrations are written by hand: they count in the size of a
lot, and only the revisions a tool generates on its own would be declared in
`tools/paths.toml`.

_Checks_: `make test-back` (`tests/test_migrations.py`: a single head, a migration
already applied is not replayed, the downgrade is the mirror of the upgrade, the schema — check
constraints and defaults included — is that of the tables of the code, four instances together),
against PostgreSQL (see « Tests »); the compatibility
with the neighbouring code, the review.

## Agents

The agents of `.claude/agents/` — framing, delivery, development and review per language —
follow this guide like a person, and their own rules are in
[agents.md](agents.md): what is authoritative, how a lot is done, where an agent stops.

## Branches, lots and pull requests

The rules are in the [README of the roadmap](../roadmap/README.md), sections « Lots » and
« Branches », and in [CONTRIBUTING](../../CONTRIBUTING.md): one lot, one issue, one branch
`lot/<identifiant>` created from `epic/EP-nn`, one pull request that returns to it.

## Commit signing

The commits that reach `main` are signed: GitHub's « Require signed commits » rule
protects `main`, and a commit it does not recognise blocks the merge. What GitHub
creates itself (the merge commit of a pull request, a squash, a commit of Dependabot) is
signed by GitHub; what a person or an agent commits is signed by the key of that
person.

**Setting up one's machine** (SSH key, the simplest):

```bash
ssh-keygen -t ed25519 -C "<commit email address>" -f ~/.ssh/id_ed25519_signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
```

Then add the content of `~/.ssh/id_ed25519_signing.pub` to GitHub, *Settings → SSH and
GPG keys → New SSH key*, with the type **Signing Key** and the address of the commits. The key must
not ask for its passphrase at every commit, failing which an agent stops: load it
into `ssh-agent` (`ssh-add`) or into the keychain of the system. Check with
`git log --show-signature -1`, then read the « Verified » badge on GitHub after a push.

**The agents** (`.claude/agents/`) commit with the git configuration of the machine where they
run: launched on the machine of a person whose key is registered, their commits are
signed and verified. Launched in a cloud session, they sign with an environment key
that GitHub does not know: their commits are not « Verified » and must not reach
`main` as they are.

**Merges.** `main` receives the epic branches by merge commit, which carries their commits: they
must therefore all be verified. So as not to block a merge, commit on
`epic/EP-nn` and `lot/*` only with a registered key, and update a branch from `main`
through the « Update branch » button of the pull request or through a signed local merge. Avoid « Rebase and merge »: GitHub
then rewrites the commits without signing them.

**Setting it up on `main`.** The rule is activated only once the epic in progress, EP-15,
is merged, because it contains unsigned commits and the rule does not re-check the history
already merged. Order: the key registered and verified, the merge of EP-15, then « Require signed
commits » on `main` (*Settings → Rules*), before creating the branch of the next epic. The rule
targets neither `epic/*` nor `lot/*`. No check of the chain duplicates it: it is GitHub that
refuses, hence this section.
