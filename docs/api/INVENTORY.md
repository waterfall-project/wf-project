# Inventaire des endpoints

Établi depuis `openapi.yaml` par `tools/inventory.py`, et régénérable par
`make inventory`. La colonne « Exigences » ne donne que celles que l'opération
cite dans ses propres mots, résumé ou description ; les paramètres, les corps et
les réponses en citent d'autres, comptées dans la couverture ci-dessous mais pas
dans le tableau.

**162 opérations sur 126 chemins, dans 13 familles.**
Le contrat cite **184 des 209 exigences** de la spécification.

## Système, métriques et traitements de fond

`paths/system.yaml` — 8 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/health` | Sonde de vivacité | — |
| GET | `/installation` | Ce que le front doit savoir de l'installation avant toute session | WF-INTF-0160 |
| GET | `/health/ready` | Sonde de préparation | WF-EXP-0040 |
| GET | `/metrics` | Métriques au format Prometheus | WF-ADM-0130, WF-OBS-0010 |
| GET | `/system/status` | Écran d'état du système | WF-ADM-0130, WF-ADM-0170, WF-OBS-0030 |
| GET | `/tasks` | Tâches de fond de l'appelant | WF-ARC-0090, WF-IHM-0080 |
| GET | `/tasks/{task_id}` | Avancement d'une tâche de fond | WF-ARC-0090, WF-IHM-0080 |
| GET | `/tasks/{task_id}/result` | Résultat d'une tâche de fond | WF-DAT-0120 |

## Session, compte courant et préférences

`paths/session.yaml` — 13 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/session/providers` | Fournisseurs d'authentification actifs | WF-ADM-0180, WF-ARC-0030 |
| GET | `/session` | Session courante | WF-ADM-0110, WF-INTF-0160, WF-SEC-0020 |
| POST | `/session` | Ouvrir une session par compte local ou par annuaire | WF-ADM-0140, WF-ADM-0180, WF-SEC-0020 |
| DELETE | `/session` | Se déconnecter | WF-SEC-0020 |
| GET | `/session/oidc/start` | Démarrer une authentification OIDC | WF-ADM-0180 |
| GET | `/session/oidc/callback` | Retour du fournisseur d'identité | WF-ADM-0180, WF-SEC-0020 |
| POST | `/session/password-reset` | Demander un lien de réinitialisation | WF-ADM-0140, WF-ARC-0110, WF-EXP-0020 |
| POST | `/session/password-reset/confirm` | Fixer un mot de passe avec un lien de réinitialisation | WF-ADM-0140 |
| GET | `/me` | Mon compte et mes préférences | WF-ADM-0040, WF-ADM-0050 |
| PATCH | `/me/preferences` | Modifier mes préférences d'affichage | WF-ADM-0040, WF-INTF-0160 |
| PUT | `/me/password` | Changer mon mot de passe | WF-ADM-0140 |
| PUT | `/me/avatar` | Déposer ou remplacer mon avatar | WF-ADM-0080 |
| DELETE | `/me/avatar` | Retirer mon avatar | WF-ADM-0080 |

## Comptes, rôles et permissions

`paths/access.yaml` — 16 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/users` | Comptes utilisateurs | WF-ADM-0030, WF-ADM-0050, WF-ADM-0060, WF-IHM-0060 |
| POST | `/users` | Créer un compte local | WF-ADM-0050, WF-ADM-0070, WF-ADM-0140, WF-ADM-0180 |
| GET | `/users/{user_id}` | Un compte utilisateur | WF-ADM-0030, WF-ADM-0050 |
| PATCH | `/users/{user_id}` | Modifier un compte | WF-ADM-0050, WF-ADM-0060 |
| PUT | `/users/{user_id}/activation` | Désactiver ou réactiver un compte | WF-ADM-0060, WF-ADM-0120, WF-SEC-0020 |
| PUT | `/users/{user_id}/access-roles` | Attribuer les rôles d'habilitation d'un compte | WF-ADM-0090, WF-SEC-0020 |
| POST | `/users/{user_id}/password-link` | Obtenir le lien de fixation du mot de passe d'un compte | WF-ADM-0100, WF-ADM-0140, WF-CMP-0030, WF-EXP-0020, WF-SEC-0030 |
| GET | `/users/{user_id}/avatar` | Avatar d'un compte | WF-ADM-0080 |
| POST | `/directory-syncs` | Resynchroniser les comptes depuis l'annuaire | WF-ADM-0070, WF-ARC-0090 |
| GET | `/directory-syncs/latest` | Résultat de la dernière synchronisation | WF-ADM-0070 |
| GET | `/permissions` | Catalogue des permissions | WF-ADM-0100 |
| GET | `/access-roles` | Rôles d'habilitation | WF-ADM-0010, WF-ADM-0090, WF-IHM-0060 |
| POST | `/access-roles` | Composer un rôle d'habilitation | WF-ADM-0020 |
| GET | `/access-roles/{access_role_id}` | Un rôle d'habilitation | WF-ADM-0090, WF-ADM-0100 |
| PATCH | `/access-roles/{access_role_id}` | Modifier un rôle | WF-ADM-0090 |
| DELETE | `/access-roles/{access_role_id}` | Supprimer un rôle | WF-ADM-0090, WF-ADM-0120 |

## Sauvegarde et restauration

`paths/platform.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/backups` | Sauvegardes | WF-ADM-0150 |
| POST | `/backups` | Déclencher une sauvegarde | WF-ADM-0150, WF-ARC-0090 |
| GET | `/backups/{backup_id}` | Une sauvegarde | WF-ADM-0150 |
| PATCH | `/backups/{backup_id}` | Marquer une sauvegarde à conserver | WF-ADM-0170 |
| GET | `/backups/{backup_id}/content` | Copier une sauvegarde hors de la plateforme | WF-ADM-0150 |
| GET | `/backup-schedule` | Planification et rétention des sauvegardes | WF-ADM-0170 |
| PUT | `/backup-schedule` | Régler la planification et la rétention | WF-ADM-0100, WF-ADM-0170, WF-EXP-0050, WF-OBS-0030 |
| GET | `/external-backup-locations` | Emplacements externes des sauvegardes | WF-ADM-0100, WF-ADM-0170 |
| POST | `/external-backup-locations/{location_name}/test` | Éprouver un emplacement externe des sauvegardes | WF-ADM-0100, WF-ADM-0170, WF-ARC-0110, WF-OBS-0030 |
| POST | `/restores` | Restaurer la plateforme | WF-ADM-0160, WF-DAT-0130 |

## Journal d'audit

`paths/audit.yaml` — 1 opération

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/audit-events` | Journal d'audit | WF-ADM-0100, WF-ADM-0110, WF-ADM-0160, WF-SEC-0030 |

## Référentiel commun

`paths/reference.yaml` — 29 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/reference/readiness` | Référentiel minimal exigé pour créer un projet | WF-CYC-0120 |
| GET | `/reference/settings` | Devise, langue par défaut, matrice de risques, seuils et délai de revue | WF-REF-0140, WF-REF-0160, WF-REF-0170, WF-REF-0180 |
| PATCH | `/reference/settings` | Régler les paramètres communs | WF-REF-0140, WF-REF-0170 |
| GET | `/reference/org-nodes` | Arbre d'organisation | WF-REF-0070 |
| POST | `/reference/org-nodes` | Créer un nœud d'organisation | WF-REF-0070 |
| PATCH | `/reference/org-nodes/{org_node_id}` | Modifier un nœud d'organisation | WF-REF-0070, WF-REF-0130 |
| PUT | `/reference/org-nodes/{org_node_id}/activation` | Désactiver ou réactiver un nœud | WF-REF-0010, WF-REF-0080 |
| GET | `/reference/resource-roles` | Rôles de ressources | WF-ADM-0100, WF-DEV-0020, WF-REF-0090, WF-REF-0100, WF-REF-0150 |
| POST | `/reference/resource-roles` | Créer un rôle de ressource | WF-REF-0090, WF-REF-0100 |
| PATCH | `/reference/resource-roles/{resource_role_id}` | Modifier un rôle de ressource | WF-REF-0090, WF-REF-0130 |
| PUT | `/reference/resource-roles/{resource_role_id}/activation` | Désactiver ou réactiver un rôle de ressource | WF-REF-0010, WF-REF-0020 |
| GET | `/reference/duration-units` | Constantes de conversion des unités de durée | WF-PLA-0160 |
| PUT | `/reference/duration-units` | Régler les constantes de conversion des unités de durée | WF-ADM-0100, WF-PLA-0160, WF-REF-0130 |
| GET | `/reference/calendars` | Calendriers | WF-REF-0110, WF-REF-0120 |
| POST | `/reference/calendars` | Créer un calendrier | WF-REF-0110 |
| PATCH | `/reference/calendars/{calendar_id}` | Modifier un calendrier | WF-REF-0110, WF-REF-0130 |
| PUT | `/reference/calendars/{calendar_id}/default` | Désigner le calendrier par défaut | WF-PLA-0010, WF-REF-0120 |
| PUT | `/reference/calendars/{calendar_id}/activation` | Désactiver ou réactiver un calendrier | WF-REF-0120 |
| GET | `/reference/cost-types` | Natures de coût | WF-REF-0030, WF-REF-0150 |
| POST | `/reference/cost-types` | Créer une nature de coût | WF-REF-0030 |
| PATCH | `/reference/cost-types/{cost_type_id}` | Modifier une nature de coût | WF-REF-0030 |
| PUT | `/reference/cost-types/{cost_type_id}/activation` | Désactiver ou réactiver une nature de coût | WF-REF-0010, WF-REF-0020 |
| GET | `/reference/cost-categories` | Catégories de coût | WF-ADM-0100, WF-DEV-0020, WF-REF-0040, WF-REF-0150 |
| POST | `/reference/cost-categories` | Créer une catégorie de coût | WF-REF-0040 |
| PATCH | `/reference/cost-categories/{cost_category_id}` | Modifier une catégorie de coût | WF-REF-0040, WF-REF-0130 |
| PUT | `/reference/cost-categories/{cost_category_id}/activation` | Désactiver ou réactiver une catégorie de coût | WF-REF-0010, WF-REF-0020 |
| GET | `/reference/hourly-rates` | Grille des taux horaires | WF-ADM-0100, WF-IHM-0130, WF-REF-0050, WF-REF-0060, WF-REF-0150 |
| GET | `/reference/cost-categories/{cost_category_id}/hourly-rates` | Taux horaires annuels d'une catégorie | WF-REF-0050, WF-REF-0060 |
| PUT | `/reference/cost-categories/{cost_category_id}/hourly-rates/{year}` | Fixer le taux horaire d'une année | WF-REF-0050, WF-REF-0130 |

## Projets, cycle de vie, lotissement, contributeurs

`paths/projects.yaml` — 19 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects` | Projets | WF-ADM-0110, WF-IHM-0120, WF-IHM-0130, WF-PRJ-0060, WF-PTF-0030 |
| POST | `/projects` | Créer un projet | WF-CYC-0010, WF-CYC-0120, WF-PRJ-0060 |
| GET | `/projects/{project_id}` | Un projet | WF-CYC-0010, WF-PRJ-0010, WF-PRJ-0080 |
| PATCH | `/projects/{project_id}` | Modifier les paramètres d'un projet | WF-ADM-0110, WF-CYC-0100, WF-PRJ-0040, WF-PRJ-0060, WF-PRJ-0090 |
| GET | `/projects/{project_id}/state-transitions` | Historique daté des états | WF-CYC-0090, WF-CYC-0130, WF-PTF-0050 |
| GET | `/projects/{project_id}/next-state` | Prochain état, déclencheur et conditions restantes | WF-CYC-0020, WF-CYC-0050 |
| POST | `/projects/{project_id}/exit` | Sortie manuelle du cycle de vie | WF-CYC-0060, WF-CYC-0080, WF-CYC-0090, WF-CYC-0130, WF-PRJ-0060, WF-SEC-0030 |
| GET | `/projects/{project_id}/work-breakdown` | Lotissement | WF-PRJ-0020 |
| PUT | `/projects/{project_id}/work-breakdown` | Saisir le lotissement | WF-PLA-0130, WF-PRJ-0020 |
| GET | `/projects/{project_id}/subprojects` | Sous-projets | WF-PRJ-0050 |
| POST | `/projects/{project_id}/subprojects` | Créer un sous-projet | WF-PRJ-0050 |
| PATCH | `/projects/{project_id}/subprojects/{subproject_id}` | Modifier un sous-projet | WF-PRJ-0050 |
| DELETE | `/projects/{project_id}/subprojects/{subproject_id}` | Supprimer un sous-projet | WF-DAT-0080, WF-PRJ-0050 |
| GET | `/projects/{project_id}/contributors` | Contributeurs du projet | WF-IHM-0110, WF-PRJ-0060 |
| PUT | `/projects/{project_id}/contributors` | Inscrire ou retirer des contributeurs | WF-ADM-0110, WF-IHM-0110, WF-PRJ-0060 |
| GET | `/projects/{project_id}/contributors/suggestions` | Contributeurs proposés | WF-PRJ-0070 |
| GET | `/projects/{project_id}/timelines` | Chronologies du projet | WF-PLA-0140 |
| POST | `/projects/{project_id}/timelines` | Créer une chronologie | WF-PLA-0140 |
| DELETE | `/projects/{project_id}/timelines/{timeline_id}` | Supprimer une chronologie | WF-PLA-0140 |

## Révisions, structures et arbre commun

`paths/revisions.yaml` — 28 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/revisions` | Historique des révisions | WF-REV-0070, WF-REV-0090 |
| POST | `/projects/{project_id}/revisions` | Ouvrir la révision en cours | WF-DAT-0010, WF-REV-0010, WF-REV-0060 |
| GET | `/projects/{project_id}/revisions/{revision_id}` | Une révision et son instantané | WF-REV-0030, WF-REV-0090 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}` | Abandonner la révision en cours | WF-DAT-0010, WF-DAT-0020, WF-REV-0010 |
| POST | `/projects/{project_id}/revisions/{revision_id}/mark` | Marquer la révision | WF-ARC-0090, WF-DAT-0040, WF-REV-0020, WF-SEC-0030 |
| PUT | `/projects/{project_id}/reference-revision` | Désigner la révision de référence | WF-CYC-0030, WF-REV-0040, WF-SEC-0030 |
| GET | `/projects/{project_id}/revisions/{revision_id}/rate-update` | Écart de taux proposé, catégorie par catégorie | WF-REV-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/rate-update` | Appliquer la mise à jour des taux | WF-REV-0060 |
| GET | `/projects/{project_id}/revisions/comparison` | Comparer deux révisions marquées | WF-DAT-0030, WF-REV-0080 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures` | Structures de coûts de la révision | WF-REV-0100 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures` | Créer un différentiel ou un devis de risque | WF-REV-0100 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge` | Fusionner un différentiel dans la structure principale | WF-ARC-0090, WF-PLA-0010, WF-REV-0050, WF-SEC-0030 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | Arbre commun de la structure | WF-DEV-0020, WF-DEV-0050, WF-IHM-0030, WF-PLA-0080, WF-PLA-0090, WF-PLA-0110, WF-PLA-0140 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | Créer une tâche ou une ligne de devis | WF-CYC-0100, WF-DAT-0020, WF-DEV-0020, WF-PLA-0010, WF-RAE-0050, WF-RIS-0010 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}` | Supprimer un nœud | WF-DAT-0090, WF-DEV-0040, WF-IHM-0110, WF-PLA-0020, WF-PLA-0070, WF-PLA-0100 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies` | Ce dont dépend une valeur calculée | WF-IHM-0030, WF-PLA-0040 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task` | Modifier la facette temps d'une tâche | WF-IHM-0040, WF-PLA-0020, WF-PLA-0040, WF-PLA-0050, WF-PLA-0150, WF-PLA-0160 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line` | Modifier la facette argent d'une ligne de devis | WF-DEV-0020, WF-DEV-0030, WF-DEV-0040, WF-IHM-0040, WF-PLA-0010, WF-RIS-0010 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors` | Remplacer les prédécesseurs d'une tâche | WF-PLA-0030, WF-PLA-0040, WF-PLA-0160 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress` | Démarrer ou terminer une tâche | WF-IND-0030, WF-PLA-0040, WF-RAE-0030 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining` | Réestimer une ligne | WF-PLA-0130, WF-RAE-0030, WF-RAE-0040 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/tracking` | Inscrire ou retirer une tâche des suivis | WF-PLA-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move` | Déplacer des nœuds dans l'arbre | WF-DEV-0040, WF-PLA-0020, WF-PLA-0040, WF-PLA-0130 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview` | Aperçu d'un collage depuis un tableur | WF-DEV-0050, WF-IHM-0050, WF-PLA-0080 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste` | Appliquer un collage | WF-IHM-0050, WF-IHM-0110 |
| POST | `/projects/{project_id}/revisions/{revision_id}/undo` | Annuler la dernière modification | WF-IHM-0110, WF-RIS-0020 |
| POST | `/projects/{project_id}/revisions/{revision_id}/redo` | Rétablir la dernière annulation | WF-IHM-0110 |
| POST | `/projects/{project_id}/revisions/{revision_id}/skeleton` | Engendrer le squelette de planning depuis le lotissement | WF-PLA-0130, WF-PRJ-0030 |

## Indicateurs de devis, de reste à engager et de projet

`paths/analysis.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/estimate-indicators` | Indicateurs de devis | WF-DEV-0010, WF-DEV-0060, WF-IND-0010 |
| GET | `/projects/{project_id}/estimate-indicators/missing-rates` | Taux horaires manquants pour le calcul | WF-CYC-0120, WF-DEV-0010, WF-REV-0060 |
| GET | `/projects/{project_id}/workload` | Plan de charge du projet | WF-DEV-0070 |
| GET | `/projects/{project_id}/remaining-indicators` | Indicateurs de reste à engager | WF-IND-0020, WF-RAE-0020 |
| GET | `/projects/{project_id}/remaining-indicators/startable-tasks` | Tâches du Kanban, par état | WF-PLA-0040, WF-RAE-0030 |
| GET | `/projects/{project_id}/indicators` | Indicateurs de valeur acquise | WF-DAT-0040, WF-IND-0010, WF-IND-0080 |
| GET | `/projects/{project_id}/indicators/milestone-tracking` | Diagramme temps/temps | WF-IND-0090 |
| GET | `/projects/{project_id}/indicators/cost-curve` | Courbe de coûts cumulés | WF-DAT-0040, WF-IND-0010, WF-IND-0100 |
| GET | `/projects/{project_id}/indicators/earned-value-curves` | Courbes de valeur acquise | WF-DAT-0040, WF-IND-0010, WF-IND-0110 |
| GET | `/projects/{project_id}/indicators/index-history` | Évolution des indices | WF-DAT-0040, WF-IND-0020, WF-IND-0130, WF-REF-0170 |

## Risques et provisions

`paths/risks.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/risks` | Registre des risques | WF-IHM-0130, WF-RIS-0030, WF-RIS-0040 |
| POST | `/projects/{project_id}/risks` | Déclarer un risque | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0030, WF-RIS-0050 |
| GET | `/projects/{project_id}/risks/{risk_id}` | Un risque | WF-RIS-0010, WF-RIS-0020, WF-RIS-0030 |
| PATCH | `/projects/{project_id}/risks/{risk_id}` | Modifier un risque | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0030 |
| DELETE | `/projects/{project_id}/risks/{risk_id}` | Supprimer un risque | WF-IHM-0110, WF-RIS-0020 |
| GET | `/projects/{project_id}/risks/{risk_id}/reviews` | Historique des réexamens | WF-RIS-0010, WF-RIS-0030 |
| POST | `/projects/{project_id}/risks/{risk_id}/reviews` | Réexaminer un risque | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0050 |
| POST | `/projects/{project_id}/risks/{risk_id}/occurrence` | Déclarer un risque survenu | WF-ARC-0090, WF-IHM-0110, WF-RIS-0020, WF-RIS-0050, WF-RIS-0060, WF-SEC-0030 |
| GET | `/projects/{project_id}/risks/coverage` | Couverture des risques | WF-RAE-0020, WF-RIS-0050 |
| GET | `/projects/{project_id}/risks/matrix` | Matrice de risques du projet | WF-IHM-0070, WF-REF-0160, WF-RIS-0030, WF-RIS-0040 |

## Coûts réels

`paths/costs.yaml` — 3 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/actual-costs` | Coûts réels du projet | WF-CRE-0010, WF-CRE-0040 |
| PUT | `/projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope` | Exclure une ligne du périmètre suivi, ou la réintégrer | WF-ADM-0100, WF-CRE-0030, WF-SEC-0030 |
| GET | `/projects/{project_id}/cost-imports` | Journal des imports de coûts réels | WF-CRE-0050 |

## Échanges par fichier

`paths/exchanges.yaml` — 7 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| POST | `/file-uploads` | Déposer un fichier | WF-ADM-0160, WF-DAT-0120 |
| GET | `/projects/{project_id}/imports` | Imports du projet | WF-ARC-0100, WF-INTF-0080 |
| POST | `/projects/{project_id}/imports` | Ouvrir un import et lancer son analyse | WF-ARC-0090, WF-ARC-0100, WF-INTF-0040, WF-INTF-0070, WF-INTF-0080, WF-INTF-0090, WF-INTF-0100, WF-INTF-0120, WF-INTF-0140 |
| GET | `/projects/{project_id}/imports/{import_id}` | Compte rendu d'un import | WF-ARC-0110, WF-INTF-0040, WF-INTF-0080, WF-PLA-0130 |
| DELETE | `/projects/{project_id}/imports/{import_id}` | Abandonner un import | WF-DAT-0120, WF-INTF-0080 |
| POST | `/projects/{project_id}/imports/{import_id}/apply` | Appliquer un import | WF-ARC-0100, WF-CRE-0030, WF-DAT-0110, WF-INTF-0080, WF-INTF-0140 |
| POST | `/projects/{project_id}/exports` | Demander un export | WF-DAT-0120, WF-INTF-0050, WF-INTF-0060, WF-INTF-0110, WF-INTF-0130, WF-INTF-0180, WF-PLA-0120 |

## Portefeuille

`paths/portfolio.yaml` — 8 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/portfolio/projects` | Liste des projets du portefeuille | WF-IHM-0130, WF-PTF-0040 |
| GET | `/portfolio/value` | Carnet, pipeline et réalisé | WF-PTF-0020, WF-PTF-0050 |
| GET | `/portfolio/workload` | Plan de charge agrégé | WF-PTF-0060 |
| GET | `/portfolio/performance` | Indices, projections, répartition par zone et évolution trimestrielle | WF-PTF-0010, WF-PTF-0020, WF-PTF-0070 |
| GET | `/portfolio/cost-structure` | Structure des coûts du portefeuille | WF-PTF-0080 |
| GET | `/portfolio/risks` | Risques du portefeuille | WF-PTF-0090, WF-RIS-0050 |
| GET | `/portfolio/cost-curve` | Courbe en S du portefeuille | WF-IND-0100, WF-PTF-0100 |
| GET | `/portfolio/pilot-health` | Santé du pilotage | WF-PTF-0110, WF-REF-0180 |

## Exigences que le contrat ne cite pas

25 sur 209. Aucune n'est un oubli : ce sont celles qui n'ont pas de
surface d'interface, et il vaut mieux qu'elles n'en aient pas.

| Domaine | Exigences | Pourquoi aucune surface d'API |
|---|---|---|
| ARC | WF-ARC-0010, WF-ARC-0040, WF-ARC-0050, WF-ARC-0070, WF-ARC-0080 | Choix d'architecture interne : noyau unique, rôles des composants de données, empaquetage, autorité du serveur, absence d'état. Ils se vérifient sur le dépôt et le déploiement. |
| CMP | WF-CMP-0010 | Compatibilité des navigateurs et largeurs d'affichage : propriété du front. |
| DAT | WF-DAT-0050, WF-DAT-0140 | Partitionnement et migrations : propriétés du schéma, invisibles du contrat. |
| EXP | WF-EXP-0010, WF-EXP-0030 | Exploitation : environnements, amorçage, mise à jour, perte maximale. Aucune n'est une opération d'API. |
| IHM | WF-IHM-0010, WF-IHM-0100, WF-IHM-0140 | Invariants d'interface : navigation, accessibilité, aide en ligne. Ils vivent dans le front. |
| INTF | WF-INTF-0010, WF-INTF-0020, WF-INTF-0030, WF-INTF-0170 | Les trois usages d'acteurs décrivent le contenu des rôles prédéfinis, servi par le catalogue des permissions ; la règle de traduction vit dans le front. |
| QUA | WF-QUA-0010, WF-QUA-0020, WF-QUA-0030, WF-QUA-0040, WF-QUA-0050, WF-QUA-0060, WF-QUA-0070, WF-QUA-0080 | Chaîne de vérification : tests, analyse statique, jeu de données, mesures. Elle s'exerce sur le contrat, elle n'y figure pas. |
