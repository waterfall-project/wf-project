# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

Les trente-six entrées de la passe du 2026-10-03 sont tranchées et intégrées ; leurs
décisions se lisent dans l'historique Git de ce fichier (dernière version complète au
commit d314a11). Deux attendent leur tour.

## 1. Les formats Excel de l'annexe B

- **Où** : annexe B ; WF-INTF-0070 à WF-INTF-0140 ; WF-CRE-0010 et WF-CRE-0020.
- **Quand** : au cadrage d'EP-09 pour le format « Coûts réels », au cadrage d'EP-12 pour
  « Devis » et « Reste à engager ». Décidé le 2026-10-03 : l'annexe reste à deux phrases
  jusque-là.
- **Déjà tranché**, à reprendre tel quel en rédigeant :
  - le fichier « Devis » présente une synthèse en premier onglet, puis un onglet par lot du
    lotissement ; le fichier « Reste à engager », un onglet par sous-projet ; le §3.2.3, le
    §3.4.5.2.1 et WF-INTF-0120 le disent déjà ;
  - une ligne désigne sa tâche par son identifiant de lignée, écrit par l'export, et à défaut
    par le libellé de la tâche ; un libellé ambigu est signalé au compte rendu, de sorte
    qu'un fichier construit de zéro dans Excel reste importable ;
  - une ligne de coût porte un numéro de pièce, une date de pièce, un montant signé, un
    élément d'OTP de la forme préfixe.code projet/code sous-projet (WF-CRE-0020), et des
    colonnes conservées à titre d'information — le fournisseur, le texte de la commande, la
    référence, le document d'achat (motif de WF-CRE-0010) ;
  - une ligne de devis ou de reste à engager désigne sa tâche et son sous-projet, sa
    catégorie ou, pour la main-d'œuvre, son rôle, sa quantité, sa charge ou son débours
    (WF-INTF-0100), son délai de paiement (WF-DEV-0020) et, pour le reste à engager, son
    montant réestimé ;
  - le numéro de version du format est inscrit dans le fichier (WF-INTF-0070), à un
    emplacement que l'annexe fixera ;
  - ce qu'il reste à dire : la ligne sans lot (le lot unique du lotissement par défaut) et
    la ligne sans sous-projet (l'ensemble « hors sous-projet »).
- **PO-01** : l'extraction des engagements et des heures relève de l'après-MVP ; le format
  étant versionné, il s'étendra sans rendre illisibles les fichiers existants.

## 2. Un sous-projet qu'une révision marquée cite ne se supprime pas

- **Où** : §4.4.1, WF-DAT-0080 (corps et Vérif) ; voisins : WF-PRJ-0050, WF-CRE-0020,
  la prose du §4.4.1 sur les régimes de suppression. Constat #634, relevé au cadrage d'EP-14
  (L42i).
- **Quoi** : la prose du §4.4.1 dit qu'un sous-projet référencé par une révision marquée
  n'est pas supprimable ; le corps et le Vérif de WF-DAT-0080 disent au contraire que sa
  suppression aboutit et le marque supprimé. **Décidé par l'auteur le 2026-10-10 : la
  suppression est refusée.** Les sous-projets déterminent la courbe de la valeur acquise ;
  supprimer un sous-projet qu'une révision marquée cite y aurait des effets de bord
  difficilement maîtrisables. Le contrat le tient (EP-14/L42l, #647 : condition
  `subproject_not_cited`, refus 409), comme il tient déjà le refus de supprimer un risque
  qu'une révision marquée cite (`risk_not_cited`).
- **Conséquences à reprendre en rédigeant** :
  - un sous-projet n'est plus jamais « marqué supprimé » : il se supprime physiquement tant
    qu'aucune révision marquée ni aucune ligne de coût ne le référence (WF-PRJ-0050 refuse
    déjà le second cas), et sa suppression est refusée au-delà ;
  - WF-CRE-0020 cite « un sous-projet marqué supprimé » : la mention devient sans objet pour
    les sous-projets ;
  - le risque suit la même règle que le sous-projet (refus) ; poste, lot, livrable et
    chronologie gardent le régime « marqué supprimé » (WF-PLA-0170 en dépend).
- **Texte proposé** :
  - corps de WF-DAT-0080, troisième phrase : « Un poste, un lot, un livrable ou une
    chronologie se supprime physiquement tant qu'aucune révision marquée ni aucune ligne de
    coût ne le référence ; au-delà, il est marqué supprimé, conservé, et n'est plus proposé
    à la saisie. Un sous-projet ou un risque qu'une révision marquée référence ne se
    supprime pas : la suppression est refusée, en nommant la raison. »
  - Vérif de WF-DAT-0080, deuxième phrase : « Celle d'un sous-projet référencé par une
    révision marquée est refusée, et le sous-projet reste proposé à la saisie. »
