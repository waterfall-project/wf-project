<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/waterfall_logo-dark.svg">
    <img src="docs/assets/waterfall_logo.svg" alt="Waterfall" width="320">
  </picture>
</p>

Chiffrer, planifier et piloter des projets qui durent : un arbre de tâches commun, vu du
côté du temps et du côté de l'argent ; des révisions qui gardent lisibles chaque offre et
chaque revue ; des provisions pour risques ; des coûts réels importés de l'ERP ; et des
indicateurs de valeur acquise qui vont de la tâche au portefeuille.

Waterfall est fait pour les projets longs — dix ans, parfois quinze — où l'offre se négocie
pendant des mois, où le budget de référence ne se déplace que par un acte contractuel, et où
la question « en sommes-nous encore où nous l'avions dit ? » doit trouver sa réponse des
années après le départ de ceux qui y ont répondu la première fois.

> **État : le socle est en place, le produit pas encore.** La spécification et le contrat
> d'interface viennent d'abord ; le dépôt porte désormais aussi le back et le front vides,
> l'outillage et la chaîne par lesquels passera chaque ligne du produit. Le produit se
> construit EPIC par EPIC, comme le planifie [`docs/roadmap`](docs/roadmap/README.md).

## Ce qui le distingue

**Un seul arbre, deux vues.** Une tâche porte ses lignes de devis. Le planning et le devis
ne sont pas deux documents à tenir d'accord : c'est le même arbre, lu du côté du temps ou du
côté de l'argent.

**Une révision est un instantané complet.** Chaque offre et chaque revue périodique est
figée entière : ses structures de coûts, et les valeurs du référentiel qu'elle a employées —
taux horaires, calendriers, rôles. Une réorganisation ou un taux corrigé des années plus
tard ne la déplacent pas : une offre reste lisible et recalculable longtemps après avoir été
remise.

**Deux montants par ligne, jamais un.** Un montant budgété, que seul un acte contractuel
change, et un montant réestimé, que chaque revue met à jour. C'est ce qui empêche un avenant
de rebaser silencieusement le budget de référence sur la dernière prévision — le défaut qui
rend tant d'outils de contrôle des coûts discrètement optimistes.

**Les provisions n'entrent jamais au budget.** Couvrir un risque n'est pas se donner un
budget pour un travail qu'on espère ne pas faire. La révision de référence garde ses
provisions à part, comme réserve pour risques ; le reste à engager porte celles des risques
identifiés aujourd'hui, nouveaux compris ; un risque survenu entre dans le projet avec un
montant budgété nul. La couverture des risques compare la réserve à ce qu'ils ont coûté :
l'écart apparaît comme une dérive, ce qu'il est.

**La valeur acquise se constate, elle ne se déclare pas.** Une tâche est terminée ou elle ne
l'est pas ; son montant budgété est acquis le jour où elle se termine. Aucun pourcentage ne
se saisit, donc l'avancement ne se discute pas.

**Un indice de portefeuille est un rapport de sommes, jamais une moyenne d'indices.** Une
moyenne donne le même poids à une affaire de cinquante mille et à une affaire d'un million :
elle ne mesure rien.

## Ce que contient ce dépôt

| Chemin | Contenu |
|---|---|
| `docs/spec` | la spécification : **203 exigences**, ses sources Word et draw.io, la projection Markdown engendrée, les outils qui la produisent et les revues qui l'ont établie |
| `docs/api` | le contrat d'interface : **150 opérations** sur 116 chemins et 147 schémas, en OpenAPI écrit à la main, avec l'inventaire des endpoints et les décisions de conception |
| `docs/roadmap` | le plan : treize EPIC dans l'ordre où ils se construisent, leurs US, leur conception, et les règles qui mènent un EPIC de ses US au code livré |
| `docs/dev` | le guide de développement, les règles de codage par langage, et les règles que suivent les agents |
| `backend/` | un seul paquet Python : le noyau métier, le service d'API et le worker |
| `frontend/` | l'application Next.js, son client engendré du contrat, ses parcours de bout en bout |
| `tools/` | les outils du dépôt : couverture des exigences, contrôle de la roadmap, règles des sources, taille des lots |
| `fixtures/` | les exemples chiffrés de la spécification, et les données que sert le faux back |
| `deploy/` | l'empaquetage : le Compose de développement aujourd'hui, le chart Helm plus tard |
| `.github/workflows/` | la chaîne, exécutée sur chaque pull request |
| `.claude/agents/` | les agents qui cadrent un EPIC, en livrent les lots, développent et relisent |

**La spécification est en français**, comme la documentation. C'est un document d'exigences
formel — chacune porte un identifiant, un motif et un critère de vérification observable — et
le traduire doublerait la source de vérité. Le contrat, le code et le README principal sont en
anglais. [README.md](README.md) dit tout ceci en anglais.

### Par où commencer

- [`docs/api/INVENTORY.md`](docs/api/INVENTORY.md) — chaque endpoint, et l'exigence qu'il
  sert. La façon la plus rapide de voir ce que le produit fait.
- [`docs/api/DECISIONS.md`](docs/api/DECISIONS.md) — ce que le contrat a dû trancher, et
  pourquoi.
- [`docs/spec/waterfall-spec.md`](docs/spec/waterfall-spec.md) — la spécification entière,
  engendrée depuis Word pour qu'une machine puisse la lire.
- [`docs/spec/revue/constats/`](docs/spec/revue/constats/) — les revues. C'est là que
  vit le raisonnement : ce qui n'allait pas, ce qui l'a remplacé, et pourquoi.
- [`docs/roadmap/README.md`](docs/roadmap/README.md) — dans quel ordre le produit se
  construit, et comment le travail passe d'un EPIC au code relu.
- [`docs/dev/README.md`](docs/dev/README.md) — le guide de développement : où vit chaque
  chose, et quel contrôle tient chaque règle.

## Comment le travail se fait

Chaque exigence est close par un seul EPIC. Un EPIC se cadre — des US dont les critères
d'acceptation citent la spécification mot pour mot, une conception, un plan de lots —, puis se
livre un lot à la fois : une issue, une branche, une pull request vers la branche
d'intégration de l'EPIC, fusionnée seulement quand la revue locale et la chaîne sont au vert.
La chaîne ne lint, ne type et ne teste que ce qu'une modification touche, fait tourner la
couverture et les tests de bout en bout quand une pull request se fusionne, et échoue sur
toute exigence qu'un test cite à tort. Des agents peuvent cadrer, développer, relire et
livrer ; fusionner un EPIC dans `main` est toujours la décision d'une personne.

## Commandes

```bash
make                      # liste les commandes
make check-tools          # dit ce qui manque
make check BASE=origin/epic/EP-01  # les contrôles de ce que ma modification touche
make check-all            # toutes les familles de contrôles
make dev                  # le front contre le faux back, sur http://localhost:3000
make mock                 # le faux back seul, servi depuis les exemples du contrat
make e2e                  # les parcours de bout en bout, dans un navigateur
make requirements         # quelles exigences les tests couvrent
make roadmap              # la roadmap confrontée à la spécification
make build-doc            # régénère la projection Markdown depuis Word et draw.io
make generate-client      # régénère le client d'API du front depuis le contrat
```

Prérequis : [uv](https://docs.astral.sh/uv/), qui apporte Python 3.13 pour le back et les
outils ; un Python 3.11 ou plus sur le `PATH`, sous le nom `python3`, qui construit la
projection ; Node 24, dont corepack apporte pnpm ; Docker, pour `make dev` ; `pandoc` 3.1.11.1, la version avec laquelle
la projection est engendrée ; et `mmdc` (`npm i -g @mermaid-js/mermaid-cli`) pour valider les
diagrammes.

## Pile technique

Décidée dans la spécification, où chaque choix est argumenté plutôt qu'affirmé : **Next.js**
et **TypeScript** au front, avec des grilles propres fondées sur TanStack Table et des
courbes sur Apache ECharts ; **FastAPI** et **Python** derrière un noyau modulaire unique et
un worker ; **PostgreSQL** comme seule source de vérité, **Redis** pour le cache et la file
de tâches, un stockage **compatible S3** pour les fichiers en transit et les sauvegardes ;
**Helm** pour Kubernetes et **Compose** pour le développement et les petites installations.

Le contrat est écrit à la main et fait foi : le client du front en est engendré, le faux back
sert ses exemples, et la chaîne rejettera un service dont les réponses s'en écartent.

## Contribuer

[CONTRIBUTING.md](CONTRIBUTING.md) — comment la spécification se modifie (jamais en éditant
le Markdown engendré), comment fonctionne le cycle de revue, comment le code arrive par lots,
et les conventions qui ne se renégocient pas fichier par fichier.

## Licence

[GNU Affero General Public License v3.0](LICENSE) uniquement.
