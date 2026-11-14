---
id: EP-28
titre: Tenir la chaîne et les outils du dépôt
statut: à planifier
depend_de: rien
famille: plateforme
issue:
---

# EP-28 — Chaîne et outillage de développement

## Objet

Les revues des lots laissent des constats qui ne touchent aucun code du produit : la chaîne
d'intégration, les gardes du dépôt, les outils des tests, le guide. Ils étaient reportés vers EP-13
ou vers l'EPIC ouvert du moment, où ils n'avaient pas leur place.

L'EPIC les rassemble. Il ne dépend d'aucun autre et ne clôt aucune exigence : il se glisse entre
deux EPICs fonctionnels, ou se joue par lots d'appoint.

## Ce qui en fait partie

- la chaîne : les images et leur miroir, les montées de Dependabot, les téléchargements à la
construction (#2255, #2452, #2643, #3025, #3028, #3041) ;
- les gardes et les outils du dépôt (#839, #850, #851, #975, #1007, #2417, #3104, #3108) ;
- les outils et les supports des tests du back et des parcours (#818, #898, #899, #935, #946, #958,
#2388, #2457, #3137, #3149) ;
- le guide (#3057, #3161).

## Ce qui n'en fait pas partie

- les défauts du code livré, même mineurs : chacun va à l'EPIC qui touche ce code ;
- l'exploitation de la plateforme — EP-13.

## Exigences réalisées

Aucune : l'EPIC ne réalise ni ne clôt d'exigence. Son tableau reste vide.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Aucune.

## Préalables

Rien.

## Définition de fini

- chaque constat reçu est corrigé, ou clos avec sa raison ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #818 — back : un test de la planification nomme un mot de passe qu'il ne lit plus ;
- #839 — front : les gardes de sources retirent pour un commentaire ce qui suit un /* écrit dans une
chaîne ;
- #850 — outil : plus aucun test ne dit qu'une page ne réveille pas la famille front-image ;
- #851 — doc : le Contrôle de la règle des actions serveur dit lire chaque source du build ;
- #898 — outil : trois mineurs du tour 2 d'US-0420 (ligne d'installation laissée, témoin des rôles
hors famille keycloak, migrations qui exigent Redis) ;
- #899 — test : deux mineurs du tour 3 d'US-0420 (verrou et processus hors du try, diagnostic perdu)
;
- #935 — outil : la fixture logs de conftest pose de faux secrets de la plateforme dans
l'environnement ;
- #946 — outil : quatre finitions du client de contrat fermé des tests du back ;
- #958 — outil : les tests du back migrent en superutilisateur, une migration qui l'exige ne casse
qu'après fusion ;
- #975 — outil : make requirements compte les citations des tests ignorés (fixme, skip) ;
- #1007 — outil : les identifiants de corrélation des exemples n'ont pas de registre, deux lots
parallèles prennent le même ;
- #2255 — chaîne : les leviers de l'audit du 2026-11-05 restent à prendre — miroir des images, cache
sous 10 Go, installation.setup, tests témoin des outils, .next/cache ;
- #2388 — front : projects.spec.ts ne se rejoue pas sur une plateforme de service déjà jouée ;
- #2417 — outil : le garde laisse passer des formes voisines de find -exec rm, xargs rm et rm -rf
sur .git, et make merge-queue non adjacent ;
- #2452 — chaîne : la construction de l'image api télécharge la clé apt de PostgreSQL depuis
postgresql.org, et la file échoue quand le site ne répond pas ;
- #2457 — outil : mockdata.py au plafond de 1000 lignes ;
- #2643 — chaîne : actionlint-py télécharge son binaire à chaque construction ;
- #3025 — outil : les montées d'images de Dependabot et le miroir de la chaîne ;
- #3028 — outil : quatre finitions du miroir de la chaîne (test d'image nue, messages, Dependabot
dans le guide) ;
- #3041 — outil : le client PostgreSQL 18 du runner dit « d'Ubuntu 26.04 » alors qu'il vient du
dépôt PGDG ;
- #3057 — documentation : une ligne du paragraphe d'US-1920 dépasse la largeur du fichier ;
- #3104 — outil : le refus à la lecture de check-service et check-all en TIER=full n'a pas de test ;
- #3108 — outil : trois mineurs du deuxième tour d'US-1910/L3 — la forme de SHARD hors e2e-service,
une apostrophe dans le $(shell) de la garde, l'exclusion écrite en dur du test des durées ;
- #3137 — back : des tests comparent l'année prise par le test à celle que le service prend à la
requête, et échouent au passage du nouvel an ;
- #3149 — outil : test_e2ebrowser, deux tests attendent une seconde fixe avant d'interrompre le
shell ;
- #3161 — outil : le défaut n° 22 de typescript.md, « une exception et une seule », ambigu pour un
état vidé quand une prop le relaie.
