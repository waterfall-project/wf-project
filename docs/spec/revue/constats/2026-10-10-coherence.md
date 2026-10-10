---
revue_du: 2026-10-10
sur: waterfall-spec.md généré le 2026-10-10 après intégration de C-256 à C-258 (branche claude/busy-clarke-pdl7gu à 1329545, partie de main à e407fba, 211 exigences)
revue_par: Claude Code — cinq relecteurs par tranche du document, triés par un sixième
perimetre: document complet, revue de cohérence — contradictions entre passages, renvois, termes, exemples chiffrés, matrices — et propagation de C-256, C-257 et C-258
---

# Revue du 2026-10-10 — cohérence du document complet

## Suivi des revues précédentes

Les constats C-001 à C-258 ne sont pas recopiés. Aucun constat intégré n'est revenu à l'état d'avant
sa correction. Les trois décisions du 10 octobre (C-256 à C-258) ont été intégrées là où elles étaient
proposées ; quatre passages voisins sont restés en retard (C-262), et quatre cas nouveaux en découlent
(C-259 à C-261, C-273). Plusieurs intégrations plus anciennes ont laissé des phrases voisines en retard,
consignées soit ici quand elles changent ce qui se construit, soit dans les relevés non retenus.

## Le tri

Les cinq relecteurs ont remis 113 relevés, toutes citations vérifiées mot pour mot. Onze doublons
entre tranches ont été fusionnés. **Un seul critère a servi au tri : le relevé ferait-il construire ou
tester deux choses différentes à deux développeurs de bonne foi ?**

- **48 constats passent ce critère** : 27 majeurs et 21 mineurs, dont deux regroupent plusieurs
  points de même nature — les exemples chiffrés de Vérif faux ou incomplets (C-287), et les passages en
  retard sur les décisions du 10 octobre (C-262).
- **43 relevés ne le passent pas** : prose d'introduction ou Motif en retard sur une exigence qui
  tranche déjà, renvoi inexact, matrice de traçabilité FBS–PBS, vocabulaire. Ils sont listés en fin de
  fichier avec la raison de leur écart, et reportés : ils ne seront repris que si un lot s'y heurte.

Les passes complètes successives ne convergent plus (13, 78, 74, puis 113 relevés bruts) : passé ce
point, une relecture trouve des cas de plus en plus fins, et une partie de ce qu'elle trouve vient des
phrases ajoutées par les intégrations précédentes. Les constats qui ont le plus servi sont venus des lots
(#456, #577, #578, #579, #634). Cette passe est la dernière revue complète ; la suite viendra des lots.

## Où regarder d'abord

Les 27 majeurs se rangent en huit familles.

1. **La ligne de provision dans le reste du document (C-259, C-260, C-261).** Les imports, la
   suppression d'une tâche et la fusion la traitent comme une ligne saisie ; elle peut être portée par un
   jalon, sous lequel la survenance place des tâches ; et un risque ré-identifié n'a pas de règle pour sa
   catégorie ni sa tâche porteuse. C'est la suite naturelle de C-257 et C-258.
2. **États des tâches et sortie du projet (C-263, C-264).** Une feuille sans ligne ne peut jamais être
   terminée ; ce que devient la révision en cours à la sortie du projet n'est pas dit.
3. **L'aller-retour MS Project (C-265).** La liaison n'a ni lignée ni identifiant écrit par l'export,
   et MS Project ne porte qu'une liaison entre deux mêmes tâches ; point à confirmer sur le corpus de
   WF-QUA-0080.
4. **Les comptes (C-266, C-267, C-268, C-269).** La lecture quotidienne des comptes désactive ceux d'un
   raccordement retiré et défait l'anonymisation ; le rôle du compte de l'amorçage n'est pas dit ; le
   journal d'audit garde le nom d'un compte anonymisé que la base interdit d'effacer.
5. **Les révisions (C-270 à C-273).** Trois Vérif contredisent leur corps (correction de la référence,
   structures d'une révision nouvelle, comparaison après fusion) ; la suppression d'un sous-projet porté par
   la seule révision en cours n'a pas de règle et la base la refuse.
6. **Les calculs (C-274 à C-279).** Le calcul est refusé tant qu'une catégorie employée n'a pas de taux,
   ce qui bloque tout devis portant une ligne hors main-d'œuvre ; plan de charge et courbe en S répartissent
   différemment le reste d'une tâche en retard ; le reste à engager après un avenant dépend du passage lu ;
   une Vérif attend une dégradation de l'indice de coût qui ne se produit pas ; le portefeuille à une date
   passée a besoin de plus que les indicateurs conservés ; les courbes conservées au mois ne portent pas les
   marches au jour.
7. **La technique (C-280 à C-284).** La file de tâches est encore décrite sans la table qui fait foi ; la
   chaîne des métriques jusqu'à l'écran d'état a trois trous ; l'invalidation du cache oublie des écritures ;
   la copie externe des sauvegardes n'a pas de flux ; des exigences F0 reposent sur des F1.
8. **L'interface (C-285, C-286).** « Terminer » sur un projet en chiffrage est absent du menu selon une
   exigence, présenté indisponible selon une autre ; un collage partiellement invalide est refusé en bloc
   selon le corps, appliqué en partie selon la Vérif.

Trois propositions laissent un choix à l'auteur, rédigé pour chaque branche : C-278 (conserver des
agrégats ou relire les révisions), C-286 (collage tout ou rien, ou partiel) et C-284 (passer en F0 ou
retoucher la Vérif).

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-259 | majeur | §3.1.4 « Interactions avec les systèmes externes » — exigences… | Les imports, la suppression d'une tâche et la fusion traitent la ligne de provision comme une ligne ordinaire | à traiter |
| C-260 | majeur | §3.2.4 « Planning », paragraphe « Le jalon » ; §3.2.6, paragraphe… | La provision peut être portée par un jalon : la survenance lui donne des sous-tâches, et il ne peut plus être terminé | à traiter |
| C-261 | majeur | §3.4.5.6 — exigences WF-RIS-0010-A  et WF-RIS-0020-A ; §3.4.4.1.1,… | C-257 : un risque écarté qui redevient identifié n'a pas de règle pour la catégorie de sa provision | à traiter |
| C-262 | mineur | WF-RIS-0020 et §4.4.1 ; WF-DEV-0020 | Propagation des décisions du 10 octobre : quatre passages en retard sur C-256, C-257 et C-258 | à traiter |
| C-263 | majeur | §3.2.4 « Planning », paragraphe « L'avancement » ; annexe A,… | Une tâche feuille sans ligne ne peut jamais être terminée, et une tâche non démarrée mise à zéro l'est malgré la Vérif du Kanban | à traiter |
| C-264 | majeur | §3.3.2 « Cycle de vie d'un projet » — exigences WF-CYC-0060-A,… | Ce que devient la révision en cours à la sortie du projet n'est pas dit | à traiter |
| C-265 | majeur | §3.1.4 — exigences WF-INTF-0040-A, WF-INTF-0050-A, WF-INTF-0060-A… | La liaison n'a ni lignée ni identifiant écrit par l'export, et MS Project ne sait pas porter deux liaisons entre deux mêmes tâches | à traiter |
| C-266 | majeur | §3.4.2.1 « FBS-1.1 : Gestion des utilisateurs » — exigence… | Retirer un raccordement « ne désactive pas » ses comptes, mais la lecture du lendemain les désactive | à traiter |
| C-267 | majeur | §3.4.2.1 « FBS-1.1 : Gestion des utilisateurs » — exigences… | La lecture des comptes défait l'anonymisation, que WF-ADM-0060 dit irréversible | à traiter |
| C-268 | majeur | §4.5.2 « Installation initiale », texte et exigence WF-EXP-0020-A … | L'amorçage ne dit pas quel rôle porte le compte administrateur, et chaque lecture fait échouer un Vérif | à traiter |
| C-269 | majeur | §4.6.1 « Sécurité » — exigence WF-SEC-0030-A et texte « Un mot des… | Le journal d'audit garde le nom d'un compte anonymisé, et la base interdit de l'en effacer | à traiter |
| C-270 | majeur | §3.4.5.1 « FBS-4.1 : Gestion des révisions » — exigence WF-REV-0040-A | La Vérif de WF-REV-0040 refuse la correction que le corps et le Motif sont faits pour permettre | à traiter |
| C-271 | majeur | §3.4.5.1 — exigence WF-REV-0100-A  ; à rapprocher de WF-REV-0010-A… | « Une révision nouvellement créée comporte une structure principale et aucune autre » contredit la reprise des structures | à traiter |
| C-272 | majeur | §3.4.5.1 — exigence WF-REV-0080-A  ; à rapprocher de… | « aucun écart de montant réestimé » est faux pour un différentiel qui ajoute ou retire des lignes | à traiter |
| C-273 | majeur | §4.4.1 — exigences WF-DAT-0080-A  et WF-DAT-0090-A  ; à rapprocher… | La suppression d’un sous-projet que portent des lignes de la révision en cours n’a pas de règle, et la base la refuse | à traiter |
| C-274 | majeur | §3.4.5.4 « Chiffrage et devis » — exigence WF-DEV-0010-A  ; à… | Le calcul est refusé tant qu’une catégorie employée n’a pas de taux, or une catégorie hors main-d’œuvre ou de provision n’en porte jamais | à traiter |
| C-275 | majeur | §3.4.5.4.4 « Plan de charge du projet » — exigence WF-DEV-0070-A ;… | Une tâche non démarrée en retard : le plan de charge met son reste dans les mois écoulés, la courbe en S après la date de calcul | à traiter |
| C-276 | majeur | §3.4.5.5 « Estimation du reste à engager » — exigence… | Après un avenant qui change une ligne non démarrée et non réestimée, le reste à engager suit le différentiel ou reste à l’ancien montant selon le passage lu | à traiter |
| C-277 | majeur | §3.4.5.5.3 « Grille de reste à engager », texte d’introduction  ;… | La Vérif attend que l’indice de coût se dégrade à l’ajout d’une tâche, qui ne change ni la valeur acquise ni le coût réel | à traiter |
| C-278 | majeur | §4.4.2 « Historisation et immuabilité des révisions » — exigence… | Le portefeuille à une date passée a besoin de plus que les indicateurs conservés | à traiter |
| C-279 | majeur | §4.4.2 — exigence WF-DAT-0040-A ; §3.4.5.8.7 WF-IND-0100-A | Courbes conservées « au pas du mois », marches exigées au jour près | à traiter |
| C-280 | majeur | §4.2.1.5 « PBS-5 : Plateforme », PBS-5.3 ; §4.3.2 tableau 8, ligne… | Les tâches planifiées et les tâches demandées entrent en file sans être inscrites dans la table qui fait foi (C-241 non propagé) | à traiter |
| C-281 | majeur | §4.6.3 « Observabilité » — exigences WF-OBS-0010-A et… | Ce que Prometheus collecte, par où l'écran d'état le lit, et où paraît une alerte quand l'écran tombe : trois trous entre WF-OBS-0010/0030 et le tableau des flux | à traiter |
| C-282 | majeur | §4.4.5 « Cache » — exigence WF-DAT-0130-A  ; à rapprocher de… | L'invalidation du cache n'énumère pas toutes les écritures dont dépend un indicateur au jour courant | à traiter |
| C-283 | majeur | §4.3.1 « Diagramme de déploiement », texte et figure 18 ; §4.3.2… | La copie des sauvegardes hors de la plateforme n'a pas de flux, et le §4.3.1 l'exclut | à traiter |
| C-284 | majeur | §4.4.6 WF-DAT-0140-A  et §4.5.3 WF-EXP-0030-A  ; §3.4.2.1… | Des exigences F0 reposent sur des exigences F1 | à traiter |
| C-285 | majeur | §3.6 — exigence WF-IHM-0090-A  ; §3.3.2 WF-CYC-0060-A | La sortie « Terminer » d'un projet en chiffrage : absente du menu selon WF-CYC-0060, présentée indisponible selon WF-IHM-0090 | à traiter |
| C-286 | majeur | §3.6 — exigence WF-IHM-0050-A  ; à rapprocher de WF-INTF-0080-A | Un collage partiellement invalide : grille inchangée selon le corps, lignes valides écrites selon la Vérif | à traiter |
| C-287 | mineur | Vérif de WF-REF-0160, WF-PTF-0010, WF-PTF-0050, WF-REV-0010,… | Vérif dont l'exemple est faux ou suppose une hypothèse non dite | à traiter |
| C-288 | mineur | §3.1.4 — exigence WF-INTF-0120-A ; annexe B | Le sous-projet d'une ligne existante : l'onglet le donne, la liste des grandeurs mises à jour ne le comprend pas | à traiter |
| C-289 | mineur | §3.1.4 — exigence WF-INTF-0050-A ; à rapprocher de WF-INTF-0110-A,… | Résidu de C-183 : l'export MS Project ne dit pas quelle révision ni quelle structure il écrit | à traiter |
| C-290 | mineur | §3.1.5 — exigence WF-INTF-0180-A ; §4.1.3 — exigence WF-ARC-0110-A | L'onglet « Hors sous-projet » et les valeurs fixées d'un fichier exporté : traduits selon WF-ARC-0110, fixes selon l'esprit de WF-INTF-0180 | à traiter |
| C-291 | mineur | §3.4.4, exigence WF-REF-0010-A ; §3.3.1, WF-CYC-0120-A | C-257 a retiré la seule règle qui tenait compte de l'état de la nature : une catégorie active d'une nature désactivée compte-t-elle ? | à traiter |
| C-292 | mineur | §3.4.4.4 « FBS-3.4 : Paramètres d’indicateurs » — exigence… | Une valeur égale à un seuil ou à une borne n'a pas de zone ni de niveau | à traiter |
| C-293 | mineur | §3.4.2.2 « FBS-1.2 : Gestion des rôles d’habilitation », texte… | La troisième exception renvoie à WF-PRJ-0070 au lieu de WF-PRJ-0060, et WF-ADM-0110 ne la connaît pas | à traiter |
| C-294 | mineur | §4.4.1, puce « Suppression » ; exigence WF-DAT-0080-A | Le régime « marqué supprimé » vise un livrable et une chronologie que rien ne référence | à traiter |
| C-295 | mineur | §3.4.5.5 — exigence WF-RAE-0010-A, corps ; à rapprocher de… | « Quel que soit l’état de sa tâche » contredit « de zéro si la tâche est terminée » | à traiter |
| C-296 | mineur | §3.4.5.4.2 « Grille de devis » — exigence WF-DEV-0050-A  ; à… | « Montant réestimé » désigne ici la valeur avant inflation, que WF-DEV-0020 appelle autrement | à traiter |
| C-297 | mineur | §3.4.5.4.3 « Gestion des coûts » — exigence WF-DEV-0030-A, corps ;… | Le montant se calcule au taux « de sa catégorie pour l’année de référence », non au taux que la révision conserve | à traiter |
| C-298 | mineur | §3.4.5.4 — exigence WF-DEV-0020-A, corps ; à rapprocher de §3.2.5… | Qu’un rôle détermine la catégorie d’une ligne de main-d’œuvre n’est dit par aucune exigence | à traiter |
| C-299 | mineur | §3.4.5.4 — exigence WF-DEV-0020-A ; à rapprocher de WF-RIS-0010-A,… | Le sous-projet d’une ligne de provision n’est dit nulle part | à traiter |
| C-300 | mineur | §3.4.5.8 — exigence WF-IND-0020-A ; à rapprocher de… | Le sous-projet d’une ligne peut changer après la référence : budget, valeur planifiée et valeur acquise d’un sous-projet ne disent pas dans quelle révision ils le lisent | à traiter |
| C-301 | mineur | §3.4.5.6.2 — exigence WF-RIS-0050-A  ; à rapprocher de… | Après un avenant, la réserve perd la part des risques déjà survenus, dont le coût reste dans la couverture | à traiter |
| C-302 | mineur | §3.4.5.5.2 « Kanban – Démarrage des tâches » — exigence… | « Passé ce délai » renvoie à un délai que WF-IHM-0110 ne fixe pas ; le jalon terminé par le Kanban sans la restriction de WF-PLA-0050 | à traiter |
| C-303 | mineur | §3.6 — exigence WF-IHM-0020-A ; à rapprocher de WF-REV-0020-A et… | Le nom de version d'une révision en cours, qu'elle n'a pas | à traiter |
| C-304 | mineur | §3.6 — exigence WF-IHM-0090-A  ; à rapprocher de WF-ADM-0110-A et… | WF-IHM-0090 range toute impossibilité en « état » ou « habilitation » : la qualité de contributeur n'est ni l'un ni l'autre | à traiter |
| C-305 | mineur | §4.5.2 « Installation initiale », texte et exigence WF-EXP-0020-A | Le calendrier amorcé « porte des heures travaillées » sans dire lesquelles | à traiter |
| C-306 | mineur | §4.1.3 — exigence WF-ARC-0110-A  ; §3.1.5 WF-INTF-0160-A | La langue des courriels d'authentification : « celle du compte », que le motif place dans le fournisseur d'identité et WF-INTF-0160 dans Waterfall | à traiter |

---

## C-259 — Les imports, la suppression d'une tâche et la fusion traitent la ligne de provision comme une ligne ordinaire

- **gravité** : majeur
- **emplacement** : §3.1.4 « Interactions avec les systèmes externes » — exigences `WF-INTF-0100-A`, `WF-INTF-0120-A`, `WF-INTF-0040-A` ; §3.2.6 « Risques » ; à rapprocher de `WF-PLA-0070-A`, `WF-REV-0050-A`, `WF-RIS-0010-A`, `WF-DEV-0020-A`
- **citation** : « une ligne existante absente du fichier est supprimée, sauf si sa tâche est démarrée ou terminée, auquel cas elle est conservée et signalée au compte rendu. » (WF-INTF-0100) ; « une ligne sans identifiant, ou dont la lignée n’existe pas dans la révision en cours, devient une ligne nouvelle » (WF-INTF-0100) ; « une tâche existante absente du fichier est supprimée selon WF-PLA-0070 » (WF-INTF-0040) ; « La suppression d’une tâche supprime ses subordonnées, les lignes de devis qu’elles portent, et les liaisons qui s’y rattachent. » (WF-PLA-0070) ; « Une ligne dont la catégorie relève d’une nature de type provision pour risques n’est créée que par la déclaration d’un risque (WF-RIS-0010) » (WF-DEV-0020)

**Constat.** C-257 et C-258 ont fait de la ligne de provision une ligne à part : créée par le système à la
déclaration du risque, portant la catégorie que le risque désigne et un montant calculé, présente « tant
qu'il est identifié » (WF-RIS-0010, §3.2.6). Quatre chemins l'ignorent encore et la traitent comme une ligne
saisie :

1. **Import du devis (FLX-03).** Rien n'exclut les lignes de provision du devis exporté (WF-INTF-0110), qui
   écrit les lignes de la structure. Retravaillé hors de Waterfall, un fichier d'où l'utilisateur a retiré une ligne
   de provision la fait supprimer (« une ligne existante absente du fichier est supprimée ») alors que son
   risque reste identifié ; un fichier qui contient une ligne d'une catégorie de provision sans identifiant
   en crée une « nouvelle », c'est-à-dire une ligne de provision saisie, que WF-DEV-0020 interdit ; une
   ligne de provision du fichier qui porte sa lignée « met à jour — quantité, charge ou débours… » des
   grandeurs qu'elle n'a pas.
2. **Import du reste à engager (FLX-05).** Même chose pour la création (« une ligne sans identifiant crée
   une ligne non anticipée ») et pour la mise à jour des « grandeurs réestimées » d'une ligne qui n'en a pas.
3. **Suppression de la tâche porteuse**, à la main (WF-PLA-0070), par l'import d'un planning qui ne la
   contient plus (WF-INTF-0040), ou par la fusion d'un différentiel qui la retire (WF-REV-0050, « les tâches
   devenues inutiles en sont retirées ») : la ligne de provision part avec elle, et le risque identifié n'a
   plus de provision. Le repli de WF-RIS-0010 (« la première tâche de premier niveau ») ne joue qu'à la
   déclaration.

Le développeur de l'import ou de la suppression n'a aucune règle : supprimer la provision fausse le devis,
le reste à engager et la couverture des risques (WF-RIS-0050) sans que rien ne le signale.

**Proposition.**

WF-INTF-0100, corps, ajouter à la fin : « Les lignes de provision des risques (WF-RIS-0010) figurent à
l’export pour information et ne sont jamais modifiées par l’import : une ligne du fichier qui porte la
lignée d’une ligne de provision est ignorée, une ligne sans identifiant dont la catégorie relève d’une
nature de type provision pour risques est rejetée (WF-DEV-0020), et une ligne de provision absente du
fichier est conservée ; le compte rendu signale les unes et les autres. » Vérif, ajouter : « Un fichier
d’où une ligne de provision a été retirée laisse cette ligne en place ; une ligne de catégorie de provision
sans identifiant est rejetée au compte rendu. »

WF-INTF-0120, corps, ajouter : « Les lignes de provision des risques ne sont ni mises à jour ni créées par
l’import, selon la même règle que WF-INTF-0100. »

WF-RIS-0010, corps, après « et peut être déplacée sur une autre ; » ajouter : « lorsque la tâche qui la porte
est supprimée — par saisie (WF-PLA-0070), par l’import d’un planning (WF-INTF-0040) ou par la fusion d’un
différentiel (WF-REV-0050) —, la ligne de provision passe sur la tâche parente de celle-ci ou, pour une
tâche de premier niveau, sur la première tâche de premier niveau restante, et la confirmation ou le compte
rendu le signale ; la suppression de la dernière tâche d’une structure principale qui porte une ligne de
provision est refusée en nommant le risque. » Vérif, ajouter : « La suppression de la tâche qui porte une
provision de 40 laisse le devis inchangé, la provision étant passée sur la tâche parente. »

WF-PLA-0070, corps, ajouter : « Les lignes de provision qu’elles portent ne sont pas supprimées : elles
passent sur une autre tâche selon WF-RIS-0010. »

*Relevé aussi par la relecture de la tranche D (relevé D-06), fusionné ici.*

**Statut.** à traiter


---

## C-260 — La provision peut être portée par un jalon : la survenance lui donne des sous-tâches, et il ne peut plus être terminé

- **gravité** : majeur
- **emplacement** : §3.2.4 « Planning », paragraphe « Le jalon » ; §3.2.6, paragraphe « Nature de la provision » ; exigences `WF-RIS-0010-A`, `WF-RIS-0060-A`, `WF-PLA-0050-A`
- **citation** : « Il ne porte pas de sous-tâches, mais il peut porter des lignes de devis : c’est ainsi que se chiffrent un acompte de sous-traitance ou une réception de fourniture. » (§3.2.4) ; « à défaut de désignation, elle est portée par la première tâche de premier niveau de la structure » (WF-RIS-0010) ; « Les tâches de premier niveau du devis propre sont placées, dans leur ordre, en dernière position sous la tâche qui portait la ligne de provision » (WF-RIS-0060) ; « par le Kanban (WF-RAE-0030) s’il ne porte aucune ligne, par la saisie d’un reste à engager nul sur toutes ses lignes sinon » (WF-PLA-0050)

**Constat.** Rien n'empêche la tâche qui porte la ligne de provision d'être un jalon : l'utilisateur en
désigne une quelconque, et le repli retient « la première tâche de premier niveau », qui est souvent le
jalon de lancement d'un planning. Le §3.2.6 parle bien de « la phase que le risque menace », mais aucune
exigence ne le dit. Deux contradictions en découlent :

1. À la survenance, WF-RIS-0060 place les tâches du devis propre **sous** la tâche porteuse. Sous un jalon,
   c'est ce que le §3.2.4, le glossaire et WF-PLA-0050 interdisent (« Une tâche feuille de durée nulle ne
   peut recevoir de sous-tâche »). Le développeur doit choisir entre refuser la survenance, transformer le
   jalon en récapitulative ou placer les tâches ailleurs.
2. Un jalon qui ne porte que la ligne de provision ne peut plus être terminé : le Kanban le refuse parce
   qu'il « porte une ligne », et la saisie d'un reste à engager nul « sur toutes ses lignes » est impossible
   sur une ligne de provision, dont le montant n'est pas saisi. WF-RIS-0010 dit pourtant que la ligne de
   provision « n'entre pas dans l'état de la tâche qui la porte », mais seulement pour la récapitulative
   (WF-PLA-0040) ; WF-PLA-0050 n'a pas suivi.

**Proposition.** WF-RIS-0060, corps, après la deuxième phrase, ajouter : « Lorsque la tâche qui portait la
ligne de provision est un jalon, ces tâches sont placées, dans leur ordre, immédiatement après lui, sous sa
tâche parente ou au premier niveau. » Vérif, ajouter : « La survenance d’un risque dont la provision était
portée par un jalon place ses tâches après ce jalon, qui reste un jalon sans sous-tâche. »

WF-PLA-0050, corps, remplacer la dernière phrase par : « Son état passe directement de non démarré à
terminé : par le Kanban (WF-RAE-0030) s’il ne porte aucune ligne hors lignes de provision (WF-RIS-0010), par
la saisie d’un reste à engager nul sur toutes ses lignes hors provision sinon ; le Kanban renvoie alors à
cette saisie. » Vérif, ajouter : « Un jalon qui ne porte qu’une ligne de provision est terminé depuis le
Kanban. »

*Relevé aussi par la relecture de la tranche D (relevé D-05), fusionné ici.*

**Statut.** à traiter


---

## C-261 — C-257 : un risque écarté qui redevient identifié n'a pas de règle pour la catégorie de sa provision

- **gravité** : majeur
- **emplacement** : §3.4.5.6 — exigences `WF-RIS-0010-A` (corps et Vérif) et `WF-RIS-0020-A` ; §3.4.4.1.1, `WF-REF-0030-A` (Vérif)
- **citation** : « La ligne de provision porte la catégorie que le risque désigne à sa déclaration parmi les catégories actives de type provision pour risques (WF-REF-0030) » et « Cette catégorie peut être changée tant que le risque est identifié. » (WF-RIS-0010) ; « Un risque identifié peut être écarté, et un risque écarté peut redevenir identifié. » (WF-RIS-0020) ; « La désactivation de la dernière catégorie active de type provision pour risques est acceptée » (WF-REF-0030, Vérif)

**Constat.** La ligne de provision n'existe que « tant qu’il est identifié » (WF-RIS-0010) :
écarter un risque la retire, et le rendre de nouveau identifié la recrée. C-257 rattache la
catégorie à la déclaration et ne conditionne que la déclaration à l'existence d'une catégorie
active. Avant C-257, une catégorie de provision active existait toujours (WF-REF-0010 et
WF-REF-0030, issus de C-192), et la question ne se posait pas. Désormais, deux cas restent sans
règle :
- un risque écarté dont la catégorie a été désactivée depuis redevient identifié ;
- un risque écarté redevient identifié alors qu'aucune catégorie de ce type n'est active.

Trois réponses sont possibles : la ligne reprend la catégorie désactivée, que WF-REF-0010 ne propose
plus ; une catégorie est demandée ; la transition est refusée. Le Vérif de WF-REF-0030 énumère les
refus qui suivent la désactivation (création d'un projet, déclaration d'un risque) mais pas
celui-là. Le changement de catégorie « tant que le risque est identifié » ne dit pas non plus vers
quoi. L'abandon d'une révision n'est pas en cause : il restaure l'évaluation marquée, ligne
comprise (WF-RIS-0020).

**Proposition.** WF-RIS-0010, corps, remplacer « Cette catégorie peut être changée tant que le
risque est identifié. La déclaration d’un risque est refusée, en nommant la condition manquante,
lorsqu’aucune catégorie de ce type n’est active. » par :

« Tant que le risque est identifié, cette catégorie peut être changée pour une autre catégorie
active de ce type. Lorsqu’un risque écarté redevient identifié, sa ligne de provision reprend la
catégorie qu’il désignait si elle est encore active. Sinon, la catégorie est demandée, comme à la
déclaration. La déclaration d’un risque, comme le retour d’un risque écarté à l’état identifié, est
refusée, en nommant la condition manquante, lorsqu’aucune catégorie de ce type n’est active. »

WF-RIS-0010, Vérif, ajouter : « Un risque écarté dont la catégorie a été désactivée redevient
identifié avec la catégorie active choisie. Sans catégorie active de ce type, son retour à l’état
identifié est refusé et nomme la condition manquante. »

WF-REF-0030, Vérif : « … ; la création d’un projet (WF-CYC-0120), la déclaration d’un risque et le
retour d’un risque écarté à l’état identifié (WF-RIS-0010) sont alors refusés. »

*Relevé aussi par la relecture de la tranche D (relevé D-23), fusionné ici.*

**Statut.** à traiter


---

## C-262 — Propagation des décisions du 10 octobre : quatre passages en retard sur C-256, C-257 et C-258

- **gravité** : mineur
- **emplacement** : §4.4.1 « Modèle de données et conventions », puce « Suppression » ; §3.4.5.4 « FBS-4.4 : Chiffrage et devis » — exigence `WF-DEV-0020-A` (Vérif) ; §3.4.4.1.1 « FBS-3.1.1 : Nature et catégories de coûts » — exigence `WF-REF-0030-A` (Vérif) ; §3.4.3.4 « FBS-2.4 : Structure des coûts du portefeuille » — exigence `WF-PTF-0080-A` (Vérif)
- **citations** : une par point, ci-dessous

**Constat.** Les trois décisions du 10 octobre ont été intégrées là où elles étaient proposées ; quatre passages voisins disent encore l'état d'avant, et chacun se lit de deux façons.

**Point 1 — « un risque qu’une révision marquée cite s’écarte » se lit comme une suppression convertie en écart.** Citation : « et un risque qu’une révision marquée cite s’écarte (WF-RIS-0020) » (§4.4.1) ; « Un risque qu’aucune révision marquée ne cite encore peut être supprimé ; au-delà, il s’écarte. » (WF-RIS-0020)

WF-DAT-0080 dit que la suppression d’un risque cité par une révision marquée « est
refusée, en nommant la raison », et la Vérif de WF-RIS-0020 le confirme. La prose du §4.4.1 et le corps
de WF-RIS-0020 disent, eux, qu’au-delà le risque « s’écarte » : on peut le comprendre comme un conseil
(on l’écarte au lieu de le supprimer) ou comme une conversion (la commande de suppression passe le risque
à l’état écarté). Les deux produits diffèrent, et la seconde lecture contredit WF-DAT-0080. La phrase
est en outre fausse pour un risque survenu, cité par une révision marquée et qui ne peut plus être écarté
(« Toute transition depuis l’état survenu est refusée »). La puce du §4.4.1 énonce enfin la règle du
sous-projet par ce qui ne se produit pas (« n’est jamais marqué supprimé ») et non par ce qui se produit :
le refus.

*Proposition.* §4.4.1, puce « Suppression », seconde phrase :

> Un sous-projet ou un risque, lui, n’est jamais marqué supprimé : sa suppression est refusée, en nommant
> la raison, dès qu’une révision marquée le cite ou, pour un sous-projet, dès que des coûts lui sont
> imputés (WF-DAT-0080, WF-PRJ-0050, WF-RIS-0020) ; un risque identifié qu’on ne veut plus suivre
> s’écarte.

WF-RIS-0020, corps : « Un risque qu’aucune révision marquée ne cite encore peut être supprimé ; au-delà,
sa suppression est refusée, et un risque identifié qu’on cesse de suivre s’écarte. »

*Relevé aussi par les relectures des tranches A et D (relevés A-10, D-20), fusionné ici.*

**Point 2 — C-258 : « ligne de nature provision » a échappé au renommage.** Citation : « La création à la main d’une ligne de nature provision est refusée. »

C-258 renomme le type « provision pour risques » partout où il est nommé. Le corps de
WF-DEV-0020 a suivi (« une nature de type provision pour risques »), mais pas son Vérif. Or c'est
un type, non une nature, qui est en cause. Une provision pour aléas est justement une nature
hors main-d'œuvre qu'on peut appeler « Provision » : sa création à la main doit, elle, aboutir.

*Proposition.* « La création à la main d’une ligne dont la catégorie relève d’une nature de type
provision pour risques est refusée. »

*Relevé aussi par les relectures des tranches D et A (relevés D-21, A-06), fusionné ici.*

**Point 3 — « La déclaration d'un risque aboutit sans autre saisie du référentiel » contredit WF-CYC-0120 et WF-EXP-0020.** Citation : « Sur une installation neuve, la nature de type provision pour risques et sa catégorie existent, et la déclaration d’un risque aboutit sans autre saisie du référentiel. » (WF-REF-0030) ; « La création d’un projet est refusée et nomme les prérequis manquants, jusqu’à ce qu’une catégorie de coût de main-d’œuvre et un rôle de ressource aient été saisis. » (WF-EXP-0020)

Déclarer un risque suppose un projet et une tâche. Or, sur une installation neuve,
créer un projet exige d'avoir saisi au moins une catégorie de main-d'œuvre et un rôle (WF-CYC-0120,
WF-EXP-0020). Pris au mot, ce Vérif ne s'exécute pas. La phrase vient de C-192, où elle voulait dire
« sans saisir de catégorie de provision ». C-257 a réécrit ce Vérif sans la reprendre. Or c'est
précisément ce que la phrase voulait dire qu'il faut maintenant écrire, puisque la catégorie de
provision est devenue un prérequis de création.

*Proposition.* Remplacer la phrase citée par : « Sur une installation neuve, la nature de type
provision pour risques et sa catégorie existent. Une fois saisis la catégorie de main-d’œuvre et le
rôle de ressource qu’exige WF-CYC-0120, un projet se crée, et la déclaration d’un risque y aboutit
sans qu’aucune catégorie de provision ait été saisie. »

*Relevé aussi par les relectures des tranches D et E (relevés D-22, E-23), fusionné ici.*

**Point 4 — « Une provision de 50 », « la part des provisions » : ni C-257 (plusieurs natures) ni C-258 (provision pour aléas) n'y sont passés.** Citation : « Une offre incluse dont le devis porte une provision de 50 n’ajoute rien à la part des provisions du budget agrégé, et 50 pondérés à celle du reste à engager agrégé. »

Le corps ventile par nature de coût. Depuis C-257, les lignes de provision d'un même
devis peuvent relever de plusieurs natures de type provision pour risques, puisque chaque risque
désigne sa catégorie. « La part des provisions » ne désigne donc aucune nature. Depuis C-258, une
« provision » peut aussi être une ligne hors main-d'œuvre, par exemple une provision pour aléas,
et une telle ligne entre au budget. Pour elle, le résultat attendu est l'inverse de celui du Vérif :
20 au budget agrégé pour une offre à 40 %.

*Proposition.* « Une offre incluse, à 40 %, dont le devis porte une ligne de provision pour
risques de 50 n’ajoute rien à la nature de cette ligne dans le budget agrégé, et ajoute 20 à cette
nature dans le reste à engager agrégé. Une ligne de 50 d’une nature hors main-d’œuvre, une
provision pour aléas par exemple, ajoute 20 à sa nature dans l’un et dans l’autre. »

**Proposition.** Les rédactions de chaque point ci-dessus.

**Statut.** à traiter

---

## C-263 — Une tâche feuille sans ligne ne peut jamais être terminée, et une tâche non démarrée mise à zéro l'est malgré la Vérif du Kanban

- **gravité** : majeur
- **emplacement** : §3.2.4 « Planning », paragraphe « L'avancement » ; annexe A, entrée « État d'avancement » ; exigences `WF-RAE-0030-A` (Vérif), `WF-RAE-0040-A` (corps), `WF-PLA-0050-A` ; à rapprocher de `WF-PRJ-0030-A`
- **citation** : « Le passage à l’état démarré est commandé par l’utilisateur ; l’état terminé résulte de la saisie d’un reste à engager nul. » (§3.2.4) ; « Le passage direct de non démarrée à terminée n’est possible que pour un jalon » (WF-RAE-0030, Vérif) ; « La saisie d’un reste à engager nul pour toutes les lignes d’une tâche la fait passer à l’état terminé » (WF-RAE-0040) ; « l’utilisateur peut y faire apparaître les tâches non démarrées pour les réestimer » (WF-RAE-0040)

**Constat.** Le modèle (§3.2.4) et le glossaire font naître l'état terminé d'une seule chose, « la saisie
d'un reste à engager nul ». Les exigences ajoutent le Kanban pour le jalon sans ligne (WF-PLA-0050,
WF-RAE-0030), et la récapitulative tire son état de ses subordonnées. Deux cas restent sans règle, ou avec
deux règles :

1. **Une tâche feuille qui n'est pas un jalon et ne porte aucune ligne** se démarre au Kanban, mais ne se
   termine par aucun geste : la grille de reste à engager n'a aucune cellule pour elle, et le Kanban ne
   termine que les jalons. C'est le cas ordinaire des feuilles du squelette (WF-PRJ-0030 : « une tâche
   feuille par livrable »), et de toute tâche de pure planification. Elle reste démarrée, sa récapitulative
   aussi (WF-PLA-0040), et ni l'avancement physique de la phase ni la valeur acquise de ses lignes propres
   n'aboutissent.
2. **Une tâche non démarrée** que l'utilisateur fait apparaître dans la grille et dont il met toutes les
   lignes à zéro passe à terminé selon le corps de WF-RAE-0040, alors que la Vérif de WF-RAE-0030 réserve ce
   passage direct au jalon. Le second cas a une conséquence de fond : la valeur acquise d'un travail jamais
   commencé serait acquise (WF-IND-0030).

**Proposition.** WF-RAE-0030, corps, après « et un jalon directement à l’état terminé, en saisissant la date
de l’événement (WF-PLA-0130) » ajouter : « , et une tâche démarrée qui ne porte aucune ligne hors lignes de
provision à l’état terminé, à une date saisie ». Vérif, ajouter : « Une tâche feuille démarrée sans ligne de
devis est terminée depuis le Kanban. »

WF-RAE-0040, corps, après « La saisie d’un reste à engager nul pour toutes les lignes d’une tâche la fait
passer à l’état terminé » ajouter : « si elle est démarrée ; sur une tâche non démarrée, cette saisie est
refusée, et la tâche se démarre d’abord depuis le Kanban (WF-RAE-0030) ». (Si l'auteur veut au contraire
permettre ce passage direct, le dire dans la Vérif de WF-RAE-0030 : « …n’est possible que pour un jalon,
ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée (WF-RAE-0040) ».)

§3.2.4, remplacer la phrase citée par : « Le passage à l’état démarré est commandé par l’utilisateur ;
l’état terminé résulte de la saisie d’un reste à engager nul sur les lignes de la tâche ou, pour un jalon ou
une tâche sans ligne, d’un geste du Kanban (WF-RAE-0030). » Glossaire, entrée « État d’avancement », même
correction.

**Statut.** à traiter


---

## C-264 — Ce que devient la révision en cours à la sortie du projet n'est pas dit

- **gravité** : majeur
- **emplacement** : §3.3.2 « Cycle de vie d'un projet » — exigences `WF-CYC-0060-A`, `WF-CYC-0090-A`, `WF-CYC-0100-A` ; à rapprocher de `WF-IND-0010-A`, `WF-PTF-0010-A`, annexe A « Révision »
- **citation** : « Une sortie manuelle n’est appliquée qu’après une confirmation qui énonce son caractère définitif et ce qu’elle rend non modifiable. » (WF-CYC-0090) ; « Dans un état terminal, le projet et toutes ses données (plannings, devis, restes à engager, coûts réels) sont en lecture seule » (WF-CYC-0100) ; « Elle est d'abord en cours d'élaboration, puis figée lorsqu'un utilisateur habilité la marque. » (annexe A, « Révision »)

**Constat.** Un projet sort du cycle de vie (Terminé, Perdu, Abandonné) à n'importe quel moment, y compris
quand il porte une révision en cours d'élaboration : la dernière revue n'a pas été marquée, ou une offre
perdue avait un brouillon. Aucune exigence ne dit ce que devient cette révision. Elle n'est plus ni marquable
ni abandonnable (WF-CYC-0100), et elle reste pourtant « en cours », ce que le glossaire réserve à une
révision modifiable. Trois lectures sont possibles — elle est figée telle quelle, elle est marquée par la
sortie, elle est abandonnée — et elles ne donnent pas les mêmes indicateurs : selon WF-IND-0010, ceux d'un
projet se calculent « au jour courant » sur la révision en cours s'il en a une, sur la dernière révision
marquée sinon ; et le portefeuille, qui retient les projets terminés d'une période (WF-PTF-0010), les lit
au jour courant par cette révision, à une date passée par la dernière révision marquée. Un projet terminé
avec une revue non marquée n'aurait donc pas les mêmes valeurs selon la date de calcul choisie.

**Proposition.** WF-CYC-0090, corps, ajouter : « Lorsque le projet porte une révision en cours, la
confirmation demande de la marquer, avec un nom de version (WF-REV-0020), ou de l’abandonner (WF-REV-0010) ;
la sortie n’est appliquée qu’avec ce choix, dans la même opération. Un projet terminal ne porte donc aucune
révision en cours. » Vérif, ajouter : « La sortie d’un projet qui porte une révision en cours demande de la
marquer ou de l’abandonner ; après la sortie, le projet n’a plus de révision en cours, et ses indicateurs se
lisent dans sa dernière révision marquée (WF-IND-0010). »

**Statut.** à traiter


---

## C-265 — La liaison n'a ni lignée ni identifiant écrit par l'export, et MS Project ne sait pas porter deux liaisons entre deux mêmes tâches

- **gravité** : majeur
- **emplacement** : §3.1.4 — exigences `WF-INTF-0040-A`, `WF-INTF-0050-A`, `WF-INTF-0060-A` ; §3.2.4, paragraphe « Les liaisons » ; à rapprocher de `WF-PLA-0030-A` et `WF-DAT-0030-A`
- **citation** : « une tâche ou une liaison du fichier qui porte l’identifiant que l’export de Waterfall y a écrit (WF-INTF-0050) met à jour l’objet existant sans toucher à sa lignée » (WF-INTF-0040) ; « Chaque tâche y porte son identifiant de lignée (WF-DAT-0030) dans le champ d’identifiant unique de MS Project » (WF-INTF-0050) ; « Chaque structure de coûts, tâche et ligne de devis porte deux identifiants » (WF-DAT-0030) ; « Deux tâches peuvent être reliées par plusieurs liaisons, et c’est pourquoi la liaison est un objet et non une simple flèche entre deux tâches. » (§3.2.4)

**Constat.** Deux incompatibilités sur la liaison, toutes deux dans la tranche :

1. WF-INTF-0040 rapproche « une tâche ou une liaison » par l'identifiant que l'export a écrit, « sans toucher
   à sa lignée ». Mais WF-INTF-0050 n'écrit d'identifiant que pour les tâches, et WF-DAT-0030 ne donne de
   lignée qu'aux structures, tâches et lignes de devis : une liaison n'a ni l'un ni l'autre. Le format XML
   de MS Project ne donne d'ailleurs aucun identifiant à une liaison : il ne porte, sous la tâche successeur,
   que l'identifiant du prédécesseur, le type et le décalage. Le développeur de l'import ne sait pas comment
   reconnaître une liaison existante, ni donc s'il doit la mettre à jour, la recréer ou la supprimer.
2. Le §3.2.4 et WF-PLA-0030 admettent « plusieurs liaisons » entre deux mêmes tâches, et c'est la raison
   donnée pour faire de la liaison un objet. MS Project ne relie deux tâches données que par une seule
   liaison (un prédécesseur ne figure qu'une fois parmi ceux d'une tâche — point à confirmer sur le corpus
   de WF-QUA-0080). Un planning qui use de cette liberté ne peut donc pas satisfaire WF-INTF-0060, qui
   promet que l'aller-retour « restitue les mêmes tâches, durées, liaisons et dates », ni la Vérif de
   WF-PLA-0030 (« importés, saisis et exportés sans perte »), alors que le Motif de WF-PLA-0030 fonde les
   liaisons sur la fidélité à MS Project.

**Proposition.** WF-INTF-0040, corps, remplacer la phrase citée par : « une tâche du fichier qui porte
l’identifiant que l’export de Waterfall y a écrit (WF-INTF-0050) met à jour la tâche existante sans toucher
à sa lignée, à ses lignes de devis, à son état ni à son rattachement au lotissement (WF-PLA-0170) ; les
liaisons, qui n’ont pas d’identifiant propre, sont rapprochées par leurs deux tâches : celles du fichier
remplacent celles de la structure, et le compte rendu présente les liaisons ajoutées, modifiées et
supprimées. »

WF-PLA-0030, corps, remplacer « Deux tâches peuvent être reliées par plusieurs liaisons. » par « Deux tâches
ne sont reliées que par une liaison au plus, comme dans MS Project ; une seconde liaison entre les mêmes
tâches est refusée. » §3.2.4, remplacer la phrase citée par : « Elle porte son type et son décalage, et
c’est pourquoi la liaison est un objet et non une simple flèche entre deux tâches. » (Si l'auteur tient aux
liaisons multiples, dire dans WF-INTF-0050 que l'export n'en écrit qu'une par paire de tâches et le signale,
et le réserver dans WF-INTF-0060.)

**Statut.** à traiter


---

## C-266 — Retirer un raccordement « ne désactive pas » ses comptes, mais la lecture du lendemain les désactive

- **gravité** : majeur
- **emplacement** : §3.4.2.1 « FBS-1.1 : Gestion des utilisateurs » — exigence `WF-ADM-0180-A` (corps et Vérif) ; exigence `WF-ADM-0070-A`
- **citation** : « La désactivation d’un raccordement ne supprime ni ne désactive les comptes qui en viennent. » (WF-ADM-0180) ; « ne peuvent plus se connecter tant qu’aucun fournisseur ne les reconnaît » (WF-ADM-0180, Vérif) ; « et désactive les comptes que le fournisseur ne connaît plus » (WF-ADM-0070)

**Constat.** On retire l'annuaire, ou le relais vers un fournisseur externe, dans la console du
fournisseur d'identité. À partir de là, le fournisseur ne connaît plus les comptes qui en venaient.
La lecture de WF-ADM-0070 tourne chaque jour par défaut, sans intervention, et désactive alors
tous ces comptes. Pour un annuaire retiré, chaque personne est en effet « retirée de l'annuaire »,
au sens du Vérif de WF-ADM-0070. WF-ADM-0180 dit pourtant que ces comptes ne sont pas désactivés.
Son Vérif les laisse sans connexion seulement « tant qu’aucun fournisseur ne les reconnaît », ce qui
suppose qu'ils se reconnectent dès qu'un fournisseur les reconnaît de nouveau. Or un compte
désactivé ne se connecte pas (WF-ADM-0060), et la lecture ne réactive jamais rien : elle crée, met à
jour ou désactive.

Deux lectures sont donc possibles :
- le retrait ne désactive pas, mais la lecture suivante désactive. Le Vérif de WF-ADM-0180 est alors
  faux après une nouvelle fédération ;
- la lecture épargne ces comptes. WF-ADM-0070 doit alors le dire, et dire selon quel critère.

Le développeur de la lecture et celui de la fédération n'implémenteront pas la même.

**Proposition.** On retient la première lecture, la seule qu'une lecture automatique sache
appliquer sans connaître l'histoire des raccordements.

WF-ADM-0180, corps, remplacer la dernière phrase par :
« La désactivation d’un raccordement ne supprime aucun compte qui en vient. La lecture suivante
désactive ceux que le fournisseur ne connaît plus (WF-ADM-0070). Leurs actes restent attribués, et
ils se réactivent à la main (WF-ADM-0060). »

WF-ADM-0180, Vérif, remplacer « Après retrait de l’annuaire, les comptes qui en venaient existent
toujours et ne peuvent plus se connecter tant qu’aucun fournisseur ne les reconnaît. » par :
« Après retrait de l’annuaire et synchronisation, les comptes qui en venaient existent toujours,
désactivés, et leurs actes restent attribués. Réactivés après une nouvelle fédération qui les
reconnaît, ils se connectent. »

Si l'auteur préfère la seconde lecture, il faut ajouter à WF-ADM-0070 : « Les comptes dont le
raccordement d’origine a été désactivé (WF-ADM-0180) ne sont pas désactivés par la lecture. » Il
faut aussi conserver ce raccordement d'origine parmi les attributs de WF-ADM-0050.

**Statut.** à traiter


---

## C-267 — La lecture des comptes défait l'anonymisation, que WF-ADM-0060 dit irréversible

- **gravité** : majeur
- **emplacement** : §3.4.2.1 « FBS-1.1 : Gestion des utilisateurs » — exigences `WF-ADM-0060-A` (corps), `WF-ADM-0070-A` (corps), `WF-ADM-0050-A` (Motif et Vérif)
- **citation** : « Un compte désactivé peut être anonymisé par un utilisateur habilité à modifier FBS-1.1, à la demande de la personne » et « sont remplacés par un libellé neutre et son avatar retiré, de façon irréversible » (WF-ADM-0060) ; « met à jour ces trois attributs sur les comptes existants » (WF-ADM-0070) ; « c’est par elle que l’annuaire et Waterfall reconnaissent le même compte » (WF-ADM-0050, Motif) ; « Le nom, le prénom et l’adresse d’un compte de l’annuaire ou d’un fournisseur externe ne sont pas modifiables dans Waterfall. » (WF-ADM-0050, Vérif)

**Constat.** WF-ADM-0070 lit tous les comptes du fournisseur d'identité. Elle crée les comptes
absents et remet à jour le nom, le prénom et l'adresse des comptes existants. WF-ADM-0060 anonymise
le compte dans Waterfall, mais ne dit rien du fournisseur. Un compte anonymisé que le fournisseur
connaît encore subit donc la lecture du lendemain. C'est toujours le cas d'un compte local, que le
fournisseur porte (WF-ADM-0180). C'est aussi le cas d'un compte de l'annuaire désactivé à la main
alors que la personne y figure encore.

Deux issues sont possibles, et aucune ne protège l'anonymisation :
- le rapprochement se fait par l'identité du fournisseur : la lecture réécrit le nom et l'adresse ;
- le rapprochement se fait par l'adresse, comme le dit le Motif de WF-ADM-0050 : le compte anonymisé
  ne porte plus cette adresse, la personne passe pour « absente » et un nouveau compte actif est créé
  à son nom.

Dans les deux cas, le Vérif de WF-ADM-0060 (« aucun écran ne présente plus son nom ni son adresse »)
échoue le lendemain. Par ailleurs, le Vérif de WF-ADM-0050 interdit de modifier dans Waterfall le nom
et l'adresse d'un compte de l'annuaire, ce que l'anonymisation fait précisément.

**Proposition.**

WF-ADM-0060, corps, après « de façon irréversible » : « ; un compte local anonymisé est retiré du
fournisseur d’identité ».

WF-ADM-0070, corps, ajouter : « La lecture ne modifie ni ne recrée un compte anonymisé
(WF-ADM-0060). Elle rapproche chaque compte du fournisseur par l’identifiant que celui-ci lui donne,
que l’anonymisation conserve. »

WF-ADM-0070, Vérif, ajouter : « Un compte anonymisé dont la personne figure encore dans l’annuaire
reste anonymisé après synchronisation, et aucun compte n’est créé à son nom. »

WF-ADM-0050, Vérif, compléter : « … ne sont pas modifiables dans Waterfall, hors leur anonymisation
(WF-ADM-0060). »

**Statut.** à traiter


---

## C-268 — L'amorçage ne dit pas quel rôle porte le compte administrateur, et chaque lecture fait échouer un Vérif

- **gravité** : majeur
- **emplacement** : §4.5.2 « Installation initiale », texte et exigence `WF-EXP-0020-A` (corps et Vérif) ; §3.4.2.2, exigences `WF-ADM-0010-A` (Vérif), `WF-ADM-0090-A`, `WF-ADM-0120-A`
- **citation** : « un unique compte administrateur local, créé dans le fournisseur d’identité et dans Waterfall » (WF-EXP-0020) ; « dispose des trois rôles prédéfinis et du catalogue des permissions » (WF-EXP-0020, Vérif) ; « Sur une installation neuve, les trois rôles existent et leurs permissions couvrent les usages des exigences citées. Un administrateur en renomme un, en modifie les permissions et le supprime, sans erreur. » (WF-ADM-0010, Vérif) ; « Un rôle ne peut être supprimé tant qu’un compte le porte. » (WF-ADM-0090)

**Constat.** Ni le corps de WF-EXP-0020 ni le texte du §4.5.2 ne disent quel rôle d'habilitation
porte le compte créé à l'installation. Or un compte sans rôle n'a aucun droit (WF-ADM-0050,
WF-ADM-0090) : lu au mot, l'installeur crée un administrateur qui ne peut rien faire, pas même se
donner un rôle. Le Vérif écrit « dispose des trois rôles prédéfinis », ce qui se lit « porte les trois
rôles ». Les deux lectures font chacune échouer un Vérif :

- **L'administrateur porte les trois rôles.** Sur une installation neuve, chaque rôle prédéfini est
  alors porté par un compte. Le Vérif de WF-ADM-0010, qui se place « sur une installation neuve »,
  supprime un rôle « sans erreur » : WF-ADM-0090 refuse cette suppression pour chacun des trois. De
  plus, WF-ADM-0120 refuse de retirer au rôle « administrateur » les permissions de modifier FBS-1.1
  et FBS-1.2.
- **« Dispose » signifie « trouve ».** L'administrateur n'a alors aucun rôle, et le reste du Vérif
  de WF-EXP-0020 (fixer son mot de passe, puis saisir la catégorie de main-d'œuvre et le rôle de
  ressource) n'est plus possible.

**Proposition.** WF-EXP-0020, corps : « … un unique compte administrateur local, porteur du rôle
prédéfini « administrateur », créé dans le fournisseur d’identité et dans Waterfall, … ».

WF-EXP-0020, Vérif : « Après installation, un administrateur fixe son mot de passe par le lien
produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis et le
catalogue des permissions. »

§4.5.2, texte : « un compte administrateur local unique, porteur du rôle « administrateur », dont le
mot de passe est fixé par le lien que l’installation produit ».

WF-ADM-0010, Vérif, seconde phrase : « Un administrateur renomme un rôle prédéfini et en modifie les
permissions, et il supprime sans erreur un rôle prédéfini qu’aucun compte ne porte. La suppression
du rôle « administrateur » qu’il porte est refusée (WF-ADM-0090, WF-ADM-0120). »

Pour saisir le référentiel, l'administrateur se donne ensuite le rôle « manager » (WF-INTF-0020),
ce que FBS-1.1 lui permet.

**Statut.** à traiter


---

## C-269 — Le journal d'audit garde le nom d'un compte anonymisé, et la base interdit de l'en effacer

- **gravité** : majeur
- **emplacement** : §4.6.1 « Sécurité » — exigence `WF-SEC-0030-A` et texte « Un mot des données personnelles » ; §3.4.2.1 `WF-ADM-0060-A` (Vérif) ; §4.5.1 `WF-EXP-0010-A`
- **citation** : « L'auteur, l'objet et le projet y sont désignés par leur identifiant et par leur libellé — et leur code pour un projet ou un rôle de ressource — tels qu'ils étaient au moment de l'action » (WF-SEC-0030) ; « la base refuse toute modification et toute suppression de ses lignes » (WF-SEC-0030) ; « Après anonymisation d’un compte désactivé, aucun écran ne présente plus son nom ni son adresse » (WF-ADM-0060, Vérif) ; « ce qui laisse l'attribution intacte et ne dit plus qui c'était » (§4.6.1, texte) ; « noms, prénoms, adresses électroniques et avatars remplacés » (WF-EXP-0010)

**Constat.** C-239 a fait porter à chaque inscription le libellé de son auteur et de son objet « tels
qu'ils étaient au moment de l'action », et WF-SEC-0030 fait refuser par la base toute modification
d'une inscription. Le libellé d'un compte est son nom et son prénom ; il figure comme auteur de
chaque action irréversible de la personne, et comme objet de la création, de la modification, de
l'attribution d'un rôle et de l'anonymisation elle-même. Après anonymisation (WF-ADM-0060, C-188),
la consultation du journal (WF-ADM-0190) présente donc toujours le nom : la Vérif de WF-ADM-0060
échoue, et la phrase du §4.6.1 est fausse. Le même défaut atteint WF-EXP-0010 : une copie de
production anonymisée pour la préproduction garde les noms dans `audit_entry`, que la base refuse
de réécrire. Un développeur doit choisir entre l'immuabilité du journal et l'anonymisation, et
chacun des deux choix fait échouer une Vérif.

**Proposition.** Faire de l'anonymisation la seule réécriture permise du journal.

- **WF-SEC-0030, corps** : « […] la base refuse toute modification et toute suppression de ses
  lignes, comme pour une révision marquée (WF-DAT-0020), à une exception : l'anonymisation d'un
  compte (WF-ADM-0060) remplace par le libellé neutre le libellé qui désigne ce compte dans les
  inscriptions, comme auteur ou comme objet, et rien d'autre. » Vérif, ajouter : « Après
  anonymisation d'un compte, aucune inscription ne porte plus son nom ; leur nombre, leurs dates et
  leurs actions sont inchangés. »
- **WF-ADM-0060, Vérif** : « Après anonymisation d’un compte désactivé, aucun écran — journal
  d'audit compris — ne présente plus son nom ni son adresse ; […] ».
- **WF-EXP-0010, corps** : « […] après anonymisation des comptes utilisateurs — noms, prénoms,
  adresses électroniques et avatars remplacés, y compris dans le journal d'audit (WF-SEC-0030) — […] ».

**Statut.** à traiter


---

## C-270 — La Vérif de WF-REV-0040 refuse la correction que le corps et le Motif sont faits pour permettre

- **gravité** : majeur
- **emplacement** : §3.4.5.1 « FBS-4.1 : Gestion des révisions » — exigence `WF-REV-0040-A` (corps, Motif, Vérif)
- **citation** : « Cette désignation peut être corrigée tant que le projet n’a reçu aucun coût réel et qu’aucune révision n’a été marquée depuis. » (corps) ; « La désignation manuelle est proposée tant que le projet n’a ni coût réel ni révision marquée postérieure à la référence, et refusée au-delà. » (Vérif) ; « tant qu’aucun coût réel n’est arrivé et qu’aucune revue n’a été marquée » (Motif)

**Constat.** Le corps mesure le délai de correction à partir de la *désignation* (« depuis ») ; la Vérif
le mesure à partir de la *révision de référence* (« postérieure à la référence »). Les deux divergent
précisément dans le cas que le Motif donne pour justifier la correction : « l’offre v2 au lieu de la v3
effectivement contractualisée ». v3 a été marquée avant la désignation de v2, donc après v2 : selon le
corps, rien n’a été marqué depuis la désignation et la correction vers v3 est permise ; selon la Vérif,
v3 est « postérieure à la référence » et la désignation manuelle est refusée. Lu ainsi, le Vérif interdit
aussi la toute première désignation d’une offre qui n’est pas la dernière marquée. Le testeur et le
développeur qui suivent la Vérif implémentent un produit où l’erreur que l’exigence veut rattraper ne se
rattrape pas. Le Motif, de son côté, dit « aucune revue n’a été marquée » : une revue (revue périodique,
annexe A) ne se marque pas, une révision si, et le « depuis » y manque.

**Proposition.** Vérif de WF-REV-0040 :

> La désignation manuelle est proposée tant que le projet n’a ni coût réel ni révision marquée depuis la
> dernière désignation, et refusée au-delà. Un projet dont les offres v2 puis v3 sont marquées, et dont
> v2 a été désignée par erreur, accepte la désignation de v3 tant qu’il n’a reçu aucun coût réel. Après
> contractualisation d’un avenant, la révision produite est la référence sans intervention de
> l’utilisateur, et l’ancienne reste consultable.

Motif, fin : « … c’est-à-dire tant qu’aucun coût réel n’est arrivé et qu’aucune révision n’a été marquée
depuis la désignation. »

**Statut.** à traiter


---

## C-271 — « Une révision nouvellement créée comporte une structure principale et aucune autre » contredit la reprise des structures

- **gravité** : majeur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0100-A` (Vérif) ; à rapprocher de `WF-REV-0010-A` (corps), `WF-RIS-0030-A`, `WF-DAT-0010-A`
- **citation** : « Une révision nouvellement créée comporte une structure principale et aucune autre. » (WF-REV-0100, Vérif) ; « Sa création reprend les structures de la dernière révision marquée, s’il en existe une » (WF-REV-0010)

**Constat.** WF-REV-0010 et WF-DAT-0010 font copier à la création d’une révision toutes les structures
de la dernière révision marquée — les différentiels non encore fusionnés comme les structures propres
des risques. La troisième phrase de la même Vérif l’exige d’ailleurs : la structure propre d’un risque
déclaré est « présente dans chaque révision marquée postérieure ». La première phrase n’est donc vraie
que pour la première révision d’un projet. Appliquée telle quelle à un projet qui porte un risque, elle
échoue sur une implémentation correcte, ou pousse à une implémentation qui perd les devis propres et les
avenants en préparation à chaque nouvelle révision.

**Proposition.** Vérif de WF-REV-0100, première phrase :

> La première révision d’un projet comporte, à sa création, une structure principale et aucune autre ;
> une révision créée à partir d’une révision marquée en reprend toutes les structures, différentielles
> et propres des risques comprises (WF-REV-0010).

**Statut.** à traiter


---

## C-272 — « aucun écart de montant réestimé » est faux pour un différentiel qui ajoute ou retire des lignes

- **gravité** : majeur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0080-A` (Vérif) ; à rapprocher de `WF-REV-0050-A`, `WF-DEV-0020-A`, `WF-DEV-0030-A`
- **citation** : « restitue exactement les tâches et les montants budgétés de ce différentiel, et aucun écart de montant réestimé » (WF-REV-0080, Vérif)

**Constat.** WF-REV-0080 compare les montants réestimés « par nature de coût et par sous-projet », donc
en totaux. Or la fusion décrite par WF-REV-0050 change ces totaux dans au moins trois cas, sans qu’aucune
autre modification soit faite entre les deux révisions : une ligne ajoutée par le différentiel apporte
son montant réestimé, absent de la révision précédente ; une tâche non démarrée retirée emporte celui de
ses lignes ; une tâche démarrée « retirée » voit son reste à engager porté à zéro, donc son réestimé
ramené à ce qui a été fait. Un différentiel qui retarde une tâche d’une année sur l’autre change aussi
l’année de consommation de ses lignes, donc leur montant (WF-DEV-0030). La phrase « les montants
réestimés de toutes les lignes sont conservés » de WF-REV-0050 ne vaut que pour les lignes existantes
que le différentiel ne fait que désigner. La Vérif échoue donc sur tout avenant ordinaire, et un
développeur qui voudrait la satisfaire annulerait le réestimé des lignes ajoutées.

**Proposition.** Vérif de WF-REV-0080 :

> La comparaison d’une révision obtenue par fusion d’un différentiel avec la révision marquée qui la
> précède, lorsqu’aucune autre modification n’a été faite entre les deux, restitue exactement les tâches
> et les montants budgétés de ce différentiel. Les montants réestimés n’y diffèrent que par les lignes
> que le différentiel ajoute ou retire, par celles des tâches démarrées qu’il termine et par celles dont
> il change l’année de consommation ; une ligne existante dont le différentiel ne modifie que le montant
> budgété ne présente aucun écart de montant réestimé.

**Statut.** à traiter


---

## C-273 — La suppression d’un sous-projet que portent des lignes de la révision en cours n’a pas de règle, et la base la refuse

- **gravité** : majeur
- **emplacement** : §4.4.1 — exigences `WF-DAT-0080-A` (corps et Vérif) et `WF-DAT-0090-A` (corps) ; à rapprocher de `WF-PRJ-0050-A` et de `WF-DEV-0020-A`
- **citation** : « Un sous-projet ou un risque se supprime physiquement tant qu’aucune révision marquée ni, pour un sous-projet, aucune ligne de coût ne le référence » (WF-DAT-0080) ; « la suppression en cascade n’est autorisée qu’à l’intérieur d’une révision en cours, d’une tâche vers ses lignes et ses liaisons » (WF-DAT-0090)

**Constat.** C-256 a fixé le cas du sous-projet cité par une révision marquée. Reste le cas le plus
courant pendant le chiffrage : un sous-projet porté seulement par des lignes de devis de la révision en
cours (« Elle appartient facultativement à un sous-projet », WF-DEV-0020). WF-DAT-0080 dit que sa
suppression est physique. Mais la ligne de devis référence le sous-projet par une clé étrangère « en
refus par défaut », et WF-DAT-0090 ne prévoit de mise à nul que pour le rattachement d’une tâche à un
poste ou à un lot. Telle qu’écrite, la base refuse donc la suppression que WF-DAT-0080 fait aboutir.
Le développeur a deux issues, toutes deux défendables : refuser la suppression tant qu’une ligne
de la révision en cours porte le sous-projet, ou faire passer ces lignes « hors sous-projet ». C’est
le même trou que C-242 a comblé pour le lot. La Vérif de WF-DAT-0080 (« La suppression d’un
sous-projet non référencé le retire de la base ») ne tranche pas : « non référencé » se lit dans les
deux sens.

**Proposition.** En suivant le modèle du lot. WF-DAT-0080, corps, après « … en nommant la raison. » :

> La suppression physique d’un sous-projet retire leur sous-projet aux lignes de devis de la révision en
> cours qui le portaient, qui passent hors sous-projet.

WF-DAT-0090, corps : « La suppression physique d’un poste ou d’un lot met à nul, en base, le
rattachement des tâches de la révision en cours, et celle d’un sous-projet le sous-projet des lignes de
devis de la révision en cours ; … ». Vérif de WF-DAT-0080, remplacer la première phrase par : « La
suppression d’un sous-projet que ne portent que des lignes de la révision en cours le retire de la base,
et ces lignes sont hors sous-projet. » Si l’auteur préfère le refus, écrire à la place dans WF-DAT-0080
« … ni aucune ligne de devis de la révision en cours ne le référence » et l’ajouter au Vérif de
WF-PRJ-0050.

**Statut.** à traiter


---

## C-274 — Le calcul est refusé tant qu’une catégorie employée n’a pas de taux, or une catégorie hors main-d’œuvre ou de provision n’en porte jamais

- **gravité** : majeur
- **emplacement** : §3.4.5.4 « Chiffrage et devis » — exigence `WF-DEV-0010-A` (corps, Vérif) ; à rapprocher de `WF-REF-0050-A` et de §3.3.1
- **citation** : « Le calcul d’un devis ou d’un reste à engager est refusé tant qu’une catégorie de coût employée n’a pas de taux horaire pour l’année de référence de sa révision (WF-REV-0060), ou de taux conservé projeté pour celle-ci. » (WF-DEV-0010) ; « Les catégories des autres natures ne portent pas de taux. » (WF-REF-0050)

**Constat.** Depuis C-026, toute ligne de devis porte une catégorie de coût, hors main-d’œuvre et
provision comprises (WF-DEV-0020), et toute ligne de provision porte la catégorie que son risque
désigne (WF-RIS-0010, C-257). Une catégorie hors main-d’œuvre ou de provision est donc
« employée » dès qu’une ligne la porte ; or WF-REF-0050 lui interdit tout taux. Lue à la lettre,
WF-DEV-0010 refuse le calcul de tout devis qui contient une fourniture ou une provision, et nomme
ces catégories comme manquantes — un refus qu’aucune saisie ne peut lever, puisque WF-REF-0050
refuse le taux demandé. C-026 l’avait relevé (« la notion de catégorie employée n’est définie que
pour la main-d’œuvre ») ; la correction a porté sur la ligne, pas sur WF-DEV-0010. Un développeur
qui restreint de lui-même le contrôle aux catégories de main-d’œuvre le fait sans texte ; un
testeur qui suit la Vérif (« énumère les catégories de coût sans taux horaire ») le déclarera en
écart.

**Proposition.** WF-DEV-0010, corps : « Le calcul d’un devis ou d’un reste à engager est refusé
tant qu’une catégorie de coût de main-d’œuvre, employée par le rôle d’une ligne, n’a pas de taux
horaire pour l’année de référence de sa révision (WF-REV-0060), ou de taux conservé projeté pour
celle-ci. Les catégories concernées sont nommées une par une. Les catégories hors main-d’œuvre et
de provision pour risques, qui ne portent pas de taux (WF-REF-0050), n’entrent pas dans ce
contrôle. » Vérif, ajouter : « Un devis qui ne porte que des lignes hors main-d’œuvre et une ligne
de provision se calcule sans aucun taux horaire. » Le §3.3.1 (« dépendent des catégories de coût
qu’un devis emploie réellement ») et le Motif de WF-CYC-0120 peuvent dire « des catégories de
main-d’œuvre ».

**Statut.** à traiter


---

## C-275 — Une tâche non démarrée en retard : le plan de charge met son reste dans les mois écoulés, la courbe en S après la date de calcul

- **gravité** : majeur
- **emplacement** : §3.4.5.4.4 « Plan de charge du projet » — exigence `WF-DEV-0070-A` ; à rapprocher de `WF-IND-0100-A`, `WF-PTF-0060-A` et du texte d’introduction du §3.4.5.5.2
- **citation** : « la charge restante d’une ligne d’une tâche démarrée est répartie sur la seule part de la durée de la tâche postérieure à la date de calcul (WF-IND-0010), et portée au mois de la date de calcul lorsque la fin de la tâche est dépassée » (WF-DEV-0070) ; « le reste à engager de chaque ligne est étalé, au prorata des heures travaillées (WF-DEV-0040), sur la part de la durée de sa tâche postérieure à la date de calcul » (WF-IND-0100)

**Constat.** C-155 a corrigé les deux exigences, mais pas de la même façon : WF-IND-0100 applique
la règle à « chaque ligne », WF-DEV-0070 à la seule « tâche démarrée ». Or une tâche peut être non
démarrée et datée, dans la révision en cours, avant la date de calcul : rien ne recale une tâche en
mode automatique sur le jour courant (WF-PLA-0020), et une tâche qui devait commencer le mois
dernier et n’a pas commencé est le cas ordinaire d’un retard. Pour elle, la courbe en S place son
reste après la date de calcul, tandis que le plan de charge le répartit sur toute la durée de la
tâche — dans des mois écoulés, que personne ne peut plus staffer —, et le place même entièrement
dans le passé si sa fin est dépassée. Le plan de charge agrégé, qui consolide cette base
(WF-PTF-0060), hérite du défaut. La différence contredit aussi le §3.4.5.5.2, pour qui le
démarrage « n’a pas d’autre effet que d’exposer les lignes de la tâche à la réestimation » : sous
WF-DEV-0070, démarrer une tâche en retard déplace sa charge dans le plan de charge.

**Proposition.** WF-DEV-0070, corps : « Sur la base d’une révision marquée pour sa charge
réestimée ou de la révision en cours — la base du reste à engager —, la charge restante de chaque
ligne d’une tâche non terminée est répartie sur la seule part de la durée de la tâche postérieure à
la date de calcul (WF-IND-0010), et portée au mois de la date de calcul lorsque la fin de la tâche
est dépassée. » Vérif, ajouter : « Une tâche non démarrée dont la date de début est antérieure à la
date de calcul ne présente aucune charge sur les mois écoulés ; sa charge est la même avant et
après son démarrage. »

**Statut.** à traiter


---

## C-276 — Après un avenant qui change une ligne non démarrée et non réestimée, le reste à engager suit le différentiel ou reste à l’ancien montant selon le passage lu

- **gravité** : majeur
- **emplacement** : §3.4.5.5 « Estimation du reste à engager » — exigence `WF-RAE-0010-A` (corps, Vérif) ; à rapprocher de `WF-REV-0050-A` (§3.4.5.1) et de `WF-DEV-0020-A`
- **citation** : « et sinon du montant réestimé de ses lignes, qui, faute de réestimation, se calcule depuis les grandeurs de la référence » (WF-RAE-0010) ; « La fusion ne modifie que les montants budgétés des lignes que le différentiel désigne ; les montants réestimés de toutes les lignes sont conservés. » (WF-REV-0050) ; « le montant budgété depuis les grandeurs de la ligne dans la révision de référence, le montant réestimé depuis ses grandeurs courantes » (WF-DEV-0020)

**Constat.** Soit une ligne de 100 heures, sur une tâche non démarrée, que personne n’a réestimée,
et un avenant dont le différentiel la porte à 150 heures. Après la fusion, trois passages
répondent différemment à la question « que vaut-elle au reste à engager ? ». WF-REV-0050 conserve
son montant réestimé : 100 heures. WF-RAE-0010, depuis C-224, calcule le montant réestimé d’une
ligne non réestimée « depuis les grandeurs de la référence » ; la référence est désormais la
révision fusionnée, et la ligne y porte… les grandeurs que la fusion n’a pas touchées (100) ou
celles du différentiel (150), selon qu’on lit « grandeurs de la référence » comme les grandeurs
courantes de la révision de référence ou comme ce dont le montant budgété est tiré. WF-DEV-0020
tire le montant budgété « des grandeurs de la ligne dans la révision de référence » : pour qu’il
vaille 150 alors que la fusion conserve 100 comme grandeurs courantes, la ligne doit porter deux
jeux de grandeurs dans la même révision, ce qu’aucune exigence ne dit (WF-RAE-0040 n’affiche que
les grandeurs « au reste à engager précédent » et « courantes »). La Vérif de WF-RAE-0010 (« égale
la somme des montants réestimés courants ») tranche pour 100 ; l’intention probable — un avenant
qui ajoute du travail non commencé l’ajoute au reste à engager — pour 150. La projection du chef de
projet, l’écart de WF-RAE-0020 et le plan de charge en dépendent. La Vérif de WF-REV-0050 ne
traite que la ligne non désignée.

**Proposition.** WF-REV-0050, corps, remplacer la phrase citée par : « La fusion donne aux lignes
que le différentiel désigne les grandeurs de référence qu’il porte, d’où leur montant budgété est
tiré (WF-DEV-0020). Une ligne désignée d’une tâche non démarrée, que personne n’a réestimée,
prend aussi ces grandeurs pour grandeurs courantes ; les grandeurs courantes et le montant
réestimé de toutes les autres lignes sont conservés. » WF-DEV-0020, corps : « le montant budgété
depuis ses grandeurs de référence, fixées par la révision de référence, le montant réestimé depuis
ses grandeurs courantes ». WF-RAE-0010, Vérif, ajouter : « Après un avenant qui porte de 100 à 150
heures une ligne non réestimée d’une tâche non démarrée, le reste à engager compte 150 heures ;
une ligne réestimée à 140 avant l’avenant garde 140. » Si l’auteur veut au contraire que le reste
à engager ignore l’avenant tant que le chef de projet n’a pas réestimé, c’est la phrase « faute de
réestimation, se calcule depuis les grandeurs de la référence » de WF-RAE-0010 qu’il faut
remplacer par « faute de réestimation, est celui que la ligne portait avant la dernière fusion ».

**Statut.** à traiter


---

## C-277 — La Vérif attend que l’indice de coût se dégrade à l’ajout d’une tâche, qui ne change ni la valeur acquise ni le coût réel

- **gravité** : majeur
- **emplacement** : §3.4.5.5.3 « Grille de reste à engager », texte d’introduction (second alinéa) ; exigence `WF-RAE-0050-A` (corps, Motif, Vérif) ; à rapprocher de `WF-IND-0070-A` et `WF-IND-0050-A`
- **citation** : « Après ajout d’une tâche chiffrée en revue périodique, le reste à engager et la projection à terminaison augmentent de son montant, le budget de référence est inchangé, et l’indice de coût se dégrade. » (WF-RAE-0050, Vérif) ; « Ils augmentent le reste à engager, donc la projection à terminaison, et dégradent l’indice de coût » (§3.4.5.5.3)

**Constat.** L’indice de coût est « le rapport de la valeur acquise au coût réel » (WF-IND-0070).
L’ajout d’une tâche au reste à engager ne touche ni l’un ni l’autre : l’indice est strictement
inchangé au moment de l’ajout. Il se dégradera plus tard, quand la dépense de cette tâche arrivera
au coût réel sans acquérir de valeur, puisque son montant budgété est nul. Une implémentation
conforme à WF-IND-0070 échoue donc à la Vérif de WF-RAE-0050, et un développeur qui veut la
satisfaire est poussé à faire entrer le reste à engager dans l’indice. Le singulier « la
projection à terminaison » a le même défaut : WF-IND-0050 en présente trois, et seule la
projection du chef de projet augmente — la projection au budget et celle au rythme constaté sont
inchangées.

**Proposition.** WF-RAE-0050, corps : « Elles augmentent le reste à engager et la projection du
chef de projet (WF-IND-0050) ». Vérif : « Après ajout d’une tâche chiffrée en revue périodique, le
reste à engager et la projection du chef de projet augmentent de son montant ; le budget de
référence, la projection au budget, la projection au rythme constaté et l’indice de coût sont
inchangés. Lorsque la dépense de cette tâche est importée au coût réel, la valeur acquise ne change
pas et l’indice de coût baisse. » §3.4.5.5.3 : « Ils augmentent le reste à engager, donc la
projection du chef de projet, et dégraderont l’indice de coût à mesure que leur dépense sera
constatée : c’est exactement ce qu’ils doivent faire. » Le Motif de WF-RAE-0050 peut rester.

**Statut.** à traiter


---

## C-278 — Le portefeuille à une date passée a besoin de plus que les indicateurs conservés

- **gravité** : majeur
- **emplacement** : §4.4.2 « Historisation et immuabilité des révisions » — exigence `WF-DAT-0040-A` (corps et Vérif) et texte « Chaque révision possède ses lignes » ; §3.4.3 `WF-PTF-0010-A`, `WF-PTF-0060-A`, `WF-PTF-0080-A`, `WF-PTF-0090-A` ; §4.6.2 tableau 15
- **citation** : « Une vue de portefeuille à une date passée, sur trois cents projets, ne lit aucune ligne de tâche ni de ligne de devis. » (WF-DAT-0040, Vérif) ; « Les vues du portefeuille à une date passée et l’historique des indicateurs d’un projet lisent ces valeurs conservées et ne recalculent rien » (WF-DAT-0040, corps) ; « le portefeuille ne lit que les indicateurs conservés » (§4.4.2, texte) ; « Toute vue du portefeuille se calcule sur un périmètre choisi par l’utilisateur » (WF-PTF-0010) ; « par rôle de ressource et par mois, la somme des charges des projets du périmètre » (WF-PTF-0060)

**Constat.** WF-PTF-0010 rend calculable à une date passée chaque vue du portefeuille (« Toute vue du portefeuille se calcule […] à une date »). WF-DAT-0040 ne
conserve que les indicateurs « par sous-projet […] et pour le projet » et les deux séries de
courbes, et sa Vérif interdit à toute vue de portefeuille à une date passée de lire une tâche ou une
ligne de devis. Trois vues ont besoin d'autre chose : le plan de charge agrégé (WF-PTF-0060), qui
somme des charges par rôle et par mois que WF-DEV-0070 tire des lignes et des dates des tâches ; la
structure des coûts (WF-PTF-0080), ventilée par nature et, pour la main-d'œuvre, par nœud
d'organisation ; la vue des risques (WF-PTF-0090), qui classe chaque risque par sa provision et le
place dans la matrice — données portées par l'évaluation des risques et par les lignes de
provision de chaque révision. Ou bien WF-DAT-0040 conserve aussi ces agrégats, ou bien ces vues
lisent le contenu des révisions : dans le second cas, la Vérif de WF-DAT-0040 et l'argument du
§4.4.2 qui justifie le partitionnement par projet tombent, et l'objectif de 2 s du tableau 15 se
mesure sur un autre chemin. Les deux implémentations sont possibles, et le document affirme
l'une tout en exigeant des vues que seule l'autre sert.

**Proposition.** Conserver les agrégats au marquage, comme les indicateurs, ce qui garde intact le principe du §4.4.2.

- **WF-DAT-0040, corps**, après la phrase sur les séries des courbes : « Sont conservés de même la
  charge par rôle de ressource et par mois (WF-DEV-0070), les totaux par nature de coût et, pour la
  main-d'œuvre, par nœud d'organisation (WF-DEV-0060, WF-RAE-0020), et, pour chaque risque, sa
  probabilité, sa gravité, sa provision et son état : c'est ce que lisent, à une date passée, le
  plan de charge agrégé, la structure des coûts et les risques du portefeuille (WF-PTF-0060,
  WF-PTF-0080, WF-PTF-0090). »
- **WF-DAT-0040, Vérif** : « Aucune vue de portefeuille à une date passée, sur trois cents projets —
  plan de charge agrégé, structure des coûts et risques compris —, ne lit de ligne de tâche ni de
  ligne de devis. »

Si l'auteur préfère l'autre voie : Vérif « Une vue d'indices ou de projections de portefeuille à
une date passée […] ne lit aucune ligne de tâche ni de ligne de devis ; le plan de charge agrégé,
la structure des coûts et les risques lisent, projet par projet, la dernière révision marquée
antérieure à cette date » et §4.4.2 « le portefeuille ne lit que les indicateurs conservés, hormis
ces trois vues, qui lisent chaque projet dans sa propre partition ».

**Statut.** à traiter


---

## C-279 — Courbes conservées « au pas du mois », marches exigées au jour près

- **gravité** : majeur
- **emplacement** : §4.4.2 — exigence `WF-DAT-0040-A` ; §3.4.5.8.7 `WF-IND-0100-A` ; §3.4.5.8.8 `WF-IND-0110-A` (Vérif) ; §3.4.5.8 `WF-IND-0030-A` (Vérif)
- **citation** : « Les séries des courbes de coûts cumulés et de valeur acquise (WF-IND-0100, WF-IND-0110) sont conservées avec eux, au pas du mois. » (WF-DAT-0040) ; « Une tâche terminée produit une marche dans la valeur acquise à sa date de terminaison. » (WF-IND-0110, Vérif) ; « la courbe saute de la différence des deux cumulés à la date de l’avenant, ce qui en fait une marche datée » (WF-IND-0100)

**Constat.** C-230 a fixé le pas des courbes conservées d'une révision marquée : le mois. Les exigences de
courbes, elles, raisonnent au jour : la marche de la valeur acquise « à sa date de terminaison »
(WF-IND-0110), la marche du budget « à la date de l’avenant » (WF-IND-0100), et une tâche « terminée
le 12 du mois contribue […] dès cette date » (WF-IND-0030). Aucune ne dit à quel pas les courbes se
calculent et se présentent. Une même révision montrerait donc une courbe au jour tant qu'elle est
en cours, et une courbe au mois une fois marquée : la figure change au marquage, alors que
WF-IND-0010 veut des indicateurs qui ne changent pas après lui, et la Vérif de WF-IND-0110 n'est
pas vérifiable sur une révision marquée. Deux lectures : un pas mensuel partout, ou un pas
journalier que la conservation dégrade.

**Proposition.** Fixer le mois comme pas de toutes les courbes, ce qui garde le choix de C-230.

- **WF-IND-0100** et **WF-IND-0110**, corps, ajouter : « Les courbes se calculent et se présentent au
  pas du mois, chaque point portant le cumul à la fin du mois ; la révision en cours et les révisions
  marquées sont présentées au même pas (WF-DAT-0040). »
- **WF-IND-0110, Vérif** : « Une tâche terminée produit une marche dans la valeur acquise au point du
  mois de sa date de terminaison. »
- **WF-IND-0100, Vérif** : « […] la courbe du budget présente, au point du mois de l'avenant, une
  marche égale à l'écart des deux cumulés à cette date […] ».

**Statut.** à traiter


---

## C-280 — Les tâches planifiées et les tâches demandées entrent en file sans être inscrites dans la table qui fait foi (C-241 non propagé)

- **gravité** : majeur
- **emplacement** : §4.2.1.5 « PBS-5 : Plateforme », PBS-5.3 ; §4.3.2 tableau 8, ligne TFX-10 ; §4.3.1 figure 18 ; §4.3.3 tableau 9, lignes FLX-01 et FLX-02 ; §4.3.4 figures 19 et 20 ; à rapprocher de `WF-ARC-0090-A` et `WF-ARC-0040-A`
- **citation** : « déclenchées par la plateforme, qui dépose la tâche en file à l'heure convenue ; le worker la prend comme les autres » (PBS-5.3) ; « Dépôt en file des tâches planifiées » (tableau 8, TFX-10) ; « tâche mise en file (TFX-04) » (tableau 9, FLX-01 et FLX-02) ; « A->>F: met en file la tâche de marquage » (figure 20) ; « Toute tâche est d’abord inscrite dans la table des tâches de fond (§4.4.1), qui fait foi de son existence, de son état et de son résultat » (WF-ARC-0090)

**Constat.** C-241 a fait de la table des tâches de fond la source de vérité et de la file de Redis une
projection qui « se reconstitue depuis cette table ». Cinq passages du §4 décrivent encore
l'ancien mécanisme : PBS-5.3 et TFX-10 font déposer la tâche planifiée directement dans Redis, et
la figure 18 ne donne aux tâches planifiées qu'une arête, vers Redis — aucune vers PostgreSQL ni
vers l'API ; le tableau 9 et les figures 19 et 20 font passer l'API de la requête à la file
(« A->>F ») sans inscription en base (aucun « A->>B » avant). Un développeur qui suit PBS-5.3 et
TFX-10 produit une sauvegarde planifiée qui n'existe que dans Redis : un redémarrage de Redis
avant sa prise la perd, ce que WF-ARC-0090 interdit (« aucune tâche demandée n’est perdue par la
perte de la file ») et ce que la Vérif de WF-ARC-0040 teste (« Une tâche demandée avant le vidage
de Redis et non encore prise est exécutée après le rétablissement »). La perte touche précisément
la sauvegarde quotidienne sur laquelle repose la perte maximale de WF-EXP-0050. Et s'il fallait
que le composant PBS-5.3 inscrive lui-même la tâche, il lui faudrait un accès à PostgreSQL que le
tableau 8 ne lui donne pas.

**Proposition.** Faire passer toute création de tâche par l'API, seule à écrire la table puis la file.

- **PBS-5.3** : « les sauvegardes planifiées (WF-ADM-0170) et la lecture périodique des comptes du
  fournisseur d'identité, déclenchées par la plateforme, qui demande la tâche au service d'API à
  l'heure convenue ; l'API l'inscrit dans la table des tâches de fond et la met en file
  (WF-ARC-0090), et le worker la prend comme les autres. »
- **Tableau 8, TFX-10** : « | TFX-10 | Tâches planifiées (PBS-5.3) | Service d'API | HTTPS, demande
  d'une tâche planifiée | Secret de la plateforme | ».
- **Figure 18** (`figures/deploiement.mmd`) : remplacer « Planif --> Redis » par « Planif --> API ».
- **Tableau 9, FLX-01** : « Dépôt par TFX-02, fichier écrit sur le stockage objet (TFX-05), tâche
  inscrite dans la table des tâches de fond (TFX-03) puis mise en file (TFX-04), analyse par le
  worker, […] » ; même insertion pour FLX-02.
- **Figures 19 et 20** : avant chaque « A->>F: met en file … », ajouter « A->>B: inscrit la tâche ».

**Statut.** à traiter


---

## C-281 — Ce que Prometheus collecte, par où l'écran d'état le lit, et où paraît une alerte quand l'écran tombe : trois trous entre WF-OBS-0010/0030 et le tableau des flux

- **gravité** : majeur
- **emplacement** : §4.6.3 « Observabilité » — exigences `WF-OBS-0010-A` et `WF-OBS-0030-A` ; §4.3.2 tableau 8, ligne TFX-09 ; §4.3.1 figure 18 ; §4.3.3 texte ; §4.2.1.4 PBS-4.3 ; §4.5.4 `WF-EXP-0040-A` ; à rapprocher de `WF-ADM-0130-A` et de `WF-SEC-0010-A`
- **citation** : « pour les composants de données, la disponibilité, l'espace utilisé et disponible. L'écran d'état du système ne présente que des valeurs issues de ces métriques. » (WF-OBS-0010, corps) ; « Chaque composant répond sur son point de métriques. » (WF-OBS-0010, Vérif) ; « Front, API, worker » (tableau 8, TFX-09, destination) ; « Les flux fonctionnels avec les acteurs (FLX-09 à FLX-19) empruntent tous le même chemin : TFX-01 puis TFX-02, et rien d’autre. » (§4.3.3) ; « Chaque alerte en cours est présentée sur l'écran d'état du système, avec sa date d'apparition. » (WF-OBS-0030) ; « l'alerte de WF-OBS-0030 est ce qui le signale à l'exploitant » (WF-EXP-0040)

**Constat.** Trois points, qui touchent la même chaîne de l'exigence à l'écran.

1. **Sources.** WF-OBS-0010 veut que les composants de données exposent leur disponibilité et
   leur espace, et sa Vérif que « chaque composant » réponde sur son point de métriques ;
   WF-ADM-0130 présente la disponibilité de « chaque composant de la plateforme », fournisseur
   d'identité compris (il figure au tableau 12). Or TFX-09 et la figure 18 ne font collecter par
   Prometheus que le front, l'API et le worker : ni PostgreSQL, ni Redis, ni le stockage objet, ni
   Keycloak, et aucun exporteur n'est au PBS. Quand ces composants sont fournis par l'exploitant
   (WF-ARC-0050), la Vérif ne peut même pas leur être imposée. Deux architectures sont possibles —
   des exporteurs déployés et collectés, ou une sonde de l'API qui publie la disponibilité des
   autres comme ses propres métriques — et le document ne choisit pas.
2. **Lecture.** L'écran d'état est servi par TFX-01 puis TFX-02 (« et rien d'autre », §4.3.3) et
   ne présente que des métriques : l'API doit donc interroger Prometheus, et ses alertes. Aucun flux
   du tableau 8 ni aucune arête de la figure 18 ne le permet ; WF-SEC-0010 chiffre « conformément au
   tableau des flux techniques », si bien qu'un flux absent n'a ni protocole ni authentification.
3. **Alerte sans écran.** C-254 a fait reposer le signalement de la perte de PostgreSQL ou de Redis
   sur l'alerte de WF-OBS-0030, mais WF-OBS-0030 ne présente ses alertes que « sur l'écran d'état du
   système » — celui qui, dans ces deux cas, n'est pas servi. La « vue de l’exploitant » de PBS-4.3,
   sur laquelle C-254 comptait, n'a ni exigence, ni flux, ni nœud sur la figure 18.

**Proposition.** - **WF-OBS-0010, corps** : « Le front, l'API et le worker exposent leurs métriques au format
  Prometheus : pour le front et l'API, […] ; pour le worker, […]. L'API expose en outre, pour chaque
  composant de données et pour le fournisseur d'identité, sa disponibilité, vérifiée par une sonde à
  chaque collecte, et, pour PostgreSQL et le stockage objet, l'espace utilisé et disponible. » Vérif :
  « Le front, l'API et le worker répondent sur leur point de métriques. L'arrêt de PostgreSQL, de
  Redis, du stockage objet ou du fournisseur d'identité fait passer sa disponibilité à zéro à la
  collecte suivante. […] »
- **Tableau 8**, au prochain numéro libre : « | TFX-nn | Service d'API | Prometheus | HTTPS, API de
  requête : métriques et alertes en cours | Réseau interne au cluster ; compte de service | » et
  « | TFX-nn | Navigateur de l'exploitant | Tableau de bord et alertes (PBS-4.3) | HTTPS | Compte de
  l'exploitant | ». **Figure 18** : « API --> Prometheus », et un nœud « Tableau de bord (PBS-4.3) »
  joint par le navigateur.
- **§4.3.3** : « […] TFX-01 puis TFX-02 ; l'écran d'état (FLX-18) lit en outre les métriques et les
  alertes par TFX-nn. »
- **WF-OBS-0030**, dernière phrase : « Chaque alerte en cours est présentée sur l'écran d'état du
  système, avec sa date d'apparition, et sur le tableau de bord de l'exploitant (PBS-4.3), qui reste
  servi lorsque PostgreSQL ou Redis sont indisponibles. » Vérif, ajouter : « Pendant l'arrêt de
  PostgreSQL, l'alerte d'indisponibilité est visible sur le tableau de bord de l'exploitant. »

**Statut.** à traiter


---

## C-282 — L'invalidation du cache n'énumère pas toutes les écritures dont dépend un indicateur au jour courant

- **gravité** : majeur
- **emplacement** : §4.4.5 « Cache » — exigence `WF-DAT-0130-A` (corps et Vérif) ; à rapprocher de `WF-CRE-0030-A`, `WF-CRE-0040-A`, `WF-CRE-0020-A`, `WF-REV-0040-A`, `WF-REV-0010-A`
- **citation** : « Chaque entrée est invalidée par l'écriture dont elle dépend : toute écriture dans une révision en cours invalide ses indicateurs, le marquage d'une révision invalide les entrées du projet, et un import de coûts réels appliqué invalide les entrées du projet. » (WF-DAT-0130) ; « Une ligne exclue reste consultable mais n’entre dans aucun indicateur. » (WF-CRE-0030) ; « La création d’un sous-projet portant ce code lui impute aussitôt les lignes qui l’attendaient » (WF-CRE-0020)

**Constat.** La liste de WF-DAT-0130 se lit comme la règle — elle suit un deux-points et sa Vérif ne teste
qu'une ligne de devis. Plusieurs écritures changent pourtant les indicateurs au jour courant sans
être ni une écriture dans la révision en cours, ni un marquage, ni un import : l'exclusion et la
réintégration d'une ligne de coût (WF-CRE-0030, dont WF-CRE-0040 veut l'effet « immédiat ») ; la
création d'un sous-projet qui se voit imputer des lignes en attente (WF-CRE-0020) ; la désignation
ou la correction de la révision de référence (WF-REV-0040), qui change le budget de référence et la
valeur planifiée, et fait parfois passer le projet à En cours ; l'abandon de la révision en cours
(WF-REV-0010), après lequel les indicateurs au jour courant se lisent sur la dernière révision
marquée. La dernière phrase (« Aucune lecture ne sert une valeur devenue fausse […] ») les couvre en
principe, mais un développeur qui implémente la liste sert un indice de coût faux pendant dix
minutes après une exclusion.

**Proposition.** - **WF-DAT-0130, corps** : « Chaque entrée est invalidée par l'écriture dont elle dépend :
  toute écriture dans une révision en cours, et son abandon, invalident les indicateurs du projet ;
  le marquage d'une révision, la désignation ou la correction de la révision de référence,
  l'application d'un import de coûts réels, l'exclusion ou la réintégration d'une ligne de coût et la
  création d'un sous-projet auquel des lignes de coût sont imputées invalident les entrées du
  projet. »
- **Vérif**, ajouter : « L'exclusion d'une ligne de coût change l'indice de coût au jour courant à la
  lecture suivante ; l'abandon de la révision en cours présente à la lecture suivante les indicateurs
  de la dernière révision marquée au jour courant. »

**Statut.** à traiter


---

## C-283 — La copie des sauvegardes hors de la plateforme n'a pas de flux, et le §4.3.1 l'exclut

- **gravité** : majeur
- **emplacement** : §4.3.1 « Diagramme de déploiement », texte et figure 18 ; §4.3.2 tableau 8 ; à rapprocher de `WF-ADM-0170-A`, `WF-EXP-0050-A`, PBS-3.3 et `WF-SEC-0010-A`
- **citation** : « la plateforme ne parle hors du cluster qu’à l’annuaire, au fournisseur d’identité externe lorsqu’il y en a un (WF-ADM-0180), et au serveur de messagerie » (§4.3.1) ; « Une sauvegarde planifiée peut être copiée automatiquement vers un emplacement externe paramétré » (WF-ADM-0170) ; « garantie par une sauvegarde planifiée quotidienne (WF-ADM-0170) copiée hors de la plateforme » (WF-EXP-0050) ; « c’est de lui qu’elles se copient hors de la plateforme » (PBS-3.3)

**Constat.** La perte maximale de vingt-quatre heures (WF-EXP-0050) repose sur une copie quotidienne hors de
la plateforme, que WF-ADM-0170 fait faire automatiquement « vers un emplacement externe
paramétré », depuis le stockage objet (PBS-3.3). C'est un flux sortant du cluster. Le tableau 8 ne
le porte pas, la figure 18 n'a aucun nœud pour cet emplacement, et la phrase du §4.3.1 — dont C-249
rappelait qu'elle sert à l'exploitant à ouvrir ses flux réseau — énumère les destinations hors
cluster sans lui. WF-SEC-0010 chiffrant « conformément au tableau des flux techniques », ce flux n'a
ni protocole, ni authentification, ni composant source désigné.

**Proposition.** - **Tableau 8**, au prochain numéro libre : « | TFX-nn | Worker | Emplacement externe des
  sauvegardes | S3 sur HTTPS, ou le protocole de l'emplacement paramétré | Clés d'accès de
  l'emplacement | ».
- **§4.3.1, texte** : « […] la plateforme ne parle hors du cluster qu’à l’annuaire, au fournisseur
  d’identité externe lorsqu’il y en a un (WF-ADM-0180), au serveur de messagerie et à l'emplacement
  externe des sauvegardes (WF-ADM-0170) ; […] ».
- **Figure 18** : un nœud « Emplacement externe des sauvegardes » hors du sous-graphe du cluster, et
  l'arête « Worker --> Externe ».
- **PBS-2.2** : « […] exports, sauvegardes et leur copie externe, lecture des comptes […] ».

*Relevé aussi par la relecture de la tranche E (relevé E-25), fusionné ici.*

**Statut.** à traiter


---

## C-284 — Des exigences F0 reposent sur des exigences F1

- **gravité** : majeur
- **emplacement** : §4.4.6 `WF-DAT-0140-A` (Vérif) et §4.5.3 `WF-EXP-0030-A` (F1) ; §3.4.2.1 `WF-ADM-0040-A` (F1) et §3.6 `WF-IHM-0060-A`, §3.1.5 `WF-INTF-0160-A`, §3.4.5.5.3 `WF-RAE-0040-A`, §3.4.3.2 `WF-PTF-0060-A` (F0) ; à rapprocher de `WF-QUA-0010-A`
- **citation** : « Une installation en version N passe en version N+1 sans interruption de service ni perte de données. » (WF-DAT-0140, Vérif, F0) ; « Le choix des colonnes, des largeurs, du tri et des filtres est une préférence d’affichage (WF-ADM-0040), conservée par grille. » (WF-IHM-0060, F0) ; « La langue de l'interface (WF-INTF-0160) est l'une de ces préférences. » (WF-ADM-0040, F1)

**Constat.** WF-QUA-0010 donne au F0 et au F1 des conséquences opposées : une exigence F0 doit être testée
et bloque la publication, une F1 a un respect « souhaité, non garanti ». Deux couples se contredisent sur ce
point. WF-EXP-0030 « Mise à jour sans interruption » est F1, mais la Vérif de WF-DAT-0140, F0, exige
le passage de N à N+1 « sans interruption de service » : la publication est refusée tant que la
propriété F1 n'est pas tenue. WF-ADM-0040 « Préférences d’affichage » est F1, mais quatre exigences
F0 en dépendent : WF-IHM-0060 (réglages des grilles, retrouvés à la réouverture), WF-INTF-0160 (la
langue : « ce choix est conservé dans son compte », et WF-ADM-0040 la range parmi les préférences), WF-RAE-0040
et WF-PTF-0060. Une équipe qui reporte les F1 au-delà du MVP casse ces quatre F0 ; une équipe qui
lit les F0 fait de fait les F1.

**Proposition.** - **WF-EXP-0030** : flexibilité « F0 », puisque WF-DAT-0140 et WF-ARC-0080 l'exigent déjà ; ou,
  si l'auteur tient au F1, **WF-DAT-0140, Vérif** : « Une installation en version N passe en version
  N+1 sans perte de données, et le code de la version N s'exécute sur le schéma migré. »
- **WF-ADM-0040** : flexibilité « F0 » ; ou scinder : « La conservation des réglages de grille
  (WF-IHM-0060), des réglages du plan de charge agrégé (WF-PTF-0060) et de la langue (WF-INTF-0160)
  est exigée [F0] ; les autres préférences d'affichage sont souhaitées [F1]. »

**Statut.** à traiter


---

## C-285 — La sortie « Terminer » d'un projet en chiffrage : absente du menu selon WF-CYC-0060, présentée indisponible selon WF-IHM-0090

- **gravité** : majeur
- **emplacement** : §3.6 — exigence `WF-IHM-0090-A` (Vérif) ; §3.3.2 `WF-CYC-0060-A` (Vérif)
- **citation** : « Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en nommant la condition manquante. » (WF-IHM-0090, Vérif) ; « Pour chaque état non terminal, le menu des sorties ne propose que les sorties permises depuis cet état, conformément au diagramme du cycle de vie. » (WF-CYC-0060, Vérif)

**Constat.** Les deux Vérif portent sur le même écran et attendent deux choses. Le testeur de WF-CYC-0060
vérifie que « Terminer » ne figure pas au menu d'un projet en chiffrage ; celui de WF-IHM-0090
vérifie qu'il y figure, grisé, avec sa condition. Les deux tests ne peuvent pas passer ensemble. Le
cas n'est pas symétrique pour toutes les sorties : « Terminer » depuis Chiffrage deviendra possible
(le projet passera à En cours), « Déclarer perdu » depuis En cours ne le deviendra jamais
(WF-CYC-0060, WF-CYC-0080) ; c'est la distinction « momentanément impossible » de WF-IHM-0090.

**Proposition.** **WF-CYC-0060, Vérif** : « Pour chaque état non terminal, le menu des sorties ne permet que les
sorties permises depuis cet état. Une sortie qui le deviendra dans un état ultérieur — Terminer
depuis Chiffrage — y est présentée indisponible, avec sa condition (WF-IHM-0090) ; une sortie qui ne
le deviendra jamais — Déclarer perdu depuis En cours — n'y figure pas. »

**Statut.** à traiter


---

## C-286 — Un collage partiellement invalide : grille inchangée selon le corps, lignes valides écrites selon la Vérif

- **gravité** : majeur
- **emplacement** : §3.6 — exigence `WF-IHM-0050-A` (corps et Vérif) ; à rapprocher de `WF-INTF-0080-A`
- **citation** : « Avant application, Waterfall présente ce qui sera écrit et ce qui sera refusé, avec le motif de chaque refus » (WF-IHM-0050, corps) ; « Un collage abandonné ou partiellement invalide laisse la grille inchangée. » (WF-IHM-0050, corps) ; « Un bloc dont une cellule porte une catégorie inconnue signale cette ligne et, en cas d'abandon, ne modifie aucune ligne. » (WF-IHM-0050, Vérif)

**Constat.** La dernière phrase du corps se lit : un collage abandonné, ou un collage partiellement invalide, laisse la grille inchangée ;
un bloc dont une seule cellule est invalide ne s'applique jamais, même confirmé. Le reste de
l'exigence dit le contraire : le compte rendu sépare « ce qui sera écrit » de « ce qui sera
refusé », ce qui n'a de sens que si l'on peut écrire le premier ; la Vérif réserve le « ne modifie
aucune ligne » au cas de l'abandon ; et le motif aligne le collage sur l'import, dont WF-INTF-0080
applique les lignes lues et rejette les autres. Un développeur peut implémenter le « tout ou
rien » ou l'application partielle, et l'un des deux tests échoue.

**Proposition.** **WF-IHM-0050, corps** : « Avant application, Waterfall présente ce qui sera écrit et ce qui sera
refusé, avec le motif de chaque refus ; après confirmation, les lignes valides sont écrites en une
seule opération, et les lignes refusées ne le sont pas. Un collage abandonné laisse la grille
inchangée. » **Vérif** : « […] Un bloc dont une cellule porte une catégorie inconnue signale cette
ligne ; confirmé, il écrit les autres lignes et non celle-ci ; abandonné, il ne modifie aucune
ligne. […] » (Si l'auteur veut le « tout ou rien », écrire à l'inverse : « Un collage dont une ligne
est refusée ne peut pas être confirmé ; il se corrige ou s'abandonne. »)

**Statut.** à traiter


---

## C-287 — Vérif dont l'exemple est faux ou suppose une hypothèse non dite

- **gravité** : mineur
- **emplacement** : §3.4.4.3 « FBS-3.3 : Paramètres de risques » — exigence `WF-REF-0160-A` (Vérif) ; §3.4.3 « FBS-2 : Portefeuille » — exigence `WF-PTF-0010-A` (Vérif) ; §3.4.3.1 « FBS-2.1 : Portefeuille de projets » — exigence `WF-PTF-0050-A` (Vérif) ; §3.4.5.1 — exigence `WF-REV-0010-A` (Vérif) ; §3.4.5.8.7 « Coûts cumulés (courbe en S) » — exigence `WF-IND-0100-A`, Vérif ; §3.4.5.4 — exigence `WF-DEV-0020-A`, Vérif ; §3.4.5.4.4 — exigence `WF-DEV-0070-A`, Vérif ; §3.4.5.6.2 — exigence `WF-RIS-0060-A`, Vérif ; §3.4.5.5.1 — exigence `WF-RAE-0020-A` (corps, Vérif)
- **citations** : une par point, ci-dessous

**Constat.** Les exemples chiffrés des Vérif deviennent des cas de test (WF-QUA-0020). Chacun des points suivants donne un résultat faux, ou juste seulement sous une hypothèse que la phrase ne dit pas : un test écrit à la lettre ferait échouer une implémentation conforme au corps.

**Point 1 — « Le total de son devis courant » compte les provisions, alors que le corps les exclut.** Citation : « Sur un projet en chiffrage, un risque est classé d’après le total de son devis courant » (WF-REF-0160, Vérif) ; « le total hors provisions du devis de sa révision courante » (WF-REF-0160, corps)

Le corps et le texte du §3.4.4.3 rapportent la gravité au devis hors provisions. Le
Vérif écrit « le total de son devis courant ». Or le glossaire définit le devis courant « lignes de
provision comprises sauf lorsque le texte précise « hors provisions » ». Un testeur qui suit le
Vérif classe donc le risque sur une assiette qui contient sa propre provision, et fait échouer une
implémentation conforme au corps. La seconde moitié du Vérif (« si ce total égale le budget de
référence ») n'a de sens que hors provisions, puisque le budget de référence n'en contient jamais.

*Proposition.* « Sur un projet en chiffrage, un risque est classé d’après le total hors provisions
de son devis courant ; la désignation de la révision de référence ne change pas son niveau si ce
total égale le budget de référence. »

*Relevé aussi par la relecture de la tranche A (relevé A-12), fusionné ici.*

**Point 2 — « La contribution pondérée » ignore les deux exceptions de WF-PTF-0020.** Citation : « Le même portefeuille calculé avec et sans les projets en chiffrage donne des valeurs différentes, et la différence égale la contribution pondérée de ces projets. »

WF-PTF-0020, depuis C-122, fait deux exceptions à la pondération : le pipeline brut et
la vue des risques. Pour ces deux grandeurs, la différence entre les deux calculs est la
contribution non pondérée, et le Vérif, pris au mot, fait échouer une implémentation conforme.

*Proposition.* « … et la différence égale la contribution de ces projets, pondérée par leur
probabilité de gain, hors le pipeline brut et la vue des risques, où elle ne l’est pas
(WF-PTF-0020). »

**Point 3 — « Dix offres closes » inclut les offres abandonnées, que le corps exclut.** Citation : « Sur dix offres closes dans la période, dont quatre gagnées, le taux de transformation vaut 40 %. » (Vérif) ; « la part des offres sorties de l’état Chiffrage sur la période » (corps)

Le corps ne compte que les sorties vers En cours ou vers Perdu. Une offre peut aussi
quitter Chiffrage vers Abandonné (figure 8), et ce choix d'exclusion a été acté. Mais une offre
abandonnée est « close » au sens courant. Sur dix offres closes dont une abandonnée, le corps donne
4 / 9, soit 44 %, et le Vérif attend 40 %.

*Proposition.* « Sur dix offres sorties de l’état Chiffrage dans la période vers En cours ou vers
Perdu, dont quatre passées à En cours, le taux de transformation vaut 40 % ; une onzième,
abandonnée dans la période, ne le change pas. »

**Point 4 — La Vérif de WF-REV-0010 dit « les mêmes » valeurs pour des taux que WF-REV-0060 projette.** Citation : « à année de référence égale, elle porte aussi les mêmes valeurs de référentiel, et sinon celles que la mise à jour de WF-REV-0060 n’a pas remplacées »

La clause, introduite par C-131, se lit : à année différente, la révision porte les mêmes
valeurs que la révision marquée, sauf celles que la mise à jour a remplacées. Mais WF-REV-0060, complété
depuis par C-133, ne laisse pas inchangé un taux non remplacé : « Une catégorie non encore présentée,
refusée, ou sans taux pour la nouvelle année, conserve son taux précédent, projeté par le taux
d’inflation du projet jusqu’à la nouvelle année de référence. » Dès que le taux d’inflation n’est pas
nul, le testeur qui compare les taux de la nouvelle révision à ceux de l’ancienne constate un écart que
la Vérif ne prévoit pas.

*Proposition.* Vérif de WF-REV-0010, deuxième phrase :

> Une révision créée à partir d’une révision marquée porte les mêmes tâches et les mêmes lignes ; à année
> de référence égale, elle porte aussi les mêmes valeurs de référentiel ; sinon, elle porte les mêmes
> rôles, calendriers et catégories, et, pour chaque catégorie dont la mise à jour de WF-REV-0060 n’a pas
> été acceptée, le taux précédent projeté par le taux d’inflation du projet jusqu’à la nouvelle année de
> référence.

**Point 5 — « Translatée de 60 jours » est faux dès qu’un risque est identifié, cas que la même phrase suppose.** Citation : « Avec un délai de paiement de 60 jours saisi sur toutes les lignes, main-d’œuvre comprise, la courbe décalée est la courbe de référence translatée de 60 jours ; la somme des décaissements à venir égale le reste à engager, provisions des risques identifiés comprises. »

Refait sur un cas : une ligne de 100 et une provision de 40 portées par une tâche
future. En mode décaissements, 100 se décale de 60 jours, 40 reste en place (corps : « une ligne
de provision, qui n’en porte pas, reste à la date de la tâche qui la porte ») : la projection n’est
pas la courbe non décalée translatée. La première proposition n’est donc vraie que sans risque
identifié, alors que la seconde, dans la même phrase, en suppose. Le coût réel, lui, n’a pas de
délai de paiement (WF-CRE-0010) et n’est pas décalé : « la courbe » ne peut pas être translatée en
entier. Enfin « courbe de référence » ne dit pas laquelle des trois séries est visée.

*Proposition.* « Avec un délai de paiement de 60 jours saisi sur toutes les lignes, main-d’œuvre
comprise, la courbe du budget de référence décalée est la courbe non décalée translatée de 60
jours ; la projection l’est aussi, hormis les lignes de provision, qui restent à leur date ; le
coût réel n’est pas décalé. La somme des décaissements à venir égale le reste à engager,
provisions des risques identifiés comprises. »

**Point 6 — « 80 fois le taux » suppose une quantité de 1.** Citation : « La saisie d’une charge de 80 heures sur une ligne budgétée à 100 heures, consommée dans l’année de référence, donne un montant réestimé de 80 fois le taux » (WF-DEV-0020) ; « La saisie d’une charge de 80 heures sur une ligne budgétée à 100 heures donne un montant réestimé de 80 fois le taux » (WF-RAE-0040)

Le montant d’une ligne de main-d’œuvre est « le produit de sa quantité, de sa charge
et du taux horaire » (WF-DEV-0030). Avec une quantité de 2, la saisie de 80 heures donne 160 fois
le taux. Les deux Vérif ne sont justes que pour une quantité de 1, hypothèse qu’elles ne disent
pas ; un testeur qui prend une ligne à quantité 2 conclut à une anomalie.

*Proposition.* Dans les deux Vérif : « La saisie d’une charge de 80 heures sur une ligne de
quantité 1 budgétée à 100 heures… ».

**Point 7 — Les exemples du plan de charge supposent une tâche calée sur les mois civils.** Citation : « La charge d’une ligne portée par une tâche de deux mois apparaît sur ces deux mois » ; « Une tâche démarrée de quatre mois, à mi-parcours à la date de calcul, dont une ligne porte un reste de 80 heures, présente ces 80 heures sur les deux mois restants »

Le plan de charge est « par mois » civil. Une tâche de deux mois qui court du 15 janvier
au 15 mars apparaît sur trois mois ; une tâche de quatre mois du 15 janvier au 15 mai, à mi-parcours
le 15 mars, répartit son reste sur mars (à moitié), avril et mai (à moitié), et non « 40 et 40 ».
Les deux exemples ne sont justes que pour une tâche qui commence le premier jour ouvré d’un mois.

*Proposition.* « La charge d’une ligne portée par une tâche qui couvre exactement deux mois civils
apparaît sur ces deux mois… » ; « Une tâche démarrée qui couvre exactement quatre mois civils, à
mi-parcours à la date de calcul — le premier jour du troisième mois —, dont une ligne porte un reste
de 80 heures… ».

**Point 8 — Le total du poste « augmente de leur montant » : il augmente de ce montant moins la provision retirée.** Citation : « le total du poste dont cette tâche relève augmente de leur montant »

Le total d’un poste est « le total du sous-arbre » de la tâche rattachée (WF-DEV-0060),
et le devis compte les lignes de provision (WF-RIS-0050 : « le devis totalise 1 060 »). La tâche qui
portait la provision est dans ce sous-arbre ; la survenance y ajoute 120 + 80 et y retire la
provision. Avec le risque de WF-RIS-0050 (provision 60), le poste augmente de 140, non de 200. La
même Vérif le dit juste pour le reste à engager (« a augmenté de 200 moins la provision retirée »).

*Proposition.* « le total du poste dont cette tâche relève augmente de leur montant, moins la
provision retirée ».

**Point 9 — L’écart « avec la révision marquée précédente » à la première revue : avec la référence (corps) ou absent (Vérif) ?.** Citation : « et le reste à engager moins celui de la révision marquée précédente » ; « Sur un projet sans revue précédente, l’écart correspondant est absent plutôt que nul »

À la première revue après la contractualisation, la révision marquée précédente
existe : c’est la référence, marquée pendant le chiffrage. Le corps fait donc calculer l’écart avec
son reste à engager ; la Vérif, qui parle de « revue précédente », le fait présenter absent. Or
WF-DAT-0040 ne conserve, pour une révision marquée avant l’état En cours, que les indicateurs de
devis : son reste à engager n’est pas conservé, et les vues qui lisent l’historique des indicateurs « ne recalculent rien ».

*Proposition.* Corps : « et le reste à engager moins celui de la révision marquée précédente,
lorsque celle-ci a été marquée à l’état En cours ». Vérif : « Sur un projet dont aucune révision
n’a été marquée à l’état En cours avant celle qui est lue, l’écart correspondant est absent plutôt
que nul. »

**Proposition.** Les rédactions de chaque point ci-dessus.

**Statut.** à traiter

---

## C-288 — Le sous-projet d'une ligne existante : l'onglet le donne, la liste des grandeurs mises à jour ne le comprend pas

- **gravité** : mineur
- **emplacement** : §3.1.4 — exigence `WF-INTF-0120-A` ; annexe B ; à rapprocher de `WF-INTF-0100-A`
- **citation** : « met à jour ses grandeurs réestimées (WF-RAE-0040) — charge, ou quantité et débours — sans toucher à son montant budgété ni à sa lignée » (WF-INTF-0120) ; « Le sous-projet d’une ligne est celui de l’onglet qui la porte, le format plaçant chaque sous-projet dans un onglet. » (WF-INTF-0120)

**Constat.** Une ligne existante, retrouvée par sa lignée, que le responsable de lot a déplacée dans
l'onglet d'un autre sous-projet : la dernière phrase de WF-INTF-0120 lui donne le sous-projet de l'onglet,
la première ne range pas le sous-projet parmi ce que l'import met à jour. WF-INTF-0100 le range, lui,
explicitement. Changer le sous-projet d'une ligne déplace son budget d'une maille de rapprochement à l'autre
(§3.2.5) : ce n'est pas un détail de format.

**Proposition.** WF-INTF-0120, remplacer la dernière phrase par : « Le sous-projet d’une ligne créée par
l’import est celui de l’onglet qui la porte, le format plaçant chaque sous-projet dans un onglet ; une ligne
existante placée dans l’onglet d’un autre sous-projet que le sien garde son sous-projet et est signalée au
compte rendu. » (Ou, si l'auteur veut que le fichier fasse foi : « …change de sous-projet, et le compte
rendu le présente comme un écart ».)

**Statut.** à traiter


---

## C-289 — Résidu de C-183 : l'export MS Project ne dit pas quelle révision ni quelle structure il écrit

- **gravité** : mineur
- **emplacement** : §3.1.4 — exigence `WF-INTF-0050-A` ; à rapprocher de `WF-INTF-0110-A`, `WF-INTF-0130-A`, `WF-INTF-0090-A`
- **citation** : « Les plannings Waterfall doivent pouvoir être exportés au format XML MS Project. » (WF-INTF-0050)

**Constat.** C-183 a fait dire aux exports Excel qu'ils portent sur « une structure de coûts d’une révision,
en cours ou marquée, la structure principale par défaut », et à l'import MS Project qu'il porte sur la
structure désignée. L'export MS Project n'a pas suivi : on ne sait ni s'il peut partir d'une révision marquée
ni s'il peut écrire un différentiel ou le devis propre d'un risque, que WF-INTF-0090 permet pourtant de
réimporter.

**Proposition.** WF-INTF-0050, corps, première phrase : « Un utilisateur habilité peut exporter au format
XML MS Project le planning d’une structure de coûts d’une révision, en cours ou marquée, la structure
principale par défaut. »

**Statut.** à traiter


---

## C-290 — L'onglet « Hors sous-projet » et les valeurs fixées d'un fichier exporté : traduits selon WF-ARC-0110, fixes selon l'esprit de WF-INTF-0180

- **gravité** : mineur
- **emplacement** : §3.1.5 — exigence `WF-INTF-0180-A` ; §4.1.3 — exigence `WF-ARC-0110-A` ; annexe B ; à rapprocher de `WF-INTF-0120-A`, `WF-INTF-0170-A`
- **citation** : « les en-têtes de colonnes des formats Excel de l’ANNEXE B: Formats d’échanges Excel, les noms de champs des fichiers MS Project, et les dates et nombres du contrat d'API sont fixes » (WF-INTF-0180) ; « Lorsqu'un service produit lui-même un texte destiné à une personne — fichier engendré, document exporté —, il le rend dans la langue du compte destinataire. » (WF-ARC-0110) ; « et les lignes sans sous-projet dans un onglet « Hors sous-projet » (WF-INTF-0120) » (annexe B)

**Constat.** WF-INTF-0180 ne fige que les en-têtes de colonnes. Le nom de l'onglet « Hors sous-projet »
est un texte que Waterfall fixe : WF-INTF-0170 le range parmi ce qui se traduit, et WF-ARC-0110 le rend « dans la langue du
compte destinataire » d'un document exporté. Or c'est ce nom qui donne le sous-projet des lignes à l'import
(WF-INTF-0120) : un fichier exporté en anglais puis réimporté par un utilisateur français ne serait pas
reconnu, ce que la Vérif de WF-INTF-0180 exclut (« donne un devis identique, sans avertissement de
format »). Il en va de même de toute valeur fixée qu'un fichier d'échange porterait (type de nature, état
d'une tâche).

**Proposition.** WF-INTF-0180, corps : « les en-têtes de colonnes, les noms d’onglets fixés par Waterfall
— dont l’onglet « Hors sous-projet » — et les valeurs codées des formats Excel de l’ANNEXE B, les noms de
champs des fichiers MS Project, et les dates et nombres du contrat d’API sont fixes ». WF-ARC-0110, corps :
« — fichier engendré, image exportée —, il le rend dans la langue du compte destinataire, hors les formats
d’échange, qui ne dépendent d’aucune langue (WF-INTF-0180) ».

**Statut.** à traiter


---

## C-291 — C-257 a retiré la seule règle qui tenait compte de l'état de la nature : une catégorie active d'une nature désactivée compte-t-elle ?

- **gravité** : mineur
- **emplacement** : §3.4.4, exigence `WF-REF-0010-A` ; §3.3.1, `WF-CYC-0120-A` ; §3.4.5.6, `WF-RIS-0010-A` ; à rapprocher de `WF-REF-0080-A`, `WF-REF-0090-A`
- **citation** : « Les nœuds d’organisation, rôles de ressources, natures de coût, catégories de coût et calendriers ne se suppriment pas » (WF-REF-0010) ; « au moins une catégorie de coût active dont la nature est de type provision pour risques » (WF-CYC-0120) ; « parmi les catégories actives de type provision pour risques » (WF-RIS-0010)

**Constat.** Les natures et les catégories se désactivent chacune pour leur compte, et rien ne dit
ce que la désactivation d'une nature fait à ses catégories. WF-REF-0080 prévoit une cascade pour les
nœuds, rien de tel n'existe pour les natures. Jusqu'à C-257, WF-REF-0030 exigeait qu'« au moins une
nature de type provision active porte toujours une catégorie active » : l'état de la nature
comptait. C-257 a retiré cette phrase. Le prérequis de WF-CYC-0120 et le choix de WF-RIS-0010 ne
lisent plus que l'état de la catégorie.

Prenons une nature de provision désactivée dont la catégorie reste active. Trois questions restent
ouvertes : un projet peut-il être créé, la catégorie est-elle proposée au risque, et la ventilation
du devis affiche-t-elle une nature désactivée ? La même question se pose pour une nature de
main-d'œuvre désactivée dont une catégorie active porte encore un rôle (WF-REF-0090).

**Proposition.** WF-REF-0010, corps, ajouter : « Désactiver une nature de coût désactive ses
catégories ; une catégorie ne peut être réactivée que si sa nature est active. »

WF-REF-0010, Vérif, ajouter : « La désactivation d’une nature désactive ses catégories. La
réactivation d’une catégorie dont la nature est désactivée est refusée. »

**Statut.** à traiter


---

## C-292 — Une valeur égale à un seuil ou à une borne n'a pas de zone ni de niveau

- **gravité** : mineur
- **emplacement** : §3.4.4.4 « FBS-3.4 : Paramètres d’indicateurs » — exigence `WF-REF-0170-A` ; §3.4.4.3, `WF-REF-0160-A` ; à rapprocher de l'entrée « Seuils d'alerte » de l'annexe A et de `WF-PTF-0070-A` (Vérif)
- **citation** : « Un indice au-dessus du seuil de vigilance est nominal, entre les deux seuils il est en vigilance, en dessous du seuil d’alerte il est en alerte. » (WF-REF-0170) ; « Elles délimitent quatre niveaux sur chaque axe. » (WF-REF-0160)

**Constat.** Aucune des deux exigences ne dit à quelle zone, ou à quel niveau, appartient une valeur
égale à un seuil. Le cas n'a rien de théorique. Avec les seuils livrés (0,9 et 0,8, WF-EXP-0020),
l'indice agrégé de l'exemple de WF-PTF-0070 vaut exactement 0,9 (900 / 1 000) : est-il nominal ou
en vigilance ? Avec les bornes livrées (1 %, 5 %, 10 %), une gravité de 50 sur un budget de 1 000
fait 5 % : est-elle au deuxième niveau ou au troisième ?

Le glossaire (« en dessous desquelles un indice […] change de zone ») et le §3.4.4.3 (« le niveau à
partir duquel un risque devient préoccupant ») suggèrent chacun une lecture, mais les exigences ne
tranchent pas. Les tests tirés des Vérif (WF-QUA) n'essaient jamais l'égalité.

**Proposition.** WF-REF-0170, corps : « Un indice supérieur ou égal au seuil de vigilance est
nominal ; inférieur au seuil de vigilance et supérieur ou égal au seuil d’alerte, il est en
vigilance ; inférieur au seuil d’alerte, il est en alerte. »

WF-REF-0170, Vérif, ajouter : « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un
indice de 0,8 en vigilance. »

WF-REF-0160, corps : « Elles délimitent quatre niveaux sur chaque axe ; une valeur égale à une borne
relève du niveau supérieur. »

WF-REF-0160, Vérif, ajouter : « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité
50 sur un projet de budget 1 000 est au troisième niveau. »

**Statut.** à traiter


---

## C-293 — La troisième exception renvoie à WF-PRJ-0070 au lieu de WF-PRJ-0060, et WF-ADM-0110 ne la connaît pas

- **gravité** : mineur
- **emplacement** : §3.4.2.2 « FBS-1.2 : Gestion des rôles d’habilitation », texte d'introduction ; exigence `WF-ADM-0110-A` (corps) ; à rapprocher de `WF-PRJ-0060-A`
- **citation** : « l’inscription d’un chef de projet par un utilisateur qui n’est pas contributeur (WF-PRJ-0070) » (§3.4.2.2) ; « s’il est contributeur de ce projet et, pour une action structurante ou le paramétrage du projet, s’il y est chef de projet (WF-PRJ-0060) » (WF-ADM-0110)

**Constat.** L'inscription d'un chef de projet par un non-contributeur, quand le compte du dernier
chef de projet est désactivé, est écrite dans WF-PRJ-0060, et y était déjà à l'intégration de C-204.
WF-PRJ-0070 est la proposition des contributeurs. Le renvoi posé par C-204 est donc faux depuis
l'origine.

WF-ADM-0110, qui est la règle d'évaluation de toute action, exige par ailleurs la qualité de
contributeur, et celle de chef de projet pour le paramétrage, sans exception. Le service
d'autorisation qui l'implémente refuse donc la seule saisie que WF-PRJ-0060 ouvre à un
non-contributeur.

**Proposition.** §3.4.2.2 : remplacer « (WF-PRJ-0070) » par « (WF-PRJ-0060) ».

WF-ADM-0110, corps, après « s’il y est chef de projet (WF-PRJ-0060) » : « , hors l’inscription d’un
chef de projet que WF-PRJ-0060 ouvre à un non-contributeur lorsque le compte du dernier chef de
projet est désactivé ».

**Statut.** à traiter


---

## C-294 — Le régime « marqué supprimé » vise un livrable et une chronologie que rien ne référence

- **gravité** : mineur
- **emplacement** : §4.4.1, puce « Suppression » ; exigence `WF-DAT-0080-A` (corps) ; à rapprocher de `WF-PRJ-0020-A`, `WF-PRJ-0030-A`, `WF-PLA-0140-A`, `WF-PLA-0170-A`, `WF-CRE-0020-A`
- **citation** : « Un poste, un lot, un livrable ou une chronologie se supprime physiquement tant qu’aucune révision marquée ni aucune ligne de coût ne le référence » (WF-DAT-0080)

**Constat.** Trois écarts entre la règle et ce qui référence réellement ces objets. (1) Une révision
marquée ne référence un poste ou un lot que par le rattachement d’une tâche (WF-PLA-0170). Elle ne
référence jamais un livrable : le squelette crée une feuille par livrable mais « ne crée d’autre lien
entre le lotissement et le planning que ce rattachement » (WF-PRJ-0030), et le rattachement ne vise
qu’un poste ou un lot. Elle ne référence pas non plus une chronologie, objet du régime projet dont ce
sont les inscriptions qui désignent des tâches par leur lignée. (2) Une ligne de coût ne référence
qu’un projet et un sous-projet (WF-CRE-0020), jamais un objet du lotissement : la clause « ni aucune
ligne de coût » est sans objet pour les quatre. (3) La règle ne dit pas ce qu’emporte la suppression
d’un poste qui contient des lots, ou d’un lot qui contient des livrables. Avec des clés étrangères en
refus par défaut (WF-DAT-0090), la base refuse la suppression physique d’un poste qui a encore des lots.
Si l’un de ces lots est marqué supprimé, le poste ne peut pas disparaître non plus. Le développeur cherche
pour le livrable et la chronologie une référence qui n’existe pas, et décide seul du sort des enfants.
Tel quel, WF-PLA-0140 (« peut être supprimée ») est la seule règle effective pour la chronologie.

**Proposition.** WF-DAT-0080, corps, remplacer la phrase citée et la suivante par :

> Un poste ou un lot se supprime physiquement tant qu’aucune tâche d’une révision marquée n’y est
> rattachée ; au-delà, il est marqué supprimé, conservé, et n’est plus proposé à la saisie. La
> suppression d’un poste emporte ses lots, et celle d’un lot ses livrables, chacun selon sa règle ; un
> poste dont un lot est marqué supprimé est marqué supprimé à son tour. Un livrable ou une chronologie se
> supprime physiquement. Un sous-projet ou un risque se supprime physiquement tant qu’aucune révision
> marquée ni, pour un sous-projet, aucune ligne de coût ne le référence ; au-delà, sa suppression est
> refusée, en nommant la raison.

§4.4.1, puce « Suppression » : même partage. Si l’auteur entend qu’une chronologie dont les inscriptions
désignent des tâches d’une révision marquée soit conservée, l’écrire comme telle, avec la référence en
cause.

**Statut.** à traiter


---

## C-295 — « Quel que soit l’état de sa tâche » contredit « de zéro si la tâche est terminée »

- **gravité** : mineur
- **emplacement** : §3.4.5.5 — exigence `WF-RAE-0010-A`, corps ; à rapprocher de `WF-INTF-0100-A`, `WF-INTF-0120-A`, `WF-DEV-0050-A`
- **citation** : « Une ligne dont le montant budgété est nul — ajoutée après la référence — compte pour son montant réestimé quel que soit l’état de sa tâche. »

**Constat.** La phrase, introduite par C-095, servait la tâche non démarrée : une ligne ajoutée
après la référence n’a pas de « grandeurs de la référence » d’où tirer son montant. Mais « quel
que soit l’état » couvre aussi la tâche terminée, pour laquelle la même phrase du corps dit « de
zéro ». Le cas existe : la grille de devis crée des lignes sans restriction d’état (WF-DEV-0050),
et les imports de devis et de reste à engager créent une ligne nouvelle « portée par la tâche
qu’elle désigne » (WF-INTF-0100, WF-INTF-0120), terminée ou non ; seule la modification des lignes
d’une tâche terminée est refusée (WF-RAE-0040). Une telle ligne compte pour zéro ou pour son
montant selon la phrase retenue.

**Proposition.** WF-RAE-0010, corps : « Une ligne dont le montant budgété est nul — ajoutée après
la référence — compte pour son montant réestimé, que sa tâche soit démarrée ou non ; sur une tâche
terminée, elle compte pour zéro comme les autres. » Si l’ajout d’une ligne à une tâche terminée
doit plutôt être refusé, le dire dans WF-DEV-0050 et WF-INTF-0100 / WF-INTF-0120 (rejet au compte
rendu).

**Statut.** à traiter


---

## C-296 — « Montant réestimé » désigne ici la valeur avant inflation, que WF-DEV-0020 appelle autrement

- **gravité** : mineur
- **emplacement** : §3.4.5.4.2 « Grille de devis » — exigence `WF-DEV-0050-A` (corps, Vérif) ; à rapprocher de `WF-DEV-0020-A`
- **citation** : « son montant réestimé aux taux de l’année de référence et, dans une colonne distincte, ce montant corrigé de l’inflation (WF-DEV-0040) » (WF-DEV-0050) ; « affiche un montant corrigé supérieur de 4,04 % à son montant » (WF-DEV-0050, Vérif) ; « Les deux montants sont exprimés inflation comprise » (WF-DEV-0020)

**Constat.** C-154 a fixé que le montant réestimé est « inflation comprise » et que la valeur avant
inflation est « une valeur de lecture » ; WF-DEV-0050 nomme encore « montant réestimé » cette
valeur de lecture, et la Vérif compare le montant corrigé à « son montant », qui est, au sens de
WF-DEV-0020, déjà corrigé. Lu à la lettre, l’exemple applique l’inflation deux fois.

**Proposition.** Corps : « son montant aux taux de l’année de référence, avant inflation, et, dans
une colonne distincte, son montant réestimé, inflation comprise (WF-DEV-0020, WF-DEV-0040) ».
Vérif : « affiche un montant réestimé supérieur de 4,04 % à son montant aux taux de l’année de
référence ».

**Statut.** à traiter


---

## C-297 — Le montant se calcule au taux « de sa catégorie pour l’année de référence », non au taux que la révision conserve

- **gravité** : mineur
- **emplacement** : §3.4.5.4.3 « Gestion des coûts » — exigence `WF-DEV-0030-A`, corps ; à rapprocher de `WF-REV-0030-A`, `WF-REV-0060-A`, `WF-DEV-0010-A`
- **citation** : « Le montant d’une ligne de main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour l’année de référence du chiffrage. »

**Constat.** Une révision conserve ses taux (WF-REV-0030) ; à la création d’une révision d’une
nouvelle année, une catégorie dont la mise à jour est refusée, ou qui n’a pas de taux pour cette
année, est chiffrée au « taux précédent, projeté » (WF-REV-0060). « Le taux horaire de sa
catégorie pour l’année de référence » se lit comme le taux du référentiel pour cette année : il
n’existe pas toujours, et il n’est pas celui que la révision applique quand la mise à jour a été
refusée. WF-DEV-0010 mentionne l’alternative (« ou de taux conservé projeté »), WF-DEV-0030 non.

**Proposition.** « … et du taux horaire que la révision retient pour sa catégorie et son année de
référence — taux du référentiel accepté, ou taux conservé projeté (WF-REV-0030, WF-REV-0060). »

**Statut.** à traiter


---

## C-298 — Qu’un rôle détermine la catégorie d’une ligne de main-d’œuvre n’est dit par aucune exigence

- **gravité** : mineur
- **emplacement** : §3.4.5.4 — exigence `WF-DEV-0020-A`, corps ; à rapprocher de §3.2.5 « La ligne de devis », annexe A « Ligne de devis », `WF-REF-0090-A`
- **citation** : « Lorsque sa catégorie relève d’une nature de main-d’œuvre, elle porte en outre un rôle de ressource et une charge en heures » (WF-DEV-0020) ; « la ligne porte en outre un rôle de ressource, qui détermine cette catégorie » (annexe A)

**Constat.** Le §3.2.5 et le glossaire disent que le rôle détermine la catégorie d’une ligne de
main-d’œuvre ; WF-DEV-0020 donne à la ligne une catégorie et un rôle comme deux attributs
indépendants, et C-026 avait laissé la question ouverte (« il faut dire lequel des deux l’emporte en
cas de désaccord »). Rien n’empêche donc, à l’implémentation, une ligne de catégorie A sous un rôle
de catégorie B, ni ne dit ce que devient la catégorie d’une ligne quand celle du rôle change
(WF-REF-0090 la laisse modifiable).

**Proposition.** WF-DEV-0020, corps : « Lorsque sa catégorie relève d’une nature de main-d’œuvre,
elle porte en outre un rôle de ressource, dont elle tient cette catégorie, et une charge en heures. »
Vérif, ajouter : « La catégorie d’une ligne de main-d’œuvre n’est pas saisissable : c’est celle de
son rôle. »

**Statut.** à traiter


---

## C-299 — Le sous-projet d’une ligne de provision n’est dit nulle part

- **gravité** : mineur
- **emplacement** : §3.4.5.4 — exigence `WF-DEV-0020-A` ; à rapprocher de `WF-RIS-0010-A`, `WF-IND-0020-A`, `WF-RAE-0020-A`
- **citation** : « Elle appartient facultativement à un sous-projet. » (WF-DEV-0020)

**Constat.** Le reste à engager, l’avancement financier et l’écart au budget se calculent par
sous-projet, et la ligne de provision compte au reste à engager (WF-RAE-0010). Elle est créée par
le système (WF-RIS-0010), qui ne dit pas à quel sous-projet elle appartient, ni si l’utilisateur peut
le choisir. C-047 a supposé qu’elle tombe dans « hors sous-projet » ; aucune exigence ne le dit. Selon
le choix, un même risque pèse sur le sous-projet qu’il menace ou sur l’ensemble hors sous-projet, et
le signal de dépassement de WF-RAE-0020 change de sous-projet.

**Proposition.** WF-RIS-0010, ajouter : « La ligne de provision n’appartient à aucun sous-projet :
elle compte dans l’ensemble « hors sous-projet » (WF-RAE-0020). » Ou, si l’auteur préfère : « La
ligne de provision appartient au sous-projet que le risque désigne, facultativement, à sa
déclaration. »

**Statut.** à traiter


---

## C-300 — Le sous-projet d’une ligne peut changer après la référence : budget, valeur planifiée et valeur acquise d’un sous-projet ne disent pas dans quelle révision ils le lisent

- **gravité** : mineur
- **emplacement** : §3.4.5.8 — exigence `WF-IND-0020-A` ; à rapprocher de `WF-INTF-0100-A`, `WF-DEV-0050-A`, `WF-IND-0030-A`, `WF-DEV-0080-A`
- **citation** : « le budget de référence d’un sous-projet est la somme des montants budgétés de ses lignes dans la révision de référence, hors lignes de provision »

**Constat.** Le sous-projet d’une ligne se modifie dans la grille de devis (WF-DEV-0050) et par
l’import de devis (WF-INTF-0100), y compris après la référence. WF-IND-0020 lit l’appartenance du
budget dans la révision de référence ; la valeur acquise (lignes des tâches terminées) et le reste à
engager se lisent naturellement dans la révision courante. Une ligne passée de A à B après la
référence fait alors acquérir à B une valeur qui figure au budget de A : à la fin du projet,
l’avancement physique de A n’atteint pas 100 % et celui de B le dépasse. La somme au projet reste
juste, la ventilation non.

**Proposition.** WF-IND-0020, ajouter : « Le budget de référence, la valeur planifiée et la valeur
acquise d’un sous-projet se calculent sur les lignes qui lui appartiennent dans la révision de
référence ; le reste à engager, sur celles qui lui appartiennent dans la révision courante. » Vérif,
ajouter : « Une ligne passée du sous-projet A au sous-projet B après la référence acquiert sa valeur
dans A, et compte son reste à engager dans B. »

**Statut.** à traiter


---

## C-301 — Après un avenant, la réserve perd la part des risques déjà survenus, dont le coût reste dans la couverture

- **gravité** : mineur
- **emplacement** : §3.4.5.6.2 — exigence `WF-RIS-0050-A` (corps, Motif) ; à rapprocher de `WF-RIS-0040-A`, annexe A « Réserve pour risques »
- **citation** : « La révision de référence conserve, comme réserve pour risques, la somme de ses lignes de provision. » ; « la réévaluation d’un risque, son écart ou sa survenance ne peuvent plus déplacer ce à quoi on les compare »

**Constat.** Refait sur l’exemple de WF-RIS-0050 : réserve 60, risque survenu à 250, écart − 190.
Un avenant produit une nouvelle référence, qui ne porte plus de ligne de provision pour ce risque
survenu : la réserve devient 0, et l’écart de couverture − 250, sans que rien n’ait changé côté
risques. Le glossaire admet que la réserve « ne bouge qu’avec » le budget, mais aucun passage ne dit
qu’un avenant retire de la réserve la part des risques survenus ou écartés avant lui, alors que leur
coût à la survenance reste dans la couverture ; la grille des risques, qui présente les survenus et
les écartés « pour la provision qu’ils portaient dans la révision de référence » (WF-RIS-0040),
les présente alors à zéro. Deux implémentations sont possibles, et le Motif cité laisse croire que
seule une ne déplace pas le repère.

**Proposition.** Trancher dans WF-RIS-0050. Soit : « À chaque nouvelle référence, la réserve
conserve, pour les risques survenus ou écartés avant elle, la provision qu’ils portaient dans la
référence précédente. » Soit : « La réserve est celle de la référence en vigueur : un avenant en
retire la part des risques survenus ou écartés avant lui, et l’écart de couverture le montre ; la
couverture ne compare à la réserve que le coût des risques survenus depuis cette référence. » Ajouter
à la Vérif le cas de l’avenant.

**Statut.** à traiter


---

## C-302 — « Passé ce délai » renvoie à un délai que WF-IHM-0110 ne fixe pas ; le jalon terminé par le Kanban sans la restriction de WF-PLA-0050

- **gravité** : mineur
- **emplacement** : §3.4.5.5.2 « Kanban – Démarrage des tâches » — exigence `WF-RAE-0030-A`, corps ; à rapprocher de `WF-IHM-0110-A`, `WF-PLA-0050-A`
- **citation** : « une tâche démarrée par erreur se corrige en annulant la saisie (WF-IHM-0110), et passé ce délai elle reste démarrée » ; « et un jalon directement à l’état terminé, en saisissant la date de l’événement (WF-PLA-0130) »

**Constat.** WF-IHM-0110 ne fixe aucun délai : l’annulation porte sur les cinquante dernières
modifications de la session et est refusée en cas de modification postérieure du même objet. « Passé
ce délai » ne désigne rien de mesurable. Par ailleurs, le corps laisse le Kanban terminer tout jalon,
alors que WF-PLA-0050 ne le permet que pour un jalon sans ligne (« par la saisie d’un reste à engager
nul sur toutes ses lignes sinon ») ; seule la Vérif de WF-RAE-0030 en porte la trace.

**Proposition.** « … une tâche démarrée par erreur se corrige en annulant la saisie (WF-IHM-0110) ;
lorsque l’annulation n’est plus possible, elle reste démarrée. » Et : « et un jalon qui ne porte
aucune ligne directement à l’état terminé, en saisissant la date de l’événement (WF-PLA-0130) ; pour
un jalon porteur de lignes, le Kanban renvoie à la saisie de son reste à engager (WF-PLA-0050) ».

**Statut.** à traiter


---

## C-303 — Le nom de version d'une révision en cours, qu'elle n'a pas

- **gravité** : mineur
- **emplacement** : §3.6 — exigence `WF-IHM-0020-A` ; à rapprocher de `WF-REV-0020-A` et `WF-REV-0090-A`
- **citation** : « la révision dans laquelle il lit — son nom de version, son état marquée ou en cours, et son caractère de référence le cas échéant » (WF-IHM-0020) ; « Le nom de version et la description sont ceux saisis au marquage » (WF-REV-0090, Vérif)

**Constat.** Le nom de version est demandé au marquage (WF-REV-0020) et saisi à ce moment (WF-REV-0090). Une
révision en cours n'en a pas : WF-IHM-0020 exige d'afficher une donnée qui n'existe pas pour la
révision où se fait toute la saisie, et ne dit pas comment la désigner.

**Proposition.** « […] la révision dans laquelle il lit — pour une révision marquée, son nom de version ; pour la
révision en cours, cette mention et le nom de version de la révision marquée dont elle est issue —,
son caractère de référence le cas échéant, et, lorsqu'un filtre est actif, ce qu'il restreint. »

**Statut.** à traiter


---

## C-304 — WF-IHM-0090 range toute impossibilité en « état » ou « habilitation » : la qualité de contributeur n'est ni l'un ni l'autre

- **gravité** : mineur
- **emplacement** : §3.6 — exigence `WF-IHM-0090-A` (corps et Vérif) ; à rapprocher de `WF-ADM-0110-A` et `WF-PRJ-0060-A`
- **citation** : « une commande que les habilitations de l'utilisateur ne permettent pas n'est pas présentée » (WF-IHM-0090) ; « Un refus de saisie sur un projet dont l'utilisateur n'est pas contributeur nomme cette condition. » (WF-IHM-0090, Vérif) ; « Inscrit comme participant, il l’ouvre et saisit le devis, mais ne marque pas de révision même s’il en porte la permission » (WF-PRJ-0060, Vérif)

**Constat.** Le §3.4.2 distingue deux mécanismes, les rôles d'habilitation et la liste des contributeurs avec
sa qualité. WF-IHM-0090 n'en connaît qu'un : une commande est soit rendue impossible par un état
(présentée indisponible), soit non permise par les habilitations (masquée). Pour un manager porteur
de « consulter tous les projets » mais non contributeur, ou pour un participant porteur de la
permission de marquer (WF-PRJ-0060), le corps ne dit pas si la commande est masquée ou présentée ;
la Vérif suppose qu'elle est présentée puis refusée.

**Proposition.** WF-IHM-0090, corps, ajouter : « Une commande que la qualité de l'utilisateur sur le projet ne
permet pas — non-contributeur, ou participant pour une action réservée aux chefs de projet
(WF-PRJ-0060) — est présentée indisponible, en nommant cette qualité. »

**Statut.** à traiter


---

## C-305 — Le calendrier amorcé « porte des heures travaillées » sans dire lesquelles

- **gravité** : mineur
- **emplacement** : §4.5.2 « Installation initiale », texte et exigence `WF-EXP-0020-A` (corps et Vérif)
- **citation** : « un calendrier actif désigné par défaut portant des heures travaillées » (WF-EXP-0020)

**Constat.** C-189 a fait écrire les valeurs livrées des bornes, des seuils et du délai ; le calendrier
amorcé, lui, n'a pas de valeur. Il commande pourtant toutes les dates des tâches sans rôle
(glossaire, « Calendrier par défaut ») et la Vérif ne peut rien en dire : un calendrier d'une heure
le dimanche satisfait le corps. Comme les bornes, c'est une valeur que l'entreprise ajustera, mais
qu'un test doit pouvoir constater.

**Proposition.** WF-EXP-0020, corps : « un calendrier actif désigné par défaut, livré à huit heures travaillées du
lundi au vendredi et aucune le samedi et le dimanche, » (valeurs à confirmer par l'auteur) ; Vérif,
ajouter : « […] et le calendrier par défaut compte huit heures du lundi au vendredi et aucune le
week-end. » ; §4.5.2, texte : même précision.

**Statut.** à traiter


---

## C-306 — La langue des courriels d'authentification : « celle du compte », que le motif place dans le fournisseur d'identité et WF-INTF-0160 dans Waterfall

- **gravité** : mineur
- **emplacement** : §4.1.3 — exigence `WF-ARC-0110-A` (corps, motif, Vérif) ; §3.1.5 `WF-INTF-0160-A` ; §3.4.2.1 `WF-ADM-0050-A`
- **citation** : « et c'est lui qui connaît la langue du compte » (WF-ARC-0110, motif) ; « ce choix est conservé dans son compte » (WF-INTF-0160) ; « À la première connexion d'un utilisateur, la langue retenue est celle que son navigateur demande » (WF-INTF-0160)

**Constat.** La langue d'un utilisateur est un attribut de son compte Waterfall (WF-ADM-0050, WF-INTF-0160).
Le motif de WF-ARC-0110 dit que c'est le fournisseur d'identité qui « connaît la langue du compte » :
rien ne la lui transmet, et un changement de langue dans Waterfall n'atteindrait pas les courriels.
Et avant sa première connexion — cas du lien de fixation d'un compte local tout juste créé
(WF-ADM-0140) —, le compte n'a pas encore de langue.

**Proposition.** WF-ARC-0110, corps : « Les courriels d'authentification — lien de mot de passe, réinitialisation
— partent du fournisseur d'identité, dans la langue que Waterfall lui transmet pour le compte : celle
que l'utilisateur a choisie (WF-INTF-0160) ou, avant sa première connexion, la langue par défaut de
l'installation. » Motif : « […] et Waterfall lui transmet la langue de chaque compte par son API
d'administration (TFX-08). »

**Statut.** à traiter


---

## Relevés non retenus

Ces relevés ne changent pas ce qui se construit ni ce qui se teste : une exigence tranche déjà, ou le
point ne touche que la prose, un renvoi, la matrice de traçabilité ou le vocabulaire. Ils sont reportés
jusqu'à ce qu'un lot s'y heurte. Les identifiants sont ceux des fichiers de relecture, non numérotés
dans la suite C-nnn.

| Relevé | Titre | Pourquoi il n'est pas retenu |
|---|---|---|
| A-07 | Résidu de C-237 : le délai de paiement « nul pour la main-d'œuvre » | résidu de C-237 dans le §3.2.5 et un Motif ; le corps de WF-DEV-0020 tranche déjà |
| A-08 | Résidu de C-224 : la tâche non démarrée « garde son montant budgété » | résidu de C-224 dans la prose du §3.2.5 ; WF-RAE-0010 tranche déjà |
| A-09 | C-257 : le cycle de la plateforme « ne se parcourt qu'une fois », alors qu'une désactivation peut l'y ramener | prose du §3.3 ; WF-CYC-0120 s'évalue à chaque création, ce que nul ne lira autrement |
| A-11 | Le modèle inscrit « une tâche » au suivi temps/temps, l'exigence et le glossaire un jalon | prose du §3.2.4 ; WF-PLA-0060 et le glossaire réservent sans ambiguïté le suivi aux jalons |
| A-16 | « Trois systèmes externes » : l'annuaire, le fournisseur d'identité externe et la messagerie manquent à la frontière | périmètre du §3.1 ; la figure 18 et le tableau 8 décrivent déjà ces systèmes |
| A-17 | Le tableau des flux avec les acteurs omet le paramétrage du projet et les sauvegardes | tableau de flux descriptif ; les exigences portent les usages |
| A-18 | « Cinq dimensions » : le §3.6 Principes d'interface n'y est pas | décompte d'une phrase d'introduction |
| A-19 | Le trait pointillé est réservé aux objets d'ancrage, que les figures relient le plus souvent en trait plein | convention graphique des figures, sans effet sur le modèle |
| A-20 | Trois entrées du glossaire qui disent autre chose que les exigences | glossaire en retard sur des exigences qui tranchent |
| B-07 | « Ne se parcourt qu'une fois » : WF-REF-0030 accepte désormais de refaire passer la plateforme sous son minimum | même point qu'A-09 |
| B-09 | Deux chemins de saisie pour trois types de nature : « Sinon » couvre la provision pour risques | prose du §3.2.5 ; WF-DEV-0020 dit qu'une ligne de provision ne se saisit pas |
| B-11 | La courbe du budget d'une offre compte les provisions, et WF-PTF-0080 lui fait dire le contraire | lecture d'une courbe de portefeuille pour une offre, cas marginal |
| B-15 | La règle d'union n'est pas tenue : aucune WF-PTF ne cite PBS-3.2, et la ligne FBS-1.4 n'a pas PBS-5.1 | matrice de traçabilité FBS–PBS, sans effet sur ce qui se construit |
| B-16 | « Désactivable (WF-REF-0130) » : la désactivation relève de WF-REF-0010 | renvoi inexact dans la prose du §4.4.1 |
| B-17 | Les deux exemples d'une fonction « insérée au milieu » ne le sont pas, contrairement à FBS-4.5.3 | exemple de numérotation de l'arborescence |
| B-20 | Le Motif justifie un rapport entre provisions survenues et écartées que la vue ne présente pas | Motif en retard sur le corps, qui tranche |
| B-21 | Le glossaire calcule le taux de charge sur la « charge planifiée », WF-PTF-0060 sur le reste à engager | glossaire en retard sur WF-PTF-0060, qui tranche |
| C-08 | WF-REV-0050 renvoie à WF-PLA-0130 pour des motifs de refus qu’elle ne porte plus | renvoi périmé et cas limite de l'horizon à la fusion |
| C-09 | WF-PLA-0160 cite PBS-2.2, que la matrice n’alloue pas à sa fonction | matrice de traçabilité FBS–PBS |
| C-10 | La récapitulative terminée qui tombe à durée nulle n’a pas de règle | cas limite ; « conserve son état » s'applique déjà |
| C-11 | Le Motif de WF-PLA-0040 range les provisions parmi les lignes qui suivent le sort de la phase ; le corps les en exclut | Motif en retard sur le corps, qui tranche |
| C-12 | Le §3.2.4 inscrit une tâche au suivi temps/temps, que WF-PLA-0060 et le glossaire réservent aux jalons | même point qu'A-11 |
| D-08 | Deux phrases en retard sur C-224 et C-095 | prose et Motif en retard sur WF-RAE-0010, qui tranche |
| D-09 | Le délai de paiement est « nul pour la main-d’œuvre », « saisissable sur toute ligne », et absent d’une ligne de provision | même point qu'A-07 |
| D-17 | « Le devis en cours » : terme sans définition, à côté du « devis courant » du glossaire | « devis en cours » se comprend comme le devis courant |
| D-18 | « C’est-à-dire avant le début de la première tâche » : faux par sous-projet et quand cette tâche ne porte rien | incise explicative ; la règle de calcul est non ambiguë |
| D-19 | Le dernier point vient de « la révision en cours », reliquat de C-165 | WF-IND-0010 dit déjà d'où vient le point au jour courant |
| D-29 | L’exclusion d’une ligne de coût est rangée parmi les « actions irréversibles », alors qu’elle se réintègre | qualificatif « irréversible » ; le comportement de l'annulation est fixé |
| D-30 | Le journal compte des lignes « ignorées », les exigences en « rejettent » | vocabulaire « ignorées » / « rejetées » d'un compte rendu |
| D-31 | Deux signalements de la tranche manquent à la liste de l’échelle commune | l'échelle commune pose déjà que la couleur ne porte jamais seule une information |
| D-32 | La ligne FBS-4.8.1 à FBS-4.8.5 n’a pas PBS-1.3, que WF-IND-0130 cite | matrice de traçabilité FBS–PBS |
| E-11 | L'écran d'état présente des valeurs qu'aucune métrique ne porte, et deux qu'WF-ADM-0130 ne liste pas (C-244 non propagé) | sources de l'écran d'état ; WF-ADM-0130 les énumère, rien ne s'y oppose |
| E-12 | Le tableau 7 et les champs PBS s'écartent de la règle d'allocation du §4.2.2 en quatre points | matrice de traçabilité FBS–PBS |
| E-13 | Résidus de C-190 : « indicateurs de la révision en cours » là où le cache porte les indicateurs au jour courant | résidus de C-190 dans la prose ; WF-DAT-0130 tranche |
| E-14 | §4.4.1 : la désactivation renvoie à WF-REF-0130, les régimes citent des références qui n'existent pas, l'intégrité oublie l'exception du journal | renvois et prose du §4.4.1 |
| E-15 | Volumétrie : un décompte faux, trois nombres qui dépendent d'une hypothèse non dite, deux renvois au §4.6.2 qu'il ne porte pas | volumétrie d'architecture, ordres de grandeur sans test qui en dépende |
| E-16 | §3.5.2 : la désignation seule fait passer à En cours, « Clôturer » nomme la sortie « Terminer », la revue oublie les risques | prose du flux de travail §3.5.2 |
| E-17 | « La révision suivante n'est créée qu'à la demande, ou par le premier import » : quatre autres saisies la créent | prose de la figure 20 |
| E-20 | WF-IHM-0110 dit « irréversibles » des actions qui se défont, et « session » sans dire laquelle | qualificatif « irréversible » et « session », sans effet sur le comportement fixé |
| E-21 | L'échelle de signalement commune énumère sept signalements ; le §3 en définit au moins quatre autres | même point que D-31 |
| E-22 | « Synchronisation de l'annuaire » pour la lecture des comptes du fournisseur d'identité, et le flux vers l'annuaire décrit deux fois | vocabulaire « synchronisation » / « lecture des comptes » |
| E-26 | La règle « Vérifiée en recette » n'est pas appliquée à WF-INTF-0060, et un test « non exécuté » n'a pas de statut | mention de recette d'un Vérif, sans effet sur ce qui se construit |
| E-28 | Le §4.5.4 compte Redis et PostgreSQL comme les seuls arrêts du travail ; le fournisseur d'identité l'arrête aussi | phrase de commentaire d'un tableau qui dit déjà l'arrêt |
