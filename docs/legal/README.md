# Licence et contributions

> **Brouillons, sans effet.** Rien de ce répertoire ne s'applique tant qu'il n'a pas été relu par
> un avocat, complété et adopté (« Pour l'adopter », ci-dessous). D'ici là, `CONTRIBUTING.md`
> reçoit les contributions sous la seule licence AGPL-3.0.

| Fichier | Contenu |
|---|---|
| [`CLA.md`](CLA.md) | le modèle public de l'accord de licence de contribution : le contributeur reste titulaire de ses droits, et concède une licence qui permet au mainteneur de distribuer le projet sous d'autres conditions que l'AGPL |
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

## Le circuit de signature

Les pull requests du dépôt sont réservées à ses collaborateurs. L'accord se signe donc avant de
le devenir, hors de GitHub (`CLA.md`, article 12) :

1. le contributeur écrit à `contact@waterfall-project.pro` pour demander à contribuer ;
2. le mainteneur lui envoie l'accord en PDF, dont l'annexe porte son identité complète et son
   adresse de notification ; le contributeur complète l'annexe et signe — signature électronique
   simple, ou PDF renvoyé signé ;
3. le mainteneur conserve l'exemplaire signé dans un registre privé : nom, courriel,
   identifiant GitHub, date, version signée ;
4. il ajoute le compte GitHub du contributeur aux collaborateurs du dépôt.

L'identité du mainteneur n'est ainsi remise qu'à un contributeur identifié, qui s'engage à ne
pas la divulguer (article 11), et chaque accord est tracé. Le statut de collaborateur tient lieu
du contrôle qu'un outil poserait dans la chaîne : une pull request ne peut venir que d'un compte
qui a signé.

**Pourquoi pas CLA Assistant.** Il garde le texte signé dans un gist, lisible par quiconque en a
le lien, et ne sait pas remettre à chaque signataire une fiche d'identité du mainteneur :
l'identité resterait hors de l'outil, et l'accord signé ne la porterait pas. Le circuit par
courriel suffit au volume d'aujourd'hui ; si le volume augmente, un outil de signature
électronique qui garde les exemplaires hors du dépôt le remplacera.

## Les choix de ce brouillon

- **Une licence, pas une cession.** Le droit français encadre étroitement la cession (article
  L131-3 du code de la propriété intellectuelle), et le droit moral ne se cède pas. Une licence
  étendue, avec droit de sous-licencier, suffit à la double licence et à une édition
  commerciale ; le contributeur garde ses droits.
- **Pas un simple DCO.** Le certificat d'origine (`Signed-off-by`) atteste qu'on a le droit de
  contribuer, pas qu'on accorde celui de changer de licence.
- **Un mainteneur personne physique, désigné publiquement par son identifiant GitHub.** Son
  identité complète n'est portée que par l'exemplaire signé. La licence bénéficie aussi à ses
  ayants droit et successeurs, dont une société qu'il constituerait pour exploiter le projet :
  elle n'aura pas à faire signer de nouveau chaque contributeur (articles 1, 3.1 et 10.3).
- **Une confidentialité dans les deux sens.** Le contributeur ne divulgue pas l'identité du
  mainteneur ; le mainteneur ne publie pas celle du contributeur (article 11), et ne traite ses
  données qu'à établir les droits concédés (article 13).
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

1. **Les en-têtes SPDX.** Ils disent `2026 waterfall-project`, une organisation GitHub et non
   une personne. Les faire porter l'identité civile du mainteneur la rendrait publique ; ils
   peuvent porter son identifiant GitHub, comme un pseudonyme, ou garder le nom du projet
   (question au conseil, ci-dessous). Le choix touche `REUSE.toml`, les en-têtes du code et le
   guide (`docs/dev/README.md`, « En-têtes et licences »). Il faut savoir aussi que la
   confidentialité de l'identité ne durera, en pratique, que jusqu'à la première licence
   commerciale, qui nommera son concédant, ou jusqu'à la société immatriculée qui reprendrait
   le projet : l'article 11.1 cesse alors de s'appliquer à ce qui est devenu public.
2. **E-02 et E-04**, qui écartent un portefeuille payant et des modules payants dans le noyau
   (`ENGAGEMENTS.md`). Si l'un ou l'autre doit rester possible, c'est avant l'adoption qu'il faut
   les réécrire : après, l'article 6.2 les tient pour chaque contribution reçue.
3. **Le préavis** d'E-07.
4. **Les issues, ouvertes à tous.** Seules les pull requests sont réservées aux collaborateurs.
   Une issue ou un constat de revue venu d'une personne qui n'a pas signé peut porter une
   rédaction proposée — les formulaires d'issue la demandent. Cette proposition n'est pas
   couverte par l'accord : soit le mainteneur la réécrit au lieu de la reprendre, soit il
   demande à son auteur de signer avant de l'intégrer. La règle retenue se dira dans
   `CONTRIBUTING.md` et dans les formulaires de `.github/ISSUE_TEMPLATE/`.
5. **La licence du contrat d'interface.** `docs/api` est sous AGPL-3.0-only (`REUSE.toml`). Un
   intégrateur qui engendre un client du contrat peut craindre que ce client doive l'être aussi.
   Une licence permissive pour le contrat — Apache-2.0, MIT ou CC-BY-4.0 — ouvrirait les
   intégrations sans rien ôter au noyau ; E-01 la permet. La décision est indépendante de
   l'accord, mais relève de la même relecture.
6. **Les crochets de l'accord** : l'identifiant GitHub du mainteneur (article 1 et annexe), la
   durée de conservation des données après l'exploitation (article 13), la juridiction
   (article 14) ; et la traduction anglaise, que l'article 14 annonce.

## Questions pour le conseil

Chacune est reprise à l'endroit du texte qu'elle concerne, dans une note « À valider », sauf les
deux dernières, qui débordent l'accord.

- Le formalisme de l'article L131-3 s'applique-t-il à une licence, et l'article 3.1 de
  l'accord y satisfait-il ?
- Que coûte de ne pas viser l'exploitation sous une forme non prévisible (article L131-6) ?
- Les modalités d'exercice du droit moral de l'article 5 valent-elles pour les contributions
  qui ne sont pas du logiciel — documentation, spécification, figures —, auxquelles l'article
  L121-7 ne s'applique pas ?
- Quelle est la force de l'engagement de l'article 6.2, et que risque le mainteneur s'il ne le
  tient pas ?
- L'engagement de confidentialité de l'article 11.1, que le texte ne borne pas dans le temps,
  tient-il au regard de l'article 1210 du code civil, et quelle en est la sanction ?
- Une signature électronique simple, ou un PDF renvoyé signé, suffisent-ils (articles 1366 et
  1367 du code civil) ? L'identité déclarée dans l'annexe, sans justificatif, suffit-elle à
  établir la chaîne des droits qu'une double licence suppose ?
- Le traitement des données de l'article 13 — sa base, la durée de conservation, la limite
  apportée à l'effacement (article 17.3.e du RGPD) — est-il correctement posé ?
- La licence de brevet de l'article 4 a-t-elle une portée utile en droit européen ?
- Le code de ce dépôt est en grande partie écrit avec un assistant d'intelligence artificielle :
  quelle protection le droit d'auteur lui donne-t-il, et qu'en résulte-t-il pour une double
  licence ?
- Les en-têtes de droit d'auteur peuvent-ils nommer le mainteneur par son identifiant GitHub,
  comme l'auteur d'une œuvre pseudonyme (articles L113-6 et L123-3), et qu'est-ce que cela
  change à l'exercice et à la durée de ses droits ?
- « Waterfall » désigne une méthode de gestion de projet. Le nom est-il protégeable comme marque
  pour un logiciel de ce domaine, ou faut-il un autre nom pour l'offre commerciale ? Sous AGPL,
  c'est la marque, et non la licence, qui empêche un tiers d'héberger le logiciel inchangé sous
  son nom.

## Pour l'adopter

1. Faire relire, trancher les notes, compléter les crochets, retirer les bandeaux « Brouillon »
   et les notes.
2. Publier la traduction anglaise de `CLA.md`.
3. Mettre en place le circuit : la boîte `contact@waterfall-project.pro`, le modèle PDF de
   l'exemplaire, tiré de `CLA.md` avec son annexe, et le registre privé, tenu hors du dépôt.
4. Vérifier que les pull requests restent réservées aux collaborateurs du dépôt.
5. Fusionner. La section « Licence » de `CONTRIBUTING.md` prend effet à la fusion.
6. Mettre à jour les en-têtes SPDX et `REUSE.toml` selon le point 1.
