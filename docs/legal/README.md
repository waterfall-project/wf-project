# Licence et contributions

> **Brouillons, sans effet.** Rien de ce répertoire ne s'applique tant qu'il n'a pas été relu par
> un avocat, complété et adopté (« Pour l'adopter », ci-dessous). D'ici là, `CONTRIBUTING.md`
> reçoit les contributions sous la seule licence AGPL-3.0.

| Fichier | Contenu |
|---|---|
| [`CLA.md`](CLA.md) | l'accord de licence de contribution : le contributeur reste titulaire de ses droits, et concède une licence qui permet de distribuer le projet sous d'autres conditions que l'AGPL |
| [`ENGAGEMENTS.md`](ENGAGEMENTS.md) | ce que le projet promet à son édition communautaire, contrepartie de l'accord |

## Pourquoi maintenant

Waterfall est publié sous AGPL-3.0-only, et `CONTRIBUTING.md` reçoit les contributions sous
cette seule licence. Une contribution reçue ainsi ne peut plus être distribuée sous d'autres
conditions sans l'accord de son auteur : la première contribution extérieure acceptée fermerait
la double licence, et toute édition commerciale qui l'intégrerait.

Au 11 octobre 2026, l'historique de `main` ne compte aucune contribution extérieure : les
commits sont de l'auteur, assisté par Claude, et un seul vient de Dependabot, une mise à jour de
dépendances. Adopter l'accord avant la première contribution extérieure ne demande donc l'accord
de personne ; l'adopter après demanderait celui de chaque contributeur.

## Les choix de ce brouillon

- **Une licence, pas une cession.** Le droit français encadre étroitement la cession (article
  L131-3 du code de la propriété intellectuelle), et le droit moral ne se cède pas. Une licence
  étendue, avec droit de sous-licencier, suffit à la double licence et à une édition
  commerciale ; le contributeur garde ses droits.
- **Pas un simple DCO.** Le certificat d'origine (`Signed-off-by`) atteste qu'on a le droit de
  contribuer, pas qu'on accorde celui de changer de licence.
- **Une contrepartie écrite et opposable.** Les engagements disent ce qu'une offre payante ne
  fera jamais à l'édition communautaire, et l'article 6.2 de l'accord les rend opposables pour
  chaque contribution, dans leur rédaction du jour où elle a été soumise. C'est ce qui rend un
  tel accord acceptable à un contributeur.
- **Des déclarations propres au contexte.** Les droits d'un employeur sur le logiciel de ses
  salariés (article L113-9), le code de tiers, et le contenu produit avec un outil
  d'intelligence artificielle, que ce dépôt emploie largement.
- **Une structure connue.** Celle de l'« Apache Individual CLA » — définitions, licence de droit
  d'auteur, licence de brevet, déclarations, absence de garantie —, réécrite en droit français.

Le découpage entre l'édition communautaire et les offres payantes que les engagements supposent
— la spécification entière dans l'édition communautaire, le payant hors du noyau, par le contrat
public — est celui que la discussion du 11 octobre 2026 a retenu comme point de départ. Les
engagements E-02 et E-04 le figent ; ce sont eux qu'il faut relire en premier.

## Ce qu'il reste à décider

1. **Le bénéficiaire** : l'auteur en nom propre, avec faculté de transférer l'accord à une
   société qu'il contrôle, ou une société créée d'abord. Les en-têtes SPDX disent aujourd'hui
   `2026 waterfall-project`, une organisation GitHub et non une personne : ils devront nommer le
   titulaire retenu — `REUSE.toml`, les en-têtes du code, et le guide
   (`docs/dev/README.md`, « En-têtes et licences »). Une adresse électronique ne suffit pas à
   désigner une partie à un contrat : l'accord nomme le bénéficiaire par son identité complète
   — nom et prénom, ou dénomination, forme, siège et immatriculation — et une adresse postale,
   l'adresse électronique ne servant qu'aux notifications. Une personne physique qui ne veut
   pas publier son adresse personnelle peut employer une adresse de domiciliation, ou porter
   l'accord par une structure immatriculée.
2. **E-02 et E-04**, qui écartent un portefeuille payant et des modules payants dans le noyau
   (`ENGAGEMENTS.md`). Si l'un ou l'autre doit rester possible, c'est avant l'adoption qu'il faut
   les réécrire : après, l'article 6.2 les tient pour chaque contribution reçue.
3. **Le préavis** d'E-07.
4. **L'outil de signature** : CLA Assistant, une application GitHub qui garde les signatures
   dans un gist, ou sa variante en GitHub Action, qui les garde dans le dépôt et pose un contrôle
   de plus dans la chaîne.
5. **La licence du contrat d'interface.** `docs/api` est sous AGPL-3.0-only (`REUSE.toml`). Un
   intégrateur qui engendre un client du contrat peut craindre que ce client doive l'être aussi.
   Une licence permissive pour le contrat — Apache-2.0, MIT ou CC-BY-4.0 — ouvrirait les
   intégrations sans rien ôter au noyau ; E-01 la permet. La décision est indépendante de
   l'accord, mais relève de la même relecture.
6. **La juridiction** de l'article 12, et la traduction anglaise de l'accord, que l'article 12
   annonce.

## Questions pour le conseil

Chacune est reprise à l'endroit du texte qu'elle concerne, dans une note « À valider ».

- Le formalisme de l'article L131-3 s'applique-t-il à une licence, et l'article 3.1 de
  l'accord y satisfait-il ?
- Que coûte de ne pas viser l'exploitation sous une forme non prévisible (article L131-6) ?
- Les modalités d'exercice du droit moral de l'article 5 valent-elles pour les contributions
  qui ne sont pas du logiciel — documentation, spécification, figures —, auxquelles l'article
  L121-7 ne s'applique pas ?
- L'acceptation par un commentaire sur une pull request suffit-elle (articles 1366 et 1367 du
  code civil) ?
- Quelle est la force de l'engagement de l'article 6.2, et que risque le bénéficiaire s'il ne le
  tient pas ?
- La licence de brevet de l'article 4 a-t-elle une portée utile en droit européen ?
- Le code de ce dépôt est en grande partie écrit avec un assistant d'intelligence artificielle :
  quelle protection le droit d'auteur lui donne-t-il, et qu'en résulte-t-il pour une double
  licence ?
- Hors de l'accord, mais lié à toute édition commerciale : « Waterfall » désigne une méthode de
  gestion de projet. Le nom est-il protégeable comme marque pour un logiciel de ce domaine, ou
  faut-il un autre nom pour l'offre commerciale ? Sous AGPL, c'est la marque, et non la licence,
  qui empêche un tiers d'héberger le logiciel inchangé sous son nom.

## Pour l'adopter

1. Faire relire, trancher les notes, compléter les crochets, retirer les bandeaux « Brouillon »
   et les notes.
2. Publier la traduction anglaise de `CLA.md`.
3. Mettre en place l'outil de signature, et son contrôle dans la chaîne.
4. Fusionner. La section « Licence » de `CONTRIBUTING.md` prend effet à la fusion : l'outil doit
   être en place avant.
5. Mettre à jour les en-têtes SPDX et `REUSE.toml` au nom du titulaire retenu.
