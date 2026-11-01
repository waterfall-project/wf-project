# Licence et contributions

> Ce document est la version française de référence ; [README.md](README.md) en est la traduction
> anglaise.

L'accord et les engagements s'appliquent à compter de leur fusion dans `main` (« Pour
l'adopter », ci-dessous) ; les contributions antérieures sont reçues sous les seules licences du
dépôt.

| Fichier | Contenu |
|---|---|
| [`CLA.md`](CLA.md) | le modèle public de l'accord de licence de contribution : le contributeur reste titulaire de ses droits, et concède une licence qui permet au mainteneur de distribuer le projet sous d'autres conditions que ses licences libres |
| [`ENGAGEMENTS.md`](ENGAGEMENTS.md) | ce que le projet promet à son édition communautaire, contrepartie de l'accord |

## Pourquoi maintenant

Waterfall est publié sous des licences libres — AGPL-3.0-only pour le code, CC BY-SA 4.0 pour
la spécification, Apache-2.0 pour le contrat d'interface —, et `CONTRIBUTING.md` reçoit les
contributions sous ces seules licences. Une contribution reçue ainsi ne peut plus être
distribuée sous d'autres conditions sans l'accord de son auteur : la première contribution
extérieure acceptée fermerait la double licence, et toute édition commerciale qui l'intégrerait.

Au 18 octobre 2026, l'historique de `main` ne compte aucune contribution extérieure : les
commits sont de l'auteur, assisté par Claude, et deux viennent de Dependabot, des mises à jour
de dépendances. Adopter l'accord avant la première contribution extérieure ne demande donc
l'accord de personne ; l'adopter après demanderait celui de chaque contributeur. La même raison
vaut pour la licence du contrat d'interface, choisie en même temps (« Les décisions prises »,
ci-dessous).

## Le circuit de signature

Les pull requests du dépôt sont réservées à ses collaborateurs. L'accord se signe donc avant de
le devenir, hors de GitHub (`CLA.md`, article 12) :

1. le contributeur écrit à `contact@waterfall-project.pro` pour demander à contribuer ;
2. le mainteneur lui envoie l'accord en PDF, dont l'annexe porte son identité complète et son
   adresse de notification ; le contributeur complète l'annexe et signe — signature électronique
   simple, ou PDF renvoyé signé — depuis l'adresse électronique que l'annexe déclare ;
3. le mainteneur contresigne, renvoie une copie au contributeur, et conserve l'exemplaire signé
   avec le message qui l'a porté dans un registre privé : nom, courriel, identifiant GitHub,
   date, version signée ;
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

## Les choix de l'accord

- **Une licence, pas une cession.** Le droit français encadre étroitement la cession (article
  L131-3 du code de la propriété intellectuelle), et le droit moral ne se cède pas. Une licence
  étendue, avec droit de sous-licencier, suffit à la double licence et à une édition
  commerciale ; le contributeur garde ses droits.
- **Un contrat-cadre, une licence par contribution.** La cession globale des œuvres futures est
  nulle (article L131-1). L'accord ne porte donc sur aucune œuvre non soumise : il fixe par
  avance les conditions, et c'est chaque soumission qui concède la licence (article 3.1). Le
  contributeur peut y mettre fin pour l'avenir à tout moment (article 10.2).
- **Pas un simple DCO.** Le certificat d'origine (`Signed-off-by`) atteste qu'on a le droit de
  contribuer, pas qu'on accorde celui de changer de licence.
- **Un mainteneur personne physique, désigné publiquement par son identifiant GitHub.** Son
  identité complète n'est portée que par l'exemplaire signé. La licence bénéficie aussi à ses
  ayants droit et successeurs, dont une société qu'il constituerait pour exploiter le projet :
  elle n'aura pas à faire signer de nouveau chaque contributeur (articles 1, 3.1 et 10.3).
- **Une confidentialité dans les deux sens, et bornée.** Le contributeur ne divulgue pas
  l'identité du mainteneur, jusqu'à ce que celui-ci la rende lui-même publique et au plus dix
  ans après la fin de l'accord ; le mainteneur ne publie pas celle du contributeur
  (article 11), et ne traite ses données qu'à établir les droits concédés (article 13).
- **Une contrepartie écrite, opposable, et sanctionnée.** Les engagements disent ce qu'une
  offre payante ne fera jamais à l'édition communautaire ; l'article 6.2 de l'accord les rend
  opposables pour chaque contribution, dans leur rédaction du jour où elle a été soumise, et
  l'article 6.4 dit ce qu'un contributeur peut faire s'ils ne sont pas tenus : retirer, pour sa
  contribution, le droit de la distribuer sous d'autres conditions qu'une licence libre. C'est
  ce qui rend un tel accord acceptable à un contributeur — et c'est aussi ce qui le protège :
  l'accord est un contrat d'adhésion, et l'article 1171 du code civil répute non écrite la
  clause qui y crée un déséquilibre significatif. Les engagements sont l'équilibre.
- **Des déclarations propres au contexte.** La capacité de contracter, les droits d'un employeur
  sur le logiciel de ses salariés (article L113-9), le code de tiers, et le contenu produit avec
  un outil d'intelligence artificielle, que ce dépôt emploie largement.
- **Un seul texte pour les personnes physiques et morales.** Un accord distinct pour les
  entreprises, sur le modèle de l'« Apache Corporate CLA », doublerait le texte à maintenir et à
  traduire pour un volume qui ne le justifie pas. L'article 8 et l'annexe en tiennent lieu, et
  la personne morale se porte fort de l'acceptation du droit moral par ses salariés auteurs.
- **Une structure connue.** Celle de l'« Apache Individual CLA » — définitions, licence de droit
  d'auteur, licence de brevet, déclarations, absence de garantie —, réécrite en droit français.

## Les choix des engagements

Le découpage entre l'édition communautaire et les offres payantes — la spécification entière
dans l'édition communautaire, le payant hors du noyau, par le contrat public — est celui que la
discussion du 11 octobre 2026 a retenu, et que l'arbitrage du 18 octobre confirme.

- **E-02 écarte un portefeuille payant.** C'est le modèle « open core » par acheteur, celui que
  les contributeurs fuient : il contredirait E-03 à la première fonction qui change de côté. Le
  payant garde les connecteurs, les services et les programmes distincts.
- **E-04 écarte des modules à clé dans le noyau.** Avec eux, E-03 ne se vérifierait plus, et
  le noyau devrait porter des points d'extension que la spécification ne prévoit pas.
- **E-07 fixe le préavis à six mois.** Le préavis ne sert qu'à prévenir : l'article 6.2 protège
  déjà chaque contribution passée, jusqu'à la prise d'effet de la modification.

## Les décisions prises

1. **Les en-têtes SPDX ne changent pas.** Ils disent `2026 waterfall-project` pour le code et
   `2026 Projet Waterfall` pour la spécification. Le droit d'auteur naît sans formalité
   (article L111-1) : la mention nomme le projet sous lequel l'œuvre est divulguée, et
   l'exemplaire de l'accord identifie le titulaire. Une œuvre divulguée sous un nom de projet
   relève du régime de l'œuvre pseudonyme : sa protection court soixante-dix ans à compter de
   la publication tant que l'auteur ne se fait pas connaître (article L123-3), ce qu'il peut
   faire à tout moment, et ce qui arrivera de fait à la première licence commerciale, qui nomme
   son concédant, ou à l'immatriculation d'une société qui reprend le projet. L'article 11.1
   cesse alors de s'appliquer.
2. **Les issues, ouvertes à tous.** Seules les pull requests sont réservées aux collaborateurs.
   Une rédaction proposée dans une issue ou un constat de revue par une personne qui n'a pas
   signé est reçue sous la licence du fichier qu'elle vise, par les conditions d'utilisation de
   GitHub (« inbound = outbound », section D.6). Le mainteneur la réécrit avant de l'intégrer ;
   il ne reprend telle quelle une rédaction substantielle qu'après signature de l'accord par
   son auteur. `CONTRIBUTING.md` et les formulaires de `.github/ISSUE_TEMPLATE/` le disent.
3. **Le contrat d'interface sous Apache-2.0.** Sous AGPL, un intégrateur qui engendre un client
   du contrat pouvait craindre que ce client doive l'être aussi. La licence Apache lève ce
   doute, apporte une concession de brevet, et reste compatible avec l'AGPL ; E-01 la prévoit.
   `REUSE.toml` la déclare pour les fichiers YAML de `docs/api` ; les outils du contrat et le
   client que le front en engendre restent sous AGPL.

## Les positions prises

Chaque question que le brouillon posait est tranchée dans le texte ; voici la raison de chaque
position, pour qu'une relecture puisse la contester en connaissance de cause.

- **Le formalisme de l'article L131-3.** La jurisprudence l'applique à la cession ; son
  extension à la licence est discutée. L'article 3.1 le suit par prudence : chaque droit est
  mentionné distinctement, avec son étendue, sa destination, son lieu et sa durée, et
  l'article 3.5 le dit. Cela ne coûte rien et ferme la question.
- **Les formes d'exploitation non prévisibles (article L131-6).** L'accord ne les vise pas :
  une telle clause exigerait une participation aux profits, absurde dans une licence gratuite.
  Le coût est de ne pas couvrir ces formes-là, que personne ne sait nommer ; les formes connues,
  dont le logiciel en tant que service, sont énumérées.
- **La gratuité.** L'article L122-7 permet une concession à titre gratuit ; l'article 3.5 s'y
  réfère.
- **La licence de brevet.** Le droit européen exclut le programme d'ordinateur « en tant que
  tel » (article 52 de la convention sur le brevet européen), mais admet les inventions mises
  en œuvre par ordinateur qui produisent un effet technique. Un contributeur qui en détiendrait
  une pourrait, sans l'article 4, soumettre son code puis agir en contrefaçon contre le projet
  et ses utilisateurs. L'article coûte rien à qui n'a pas de brevet ; il reste.
- **Le droit moral hors logiciel.** L'article L121-7 ne vaut que pour le logiciel. Pour la
  spécification et la documentation, l'article 5.2 fonde les mêmes modalités sur le consentement
  donné en connaissance de cause à une œuvre révisée en continu, et sur la clause 2.b.1 de
  CC BY-SA 4.0, que tout contributeur à la spécification accepte déjà en publiant sous cette
  licence. L'intégrité reste protégée contre l'atteinte à l'honneur et à la réputation, qu'aucun
  consentement anticipé ne peut lever. Le droit de retrait (article L121-4) subsiste pour ces
  œuvres, sous la condition légale d'indemniser préalablement l'exploitant ; il n'avait pas à
  être écrit.
- **La force de l'article 6.2 et sa sanction.** Un engagement contractuel s'exécute en nature
  ou se résout en dommages et intérêts (articles 1217 et suivants du code civil). L'article 6.4
  stipule la sanction qui a du sens : après mise en demeure restée sans effet soixante jours,
  le contributeur retire, pour sa contribution, le droit de la distribuer autrement que sous
  une licence libre. Les licences libres déjà concédées aux tiers demeurent — l'AGPL et
  CC BY-SA sont irrévocables —, de sorte que la sanction retire exactement ce que l'accord
  donne, et rien à la communauté.
- **La confidentialité (article 1210 du code civil).** Un engagement sans terme serait
  perpétuel. L'article 11.1 cesse quand le mainteneur rend lui-même son identité publique, et
  au plus tard dix ans après la fin de l'accord. La sanction est celle du droit commun
  (article 11.3) ; une clause pénale ferait fuir les contributeurs pour un risque que la
  publicité inévitable de l'identité rend faible.
- **La signature (articles 1366, 1367 et 1375 du code civil).** Une signature électronique
  simple, ou un PDF signé et renvoyé, sont admis en preuve ; seule la signature qualifiée
  bénéficie d'une présomption de fiabilité, et celui qui se prévaut d'une signature simple doit,
  en cas de contestation, en établir la fiabilité. L'envoi depuis l'adresse déclarée, le message
  conservé au registre, l'invitation du compte GitHub et les commits qui en viennent forment
  cette preuve. L'accord est synallagmatique — le mainteneur s'oblige aux articles 6, 11 et
  13 — : il faut autant d'originaux que de parties, d'où la contresignature et la copie renvoyée
  (article 12.1). Aucun justificatif d'identité : l'« Apache Individual CLA » n'en demande pas,
  et il alourdirait le traitement de données pour une garantie que les déclarations de
  l'article 7 donnent déjà (article 12.5).
- **Les données personnelles.** La base est l'exécution du contrat (article 6.1.b du RGPD),
  puis l'intérêt légitime à conserver la preuve des droits (article 6.1.f). La conservation
  court cinq ans après la fin de l'exploitation, durée de la prescription des actions
  contractuelles (article 2224 du code civil). L'effacement est limité par l'article 17.3.e du
  RGPD tant que la preuve peut servir. L'article 13 nomme les destinataires — prestataires
  d'hébergement et de messagerie, conseils — et le droit de saisir la CNIL.
- **La juridiction.** Entre parties qui ne sont pas toutes commerçantes, une clause attributive
  de compétence territoriale est réputée non écrite (article 48 du code de procédure civile),
  et le contentieux du droit d'auteur relève de tribunaux judiciaires désignés par décret
  (article L331-1 du code de la propriété intellectuelle). L'article 14.3 retient les
  juridictions françaises et, là où la loi permet d'en convenir — notamment avec un contributeur
  établi hors de France —, celles du domicile du mainteneur, que l'exemplaire indique sans que
  le modèle public le dise.
- **Le code écrit avec un assistant d'intelligence artificielle.** Le droit d'auteur protège
  l'œuvre de l'esprit qui porte l'empreinte de son auteur. Ce qu'un assistant produit sans
  apport créatif humain n'est pas protégé ; ce que l'auteur a conçu, spécifié, choisi, relu et
  refondu l'est, à hauteur de cet apport, et l'ensemble l'est comme sélection et agencement.
  Pour la double licence, la conséquence est que la part non protégée n'est exclusive pour
  personne : la valeur d'une édition commerciale tient alors à la marque, au service, et aux
  parties protégées. L'accord n'a rien à en dire de plus que l'article 7.5.
- **Les en-têtes et l'œuvre pseudonyme.** Voir « Les décisions prises », point 1.
- **La marque « Waterfall ».** Le mot désigne une méthode de gestion de projet : pour un
  logiciel de ce domaine, il est descriptif, et un dépôt du seul mot risque le refus pour défaut
  de caractère distinctif (article L711-2 du code de la propriété intellectuelle, article 7.1.c
  du règlement sur la marque de l'Union européenne). Une marque semi-figurative — le logo et le
  mot — se dépose, avec une protection mince sur le mot seul ; l'offre commerciale gagnera à
  porter un nom distinctif, et la mention « le nom et le logo ne sont pas couverts par cette
  licence » reste la bonne pratique. Sous AGPL, c'est la marque et non la licence qui empêche un
  tiers d'héberger le logiciel inchangé sous le nom du projet.

## Pour l'adopter

1. Publier la traduction anglaise de `CLA.md`.
2. Mettre en place le circuit : la boîte `contact@waterfall-project.pro`, le modèle PDF de
   l'exemplaire, tiré de `CLA.md` avec son annexe, et le registre privé, tenu hors du dépôt.
3. Vérifier que les pull requests restent réservées aux collaborateurs du dépôt.
4. Fusionner. La section « Licence » de `CONTRIBUTING.md`, l'accord et les engagements prennent
   effet à la fusion.
