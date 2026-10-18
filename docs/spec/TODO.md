# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

Les trente-six entrées de la passe du 2026-10-03 sont tranchées et intégrées ; leurs
décisions se lisent dans l'historique Git de ce fichier (dernière version complète au
commit d314a11). Cinq attendent leur tour ; celle de #634 est intégrée (C-256).

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

## 4. La restauration réinscrit le journal par identifiant (#892, #893, #894)

- **Où** : WF-ADM-0160, son corps et son Vérif.
- **Quoi** : la conception d'EP-03 (PR #939), sur les décisions de l'auteur du 2026-10-12,
  s'écarte de la lettre de l'exigence en trois points, relevés par la revue d'US-0440/L1 :
  - **le journal par identifiant** (#894) : le corps dit les inscriptions « postérieures à la
    date de la sauvegarde » relues avant le remplacement des bases et réinscrites après lui, et
    que la restauration « remplace l'intégralité des deux bases ». Le vidage n'étant pas
    instantané au regard de cette date, une inscription faite pendant lui serait doublée ou
    perdue : la restauration réinscrit les inscriptions dont l'identifiant manque au journal
    restauré. Sur la même installation, le résultat est celui du corps ; sur une autre, les
    inscriptions de la cible antérieures à la date de la sauvegarde sont gardées aussi. Le
    corps et le Vérif (« rien de postérieur, hors le journal d'audit ») sont à mettre d'accord
    avec cette réinscription ;
  - **la table des sauvegardes est gardée** (#893) : relue et réinscrite comme le journal,
    sans quoi la liste perdrait les sauvegardes prises après celle qu'on restaure, dont les
    archives restent sur le stockage objet ;
  - **les tâches restaurées en cours passent en échec** (#892) : une tâche restaurée en file
    ou en cours passe en échec avant la reprise du worker, sans quoi la sauvegarde en cours au
    moment du vidage se relancerait et écraserait son archive.
  Décidé par l'auteur le 2026-10-12 : à intégrer à la prochaine passe.
- **Texte proposé**, pour le corps : « … Le journal d'audit (WF-SEC-0030) est conservé à
  travers la restauration : ses inscriptions absentes du journal restauré sont relues avant
  le remplacement des bases et réinscrites après lui, de même que la liste des sauvegardes ;
  les traitements en attente ou en cours dans les bases restaurées sont terminés en échec ; la
  restauration elle-même s'inscrit au journal une fois faite. » ; et pour le Vérif : « … et
  rien de postérieur, hors le journal d'audit et la liste des sauvegardes, qui gardent leurs
  inscriptions et leurs sauvegardes ; le journal nomme la restauration. »

## 5. Les tests de la chaîne contre le Compose : les parcours sur la plateforme de développement (#948)

- **Où** : WF-ARC-0050, son Vérif ; §4.4, la chaîne CI/CD (« exécute les tests contre une
  plateforme Compose »).
- **Quoi** : le Vérif demande que « les tests de la chaîne CI/CD s'exécutent contre » la
  plateforme que le fichier Compose démarre à partir des mêmes images que le chart, soit, en
  EP-03, le Compose de démonstration (`compose.prod.yaml`). Les parcours contre le service
  (US-0340) se jouent sur le Compose de développement (`compose.service.yaml`), construit des
  mêmes Dockerfiles : le Compose de démonstration demande un nom public, des certificats et un
  amorçage. Il est prouvé par un essai de la chaîne (`make production-trial`) : amorçage, sonde
  de vie, TLS et redirection vers HTTPS, en-têtes, console de Keycloak masquée, fixation du
  mot de passe du premier administrateur, connexion. Relevé par la réalisation d'US-0430/L2 ;
  décidé par l'auteur le 2026-10-12 : l'écart est noté sous US-0430, et le Vérif est à mettre
  d'accord à la prochaine passe.
- **Texte proposé**, pour la dernière phrase du Vérif : « Le fichier Compose démarre une
  plateforme complète sur une machine seule, à partir des mêmes images que le chart, et la
  chaîne CI/CD y joue un essai de démarrage, d'amorçage et de connexion ; ses parcours de bout
  en bout s'exécutent contre une plateforme Compose construite des mêmes sources. »
