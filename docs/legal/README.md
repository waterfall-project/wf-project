# Licence and contributions

> This is the English version of [README-fr.md](README-fr.md); when the two differ, the French text
> is the reference.

The agreement and the commitments apply from their merge into `main` (« Adopting it »,
below); earlier contributions are received under the repository's licences
alone.

| File | Contents |
|---|---|
| [`CLA.md`](CLA.md) | the public template of the contributor licence agreement: the contributor remains the holder of their rights, and grants a licence that allows the maintainer to distribute the project under other conditions than its free licences |
| [`ENGAGEMENTS.md`](ENGAGEMENTS.md) | what the project promises to its community edition, the counterpart of the agreement |

## Why now

Waterfall is published under free licences — AGPL-3.0-only for the code, CC BY-SA 4.0 for
the specification, Apache-2.0 for the interface contract —, and `CONTRIBUTING.md` receives
contributions under these licences alone. A contribution received this way can no longer be
distributed under other conditions without its author's agreement: the first outside
contribution accepted would close the dual licence, and any commercial edition that integrated it.

As of 18 October 2026, the history of `main` counts no outside contribution: the
commits are the author's, assisted by Claude, and two come from Dependabot, dependency
updates. Adopting the agreement before the first outside contribution therefore asks
nobody's agreement; adopting it afterwards would ask that of every contributor. The same reason
holds for the licence of the interface contract, chosen at the same time (« The decisions taken »,
below).

## The signing process

The pull requests of the repository are reserved to its collaborators. The agreement is therefore
signed before becoming one, outside GitHub (`CLA.md`, article 12):

1. the contributor writes to `contact@waterfall-project.pro` to ask to contribute;
2. the maintainer sends them the agreement as a PDF, whose annex carries their full identity and their
   notification address; the contributor completes the annex and signs — simple electronic
   signature, or PDF returned signed — from the email address the annex declares;
3. the maintainer countersigns, returns a copy to the contributor, and keeps the signed copy
   with the message that carried it in a private register: name, email, GitHub identifier,
   date, version signed;
4. they add the contributor's GitHub account to the collaborators of the repository.

The maintainer's identity is thus handed only to an identified contributor, who undertakes not
to disclose it (article 11), and each agreement is traced. The status of collaborator takes the place
of the check a tool would put in the chain: a pull request can only come from an account
that has signed.

**Why not CLA Assistant.** It keeps the signed text in a gist, readable by anyone who has
the link, and does not know how to hand each signatory an identity sheet of the maintainer:
the identity would remain outside the tool, and the signed agreement would not carry it. The
email process is enough for today's volume; if the volume grows, an electronic signature
tool that keeps the copies outside the repository will replace it.

## The choices of the agreement

- **A licence, not an assignment.** French law tightly frames assignment (article
  L131-3 of the intellectual property code), and the moral right cannot be assigned. A broad
  licence, with the right to sublicense, is enough for the dual licence and for a commercial
  edition; the contributor keeps their rights.
- **A framework contract, one licence per contribution.** The global assignment of future works is
  void (article L131-1). The agreement therefore bears on no work not submitted: it fixes in
  advance the conditions, and it is each submission that grants the licence (article 3.1). The
  contributor can end it for the future at any time (article 10.2).
- **Not a mere DCO.** The certificate of origin (`Signed-off-by`) attests that one has the right to
  contribute, not that one grants the right to change licence.
- **A maintainer who is a natural person, designated publicly by their GitHub identifier.** Their
  full identity is carried only by the signed copy. The licence also benefits their
  assigns and successors, including a company they would set up to exploit the project:
  it will not have to make every contributor sign again (articles 1, 3.1 and 10.3).
- **A confidentiality in both directions, and bounded.** The contributor does not disclose
  the maintainer's identity, until the latter makes it public themselves and at most ten
  years after the end of the agreement; the maintainer does not publish that of the contributor
  (article 11), and processes their data only to establish the rights granted (article 13).
- **A written counterpart, enforceable, and sanctioned.** The commitments say what a
  paid offer will never do to the community edition; article 6.2 of the agreement makes them
  enforceable for each contribution, in their wording of the day it was submitted, and
  article 6.4 says what a contributor can do if they are not held: withdraw, for their
  contribution, the right to distribute it under other conditions than a free licence. That is
  what makes such an agreement acceptable to a contributor — and it is also what protects it:
  the agreement is a contract of adhesion, and article 1171 of the civil code deems unwritten the
  clause that creates a significant imbalance in it. The commitments are the balance.
- **Declarations specific to the context.** The capacity to contract, the rights of an employer
  over the software of its employees (article L113-9), third-party code, and the content produced with
  an artificial intelligence tool, which this repository employs widely.
- **A single text for natural and legal persons.** A separate agreement for
  companies, on the model of the « Apache Corporate CLA », would double the text to maintain and to
  translate for a volume that does not justify it. Article 8 and the annex take its place, and
  the legal person guarantees the acceptance of the moral right by its employee authors.
- **A known structure.** That of the « Apache Individual CLA » — definitions, copyright
  licence, patent licence, declarations, absence of warranty —, rewritten in French law.

## The choices of the commitments

The split between the community edition and the paid offers — the whole specification
in the community edition, the paid part outside the core, through the public contract — is the one the
discussion of 11 October 2026 retained, and that the arbitration of 18 October confirms.

- **E-02 rules out a paid portfolio.** It is the « open core » model by buyer, the one
  contributors flee: it would contradict E-03 at the first function that changes side. The
  paid part keeps the connectors, the services and the separate programs.
- **E-04 rules out keyed modules in the core.** With them, E-03 could no longer be verified, and
  the core would have to carry extension points that the specification does not provide for.
- **E-07 sets the notice period at six months.** The notice serves only to warn: article 6.2 already
  protects each past contribution, until the change takes effect.

## The decisions taken

1. **The SPDX headers do not change.** They say `2026 waterfall-project` for the code and
   `2026 Projet Waterfall` for the specification. Copyright arises without formality
   (article L111-1): the mention names the project under which the work is disclosed, and
   the copy of the agreement identifies the holder. A work disclosed under a project name
   falls under the regime of the pseudonymous work: its protection runs seventy years from
   publication as long as the author does not make themselves known (article L123-3), which they can
   do at any time, and which will happen in fact at the first commercial licence, which names
   its licensor, or at the registration of a company that takes over the project. Article 11.1
   then ceases to apply.
2. **Issues, open to all.** Only pull requests are reserved to collaborators.
   A wording proposed in an issue or a review finding by a person who has not
   signed is received under the licence of the file it targets, by GitHub's terms of
   service (« inbound = outbound », section D.6). The maintainer rewrites it before integrating it;
   they take up a substantial wording as is only after its author has signed the
   agreement. `CONTRIBUTING.md` and the forms of `.github/ISSUE_TEMPLATE/` say so.
3. **The interface contract under Apache-2.0.** Under AGPL, an integrator who generates a client
   from the contract could fear that this client would have to be too. The Apache licence lifts this
   doubt, brings a patent grant, and remains compatible with the AGPL; E-01 provides for it.
   `REUSE.toml` declares it for the YAML files of `docs/api`; the tools of the contract and the
   client the front generates from it remain under AGPL.

## The positions taken

Each question the draft raised is settled in the text; here is the reason for each
position, so that a review can contest it knowingly.

- **The formalism of article L131-3.** Case law applies it to assignment; its
  extension to the licence is debated. Article 3.1 follows it out of caution: each right is
  mentioned separately, with its scope, its purpose, its place and its duration, and
  article 3.5 says so. It costs nothing and closes the question.
- **The forms of exploitation that cannot be foreseen (article L131-6).** The agreement does not
  cover them: such a clause would require a share of the profits, absurd in a free licence.
  The cost is not covering those forms, which nobody can name; the known forms,
  including software as a service, are listed.
- **Free of charge.** Article L122-7 allows a grant free of charge; article 3.5 refers
  to it.
- **The patent licence.** European law excludes the computer program « as
  such » (article 52 of the European patent convention), but admits computer-implemented
  inventions that produce a technical effect. A contributor who held
  one could, without article 4, submit their code then sue the project
  and its users for infringement. The article costs nothing to whoever has no patent; it stays.
- **The moral right outside software.** Article L121-7 holds only for software. For the
  specification and the documentation, article 5.2 founds the same terms on the consent
  given knowingly to a work revised continuously, and on clause 2.b.1 of
  CC BY-SA 4.0, which every contributor to the specification already accepts by publishing under that
  licence. Integrity remains protected against harm to honour and reputation, which no
  anticipated consent can lift. The right of withdrawal (article L121-4) subsists for these
  works, under the legal condition of first indemnifying the party exploiting them; it did not have to
  be written.
- **The force of article 6.2 and its sanction.** A contractual commitment is performed in kind
  or resolves into damages (articles 1217 and following of the civil code). Article 6.4
  stipulates the sanction that makes sense: after a formal notice left without effect for sixty days,
  the contributor withdraws, for their contribution, the right to distribute it otherwise than under
  a free licence. The free licences already granted to third parties remain — the AGPL and
  CC BY-SA are irrevocable —, so that the sanction withdraws exactly what the agreement
  gives, and nothing from the community.
- **Confidentiality (article 1210 of the civil code).** A commitment without a term would be
  perpetual. Article 11.1 ceases when the maintainer makes their identity public themselves, and
  at the latest ten years after the end of the agreement. The sanction is that of ordinary law
  (article 11.3); a penalty clause would make contributors flee for a risk that the
  inevitable publicity of the identity makes low.
- **The signature (articles 1366, 1367 and 1375 of the civil code).** A simple electronic
  signature, or a PDF signed and returned, are admitted as evidence; only the qualified signature
  benefits from a presumption of reliability, and whoever relies on a simple signature must,
  if contested, establish its reliability. The sending from the declared address, the message
  kept in the register, the invitation of the GitHub account and the commits that come from it form
  that evidence. The agreement is bilateral — the maintainer binds themselves under articles 6, 11 and
  13 —: it takes as many originals as parties, hence the countersignature and the copy returned
  (article 12.1). No proof of identity: the « Apache Individual CLA » asks for none,
  and it would weigh down the data processing for a guarantee that the declarations of
  article 7 already give (article 12.5).
- **Personal data.** The basis is the performance of the contract (article 6.1.b of the GDPR),
  then the legitimate interest in keeping the evidence of the rights (article 6.1.f). Retention
  runs five years after the end of the exploitation, the limitation period of contractual
  actions (article 2224 of the civil code). Erasure is limited by article 17.3.e of the
  GDPR as long as the evidence can serve. Article 13 names the recipients — hosting
  and email providers, counsel — and the right to refer to the CNIL.
- **Jurisdiction.** Between parties who are not all traders, a clause conferring
  territorial jurisdiction is deemed unwritten (article 48 of the code of civil procedure),
  and copyright litigation falls to judicial courts designated by decree
  (article L331-1 of the intellectual property code). Article 14.3 retains the
  French courts and, where the law allows agreeing on it — notably with a contributor
  established outside France —, those of the maintainer's domicile, which the copy states without
  the public template saying it.
- **Code written with an artificial intelligence assistant.** Copyright protects
  the work of the mind that bears the imprint of its author. What an assistant produces without
  human creative input is not protected; what the author has designed, specified, chosen, reviewed and
  reworked is, to the extent of that input, and the whole is as selection and arrangement.
  For the dual licence, the consequence is that the unprotected part is exclusive to
  nobody: the value of a commercial edition then lies in the brand, the service, and the
  protected parts. The agreement has nothing more to say about it than article 7.5.
- **The headers and the pseudonymous work.** See « The decisions taken », point 1.
- **The « Waterfall » trademark.** The word designates a project management method: for a
  piece of software in this field, it is descriptive, and a filing of the word alone risks refusal
  for lack of distinctive character (article L711-2 of the intellectual property code, article 7.1.c
  of the European Union trade mark regulation). A semi-figurative mark — the logo and the
  word — can be filed, with thin protection on the word alone; the commercial offer will gain from
  carrying a distinctive name, and the mention « the name and the logo are not covered by this
  licence » remains the good practice. Under AGPL, it is the trademark and not the licence that
  prevents a third party from hosting the unchanged software under the project's name.

## Adopting it

1. Publish the English translation of `CLA.md`.
2. Set up the process: the `contact@waterfall-project.pro` mailbox, the PDF template of the
   copy, drawn from `CLA.md` with its annex, and the private register, kept outside the repository.
3. Check that pull requests remain reserved to the collaborators of the repository.
4. Merge. The « Licence » section of `CONTRIBUTING.md`, the agreement and the commitments take
   effect at the merge.
