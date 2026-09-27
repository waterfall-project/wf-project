# Security policy

## What there is to report today

There is no released version of Waterfall and no deployed instance: this repository holds
a specification and an interface contract, and the implementation has not started. So there
is no vulnerable build to report against — but a specification can hold a security defect,
and that is worth reporting before any code is written, when it still costs nothing to fix.

| Version | Supported |
|---|---|
| none released yet | — |

## Reporting

Write to **contact@waterfall-project.pro**, in French or in English.

Please do not open a public issue for something that would be exploitable once the code
exists. For everything else — a rule that is too weak, a permission that is too broad, a
piece of data that should not be kept — a public issue is welcome and more useful, because
the discussion stays with the requirement.

Tell us what you found, where (a section number or a requirement identifier is ideal), and
what you think it would allow. We will acknowledge your message and tell you what we decide
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
