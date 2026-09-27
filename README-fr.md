<p align="center">
  <img src="docs/assets/waterfall_logo.svg" alt="Waterfall" width="320">
</p>

Chiffrer, planifier et piloter des projets qui durent : un arbre de tâches commun, vu du
côté du temps et du côté de l'argent ; des révisions qui gardent lisibles chaque offre et
chaque revue ; des provisions pour risques ; des coûts réels importés de l'ERP ; et des
indicateurs de valeur acquise qui vont de la tâche au portefeuille.

Waterfall est fait pour les projets longs — dix ans, parfois quinze — où l'offre se négocie
pendant des mois, où le budget de référence ne se déplace que par un acte contractuel, et où
la question « en sommes-nous encore où nous l'avions dit ? » doit trouver sa réponse des
années après le départ de ceux qui y ont répondu la première fois.

> **État : pas encore de code.** Ce dépôt porte la spécification et le contrat d'interface.
> L'implémentation en part, et non l'inverse.

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

**Les provisions restent hors du budget** jusqu'à la survenance du risque. Couvrir un risque
n'est pas se donner un budget pour un travail qu'on espère ne pas faire. À la survenance, le
budget n'augmente que de la provision, jamais du coût réel du risque : l'écart apparaît
comme une dérive, ce qu'il est.

**La valeur acquise se constate, elle ne se déclare pas.** Une tâche est terminée ou elle ne
l'est pas ; son montant budgété est acquis le jour où elle se termine. Aucun pourcentage ne
se saisit, donc l'avancement ne se discute pas.

**Un indice de portefeuille est un rapport de sommes, jamais une moyenne d'indices.** Une
moyenne donne le même poids à une affaire de cinquante mille et à une affaire d'un million :
elle ne mesure rien.

## Ce que contient ce dépôt

| Chemin | Contenu |
|---|---|
| `docs/spec` | la spécification : **203 exigences**, ses sources Word et draw.io, la projection Markdown engendrée, les outils du pipeline et les neuf revues qui l'ont établie |
| `docs/api` | le contrat d'interface : **150 opérations** sur 116 chemins et 147 schémas, en OpenAPI écrit à la main, avec l'inventaire des endpoints et les décisions de conception |

**La spécification est en français.** C'est un document d'exigences formel — chacune porte un
identifiant, un motif et un critère de vérification observable — et le traduire doublerait la
source de vérité. Le contrat, le code et le README principal sont en anglais.
[README.md](README.md) dit tout ceci en anglais.

### Par où commencer

- [`docs/api/INVENTAIRE.md`](docs/api/INVENTAIRE.md) — chaque endpoint, et l'exigence qu'il
  sert. La façon la plus rapide de voir ce que le produit fait.
- [`docs/api/DECISIONS.md`](docs/api/DECISIONS.md) — ce que le contrat a dû trancher, et
  pourquoi.
- [`docs/spec/waterfall-spec.md`](docs/spec/waterfall-spec.md) — la spécification entière,
  engendrée depuis Word pour qu'une machine puisse la lire.
- [`docs/spec/revue/constats/`](docs/spec/revue/constats/) — les neuf revues. C'est là que
  vit le raisonnement : ce qui n'allait pas, ce qui l'a remplacé, et pourquoi.

## Commandes

```bash
make                  # liste les commandes
make build-doc        # régénère la projection Markdown depuis Word et draw.io
make lint-openapi     # contrôle le contrat
make build-openapi    # contrôle puis assemble le contrat en un fichier
make mock             # sert un faux back depuis le contrat
make inventory        # régénère l'inventaire des endpoints et la couverture
make check-tools      # dit ce qui manque
```

Prérequis : Python 3.11 ou plus, `pandoc`, Node avec `npx`, et `mmdc`
(`npm i -g @mermaid-js/mermaid-cli`) pour valider les diagrammes.

## Pile technique retenue

Décidée dans la spécification, où chaque choix est argumenté plutôt qu'affirmé : **Next.js**
et **TypeScript** au front, avec des grilles propres fondées sur TanStack Table et des
courbes sur Apache ECharts ; **FastAPI** et **Python** derrière un noyau modulaire unique et
un worker ; **PostgreSQL** comme seule source de vérité, **Redis** pour le cache et la file
de tâches, un stockage **compatible S3** pour les fichiers en transit et les sauvegardes ;
**Helm** pour Kubernetes et **Compose** pour le développement et les petites installations.

Le contrat est écrit à la main et fait foi : le client du front en est engendré, et la chaîne
rejette une version dont les réponses s'en écartent.

## Contribuer

[CONTRIBUTING.md](CONTRIBUTING.md) — comment la spécification se modifie (jamais en éditant
le Markdown engendré), comment fonctionne le cycle de revue, et les conventions qui ne se
renégocient pas fichier par fichier.

## Licence

[GNU Affero General Public License v3.0](LICENSE) uniquement.
