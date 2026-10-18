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
Une attend son tour : l'annexe B, dont le minimum tranché est écrit (C-364).

## 1. Les formats Excel de l'annexe B

- **Où** : annexe B ; WF-INTF-0070 à WF-INTF-0140 ; WF-CRE-0010 et WF-CRE-0020.
- **Quand** : à la remise par l'auteur d'un exemple de chaque fichier, puis au cadrage d'EP-09
  pour le format « Coûts réels », et d'EP-07 et EP-09 pour « Devis » et « Reste à engager »
  (EP-12, abandonné, les répartit). La reprise du 2026-10-18 a écrit le minimum tranché
  (C-364) : un paragraphe par format, la désignation de la tâche, la version inscrite dans le
  fichier, l'onglet « Hors lot » et la cellule de sous-projet vide.
- **Reste à fixer** : l'emplacement du numéro de version dans le fichier, et les en-têtes de
  colonnes de chaque format.
- **PO-01** : l'extraction des engagements et des heures relève de l'après-MVP ; le format
  étant versionné, il s'étendra sans rendre illisibles les fichiers existants.
