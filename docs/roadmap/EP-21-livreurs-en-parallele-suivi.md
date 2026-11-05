---
id: EP-21
titre: Combler ce que l'outillage des livreurs en parallèle laisse passer, avant l'essai à N = 4
statut: à planifier
depend_de: EP-19
famille: plateforme
issue:
---

# EP-21 — Livreurs en parallèle : suivi

## Objet

EP-19 a rendu le dépôt sûr pour plusieurs livreurs à la fois sur un même poste. Ses revues
locales ont relevé des écarts qu'aucun lot ne pouvait reprendre (décision de l'auteur du
2026-11-04) : des formes d'arrêt ou de suppression qu'un agent peut écrire sans malice et que le
garde des commandes laisse passer, deux démarrages concurrents des services de test d'un même
créneau, et l'accord entre le gabarit du tableau de suivi et `make tracking`, que rien
n'éprouve. EP-21 les comble. À N = 1, ils restent rares ; ils compteront à l'essai à N = 4.

Il dépend d'EP-19. Son rang se fixe à son cadrage.

## Ce qui en fait partie

- les constats ci-dessous, à détailler en US au cadrage.

## Ce qui n'en fait pas partie

- les formes qui ne s'écrivent que pour contourner le garde : ce sont des limites connues
  d'US-1080 (EP-19, « Hors périmètre ») ;
- relever N et l'essai à N = 4 : c'est l'auteur qui les fait, sur la nouvelle machine, selon
  le guide (EP-19).

## Exigences réalisées

Aucune : c'est l'outillage du dépôt, comme EP-19.

## Opérations du contrat

Aucune.

## Préalables

EP-19 livré.

## Définition de fini

À écrire au cadrage.

## Constats reçus

Reportés d'EP-19 (décision de l'auteur du 2026-11-04) :

- #1890 — outil : les formes d'arrêt que le garde des commandes ne voit pas, sauf celles qui ne
  s'écrivent que pour le contourner. Restent : `find … -delete`, `find … -exec rm`,
  `mv .git/index.lock …`, `docker rmi`, `docker volume rm`, et les préfixes que le garde ne suit
  pas (`busybox`, `su -c`, `flock`, `watch`).
- #1893 — outil : le garde suit mal un `cd` dans `.git` (sous `bash -c`, par `pushd`,
  `env -C`, un chemin calculé, ou derrière `command` et `builtin` ; un `cd ..` ne remet pas l'état
  à zéro) et les abréviations des options longues (`env --ch`).
- #1909 — outil : deux démarrages concurrents des services de test d'un même créneau.
- #1915 — outil : rien n'éprouve que le tableau du gabarit d'un EPIC se modifie par
  `make tracking`.
