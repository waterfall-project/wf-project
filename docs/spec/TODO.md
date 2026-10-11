# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

Les trente-six entrées de la passe du 2026-10-03 sont tranchées et intégrées ; leurs
décisions se lisent dans l'historique Git de ce fichier (dernière version complète au
commit d314a11). Trois attendent leur tour.

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

## 2. Le Vérif de WF-ADM-0120 ne constate pas la modification d'un rôle (#749)

- **Où** : WF-ADM-0120, son Vérif.
- **Quoi** : le corps interdit de retirer au dernier compte administrateur l'une des
  permissions `users.write` ou `access_roles.write`, quel que soit le chemin — désactivation
  du compte, retrait de son rôle, modification ou suppression d'un rôle. Le Vérif ne constate
  que la désactivation et le retrait du rôle d'un compte : le refus de la modification d'un
  rôle, qu'EP-03 réalise (US-0380/L1b), n'est constaté par aucune phrase. Relevé par la revue
  d'US-0380/L1b ; décidé par l'auteur le 2026-10-11 : à intégrer à la prochaine passe.
- **Texte proposé**, à ajouter au Vérif : « La modification d'un rôle qui retirerait l'une de
  ces permissions au dernier compte qui les porte est refusée. »

## 3. La tâche planifiée se dépose par la commande du worker, pas par l'API (#808)

- **Où** : §4.2.1.5, PBS-5.3 « Tâches planifiées » ; §4.3.2, tableau 8, ligne TFX-10.
- **Quoi** : la révision du 2026-10-10 (C-280) fait demander la tâche planifiée — sauvegarde
  planifiée (WF-ADM-0170), lecture périodique des comptes du fournisseur d'identité — au
  service d'API, en HTTPS, sous un secret de la plateforme (TFX-10). La conception d'EP-03 et
  US-0370/L1 la font déposer par une commande du worker (`waterfall-worker enqueue`), qui
  l'inscrit dans la table des tâches de fond puis la met en file : la garantie de C-280 — la
  table fait foi avant la file — est tenue, sans opération ni secret de plus. Décidé par
  l'auteur le 2026-10-11 : la spécification suit la conception.
- **Texte proposé**, pour PBS-5.3 : « … déclenchées par la plateforme à l'heure convenue, par
  une commande du worker qui inscrit la tâche dans la table des tâches de fond et la met en
  file (WF-ARC-0090) ; le worker la prend comme les autres. » ; et TFX-10 retiré du tableau 8,
  ou réécrit « Tâches planifiées (PBS-5.3) → Base de données et file — inscription et mise en
  file par la commande du worker ».
