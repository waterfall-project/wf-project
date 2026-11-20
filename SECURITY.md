# Security policy

## What to report

Waterfall publishes versioned container images, and this repository holds the code behind them
as well as the specification and the interface contract. Report a security defect in either:

- **in the code** — a way to read or change data without the permission, to get around the
  authentication or a session rule, to reach a secret, or to make the server do what it should
  not: say which part (the back, the front, the Keycloak extension, an image, the deployment) and
  what you did to see it;
- **in the specification** — a rule that is too weak, a permission that is too broad, a piece of
  data that should not be kept. It is worth reporting before it reaches the code, when it still
  costs little to fix.

| Version | Supported |
|---|---|
| The latest published version | Yes: it alone receives the security fixes |
| Any earlier version | No: update to the latest one |

## Reporting

Write to **contact@waterfall-project.pro**, in French or in English.

Please do not open a public issue for something that is exploitable. For everything else — a rule
that is too weak, a permission that is too broad, a piece of data that should not be kept — a
public issue is welcome and more useful, because the discussion stays with the requirement.

Tell us what you found, where (a file, a section number or a requirement identifier is ideal),
and what you think it would allow. We will acknowledge your message and tell you what we decide
about it; we have no bounty programme.

## What the specification already commits to

Reading these before reporting may save you time — and if you think one of them is wrong,
that is exactly the kind of finding we want:

- **WF-SEC-0010** — every exchange encrypted, including between components; no secret in the
  repository, in a container image or in a log.
- **WF-SEC-0020** — sessions kept in the database, expiring by age and by inactivity, and
  revoked immediately when an account is deactivated or loses all its roles.
- **WF-SEC-0030** — an audit journal of the irreversible and structuring actions, which the
  platform itself cannot rewrite.
- **WF-ADM-0140** — passwords of at least twelve characters, lockout after ten failures, a
  single-use reset link valid for one hour, and no periodic expiry.
- **WF-ADM-0110** and **WF-ARC-0070** — every action authorised by the server, at each
  action, whatever the entry point: screen, import, background task or direct API call.
- **WF-EXP-0010** — no production data in any other environment without the accounts being
  anonymised.

The whole specification is in [`docs/spec/waterfall-spec.md`](docs/spec/waterfall-spec.md),
in French.

## Licence

Waterfall is published under the [GNU Affero General Public License v3.0](LICENSE) only.
