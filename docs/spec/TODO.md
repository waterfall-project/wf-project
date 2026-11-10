# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

Les trente-six entrées de la passe du 2026-10-03 sont tranchées et intégrées ; leurs
décisions se lisent dans l'historique Git de ce fichier (dernière version complète au
commit d314a11). Celle de #634 est intégrée (C-256) ; celles de #749, #808, de la
restauration et de #948 le sont par la reprise du 2026-10-18 (C-353, C-355, C-356, C-357).
La dernière, les formats Excel de l'annexe B, l'est par la reprise du 2026-10-22 (C-370) : la
version 1 des formats « Devis », « Reste à engager » et « Coûts réels », sur les exemples de
l'auteur et deux prototypes engendrés (`docs/spec/exemples/`).

## Le montant d'un coût réel et l'élément d'OTP sans code de sous-projet (#2721, EP-09)

Relevé par la revue d'US-1610/L1 (#2403) ; décision de l'auteur du 2026-11-10 : les choix du lot
sont gardés et s'écrivent dans la spécification.

- **WF-CRE-0010, corps** — rien ne dit si un montant à plus de deux décimales s'arrondit ou se
  rejette. Texte proposé, après « un montant signé » : « , arrondi au centime à l'import, la
  moitié au plus loin de zéro (−0,005 donne −0,01) ».
- **WF-CRE-0020, corps et Vérif** — « Une ligne dont l'élément d'OTP n'a pas cette forme » ne dit
  pas le cas d'un élément sans rien après la barre oblique (`A.ABC.26001/`). Texte proposé pour le
  corps, après « le code projet peut contenir des points » : « ; une barre oblique suivie d'aucun
  code n'est pas de cette forme » ; pour le Vérif, « — vide, ou sans rien avant la barre
  oblique — » devient « — vide, ou sans rien avant ou après la barre oblique — ».

Le contrat le dit dans la description d'`ImportRejection` (US-1610/L2, #2404) ; la feuille de route
cite la phrase nouvelle du Vérif une fois le Word intégré.
