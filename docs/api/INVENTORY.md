# Inventaire des endpoints

Établi depuis `openapi.yaml` par `tools/inventory.py`, et régénérable par
`make inventory`. La colonne « Exigences » ne donne que celles que l'opération
cite dans ses propres mots, résumé ou description ; les paramètres, les corps et
les réponses en citent d'autres, comptées dans la couverture ci-dessous mais pas
dans le tableau.

**169 opérations sur 131 chemins, dans 13 familles.**
Le contrat cite **190 des 212 exigences** de la spécification.

## Système, métriques et traitements de fond

`paths/system.yaml` — 8 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/health` | Liveness probe, and the maintenance of a restore | WF-ADM-0160 |
| GET | `/installation` | What the front must know about the installation before any session | WF-EXP-0020, WF-INTF-0160 |
| GET | `/health/ready` | Readiness probe | WF-EXP-0040 |
| GET | `/metrics` | Metrics in Prometheus format | WF-ADM-0130, WF-OBS-0010, WF-SEC-0010 |
| GET | `/system/status` | System status screen | WF-ADM-0100, WF-ADM-0130, WF-ADM-0170, WF-EXP-0030, WF-OBS-0030 |
| GET | `/tasks` | The caller's background tasks | WF-ARC-0090, WF-IHM-0080 |
| GET | `/tasks/{task_id}` | Progress of a background task | WF-ARC-0090, WF-IHM-0080 |
| GET | `/tasks/{task_id}/result` | Result of a background task | WF-ARC-0040, WF-ARC-0090, WF-DAT-0120 |

## Compte courant, préférences et avatar

`paths/me.yaml` — 5 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/me` | My account and my preferences | WF-ADM-0040, WF-ADM-0050, WF-ADM-0060, WF-ADM-0110, WF-ADM-0180, WF-ARC-0030, WF-IHM-0090, WF-SEC-0020 |
| DELETE | `/me/sessions` | Sign me out | WF-ARC-0030, WF-SEC-0020 |
| PATCH | `/me/preferences` | Edit my display preferences | WF-ADM-0040, WF-IHM-0060, WF-INTF-0160, WF-PLA-0140 |
| PUT | `/me/avatar` | Upload or replace my avatar | WF-ADM-0080, WF-EXP-0020 |
| DELETE | `/me/avatar` | Remove my avatar | WF-ADM-0080 |

## Comptes, rôles et permissions

`paths/access.yaml` — 20 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/users` | User accounts | WF-ADM-0030, WF-ADM-0050, WF-ADM-0060, WF-ADM-0120, WF-DAT-0070, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130 |
| POST | `/users` | Create a local account | WF-ADM-0050, WF-ADM-0070, WF-ADM-0090, WF-ADM-0100, WF-ADM-0140, WF-ADM-0180 |
| GET | `/users/{user_id}` | A user account | WF-ADM-0030, WF-ADM-0050 |
| PATCH | `/users/{user_id}` | Modify an account | WF-ADM-0050, WF-ADM-0060, WF-ADM-0070 |
| PUT | `/users/{user_id}/activation` | Deactivate or reactivate an account | WF-ADM-0060, WF-ADM-0120, WF-SEC-0020 |
| POST | `/users/{user_id}/anonymization` | Anonymise a deactivated account | WF-ADM-0060, WF-ADM-0070, WF-ADM-0100, WF-SEC-0030 |
| PUT | `/users/{user_id}/access-roles` | Assign the access roles of an account | WF-ADM-0090, WF-ADM-0120, WF-SEC-0020 |
| POST | `/users/{user_id}/password-link` | Get the password setup link of an account | WF-ADM-0100, WF-ADM-0140, WF-CMP-0030, WF-EXP-0020, WF-SEC-0030 |
| POST | `/users/{user_id}/invitation` | Resend the password setup email of an account | WF-ADM-0100, WF-ADM-0140, WF-CMP-0030, WF-EXP-0040, WF-SEC-0030 |
| GET | `/users/{user_id}/avatar` | Avatar of an account | WF-ADM-0080 |
| POST | `/identity-syncs` | Read the identity provider's accounts | WF-ADM-0050, WF-ADM-0070, WF-ADM-0180, WF-ARC-0090 |
| GET | `/identity-syncs/latest` | Report of the latest account read | WF-ADM-0070 |
| GET | `/identity-sync-schedule` | Periodicity of the account read | WF-ADM-0070, WF-ADM-0100, WF-ADM-0170 |
| PUT | `/identity-sync-schedule` | Set the periodicity of the account read | WF-ADM-0070, WF-ADM-0100 |
| GET | `/permissions` | Permission catalogue | WF-ADM-0100 |
| GET | `/access-roles` | Access roles | WF-ADM-0010, WF-ADM-0060, WF-ADM-0090, WF-ADM-0100, WF-ADM-0110, WF-DAT-0070, WF-IHM-0060, WF-IHM-0130 |
| POST | `/access-roles` | Compose an access role | WF-ADM-0020, WF-ADM-0100 |
| GET | `/access-roles/{access_role_id}` | An access role | WF-ADM-0090, WF-ADM-0100, WF-ADM-0110 |
| PATCH | `/access-roles/{access_role_id}` | Modify a role | WF-ADM-0090, WF-ADM-0100, WF-ADM-0110 |
| DELETE | `/access-roles/{access_role_id}` | Delete a role | WF-ADM-0090, WF-ADM-0100, WF-ADM-0110, WF-ADM-0120, WF-DAT-0080 |

## Sauvegarde et restauration

`paths/platform.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/backups` | Backups | WF-ADM-0100, WF-ADM-0150, WF-ADM-0170, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130 |
| POST | `/backups` | Start a backup | WF-ADM-0100, WF-ADM-0150, WF-ARC-0090, WF-SEC-0030 |
| GET | `/backups/{backup_id}` | A backup | WF-ADM-0100, WF-ADM-0150, WF-IHM-0090 |
| PATCH | `/backups/{backup_id}` | Mark a backup to keep | WF-ADM-0100, WF-ADM-0170, WF-IHM-0090, WF-IHM-0110 |
| GET | `/backups/{backup_id}/content` | Copy a backup outside the platform | WF-ADM-0100, WF-ADM-0150, WF-IHM-0090 |
| GET | `/backup-schedule` | Scheduling and retention of the backups | WF-ADM-0100, WF-ADM-0170, WF-EXP-0050 |
| PUT | `/backup-schedule` | Set the scheduling and the retention | WF-ADM-0100, WF-ADM-0160, WF-ADM-0170, WF-EXP-0040, WF-EXP-0050, WF-OBS-0030 |
| GET | `/external-backup-locations` | External backup locations | WF-ADM-0100, WF-ADM-0170 |
| POST | `/external-backup-locations/{location_name}/test` | Test an external backup location | WF-ADM-0100, WF-ADM-0170, WF-ARC-0110, WF-OBS-0030 |
| POST | `/restores` | Restore the platform | WF-ADM-0150, WF-ADM-0160, WF-ARC-0090, WF-DAT-0120, WF-DAT-0130, WF-IHM-0090, WF-SEC-0030 |

## Journal d'audit

`paths/audit.yaml` — 2 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/audit-events` | Audit log | WF-ADM-0100, WF-ADM-0110, WF-ADM-0160, WF-ADM-0190, WF-IHM-0060, WF-IHM-0130, WF-SEC-0030 |
| GET | `/audit-events/facets` | Authors and projects of the audit log | WF-ADM-0060, WF-ADM-0100, WF-ADM-0190, WF-IHM-0130, WF-SEC-0030 |

## Référentiel commun

`paths/reference.yaml` — 31 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/reference/readiness` | Minimum reference data required to create a project | WF-CYC-0120, WF-EXP-0020, WF-RIS-0010 |
| GET | `/reference/settings` | Currency, company name, language, risk matrix, thresholds and review interval | WF-EXP-0020, WF-REF-0140, WF-REF-0160, WF-REF-0170, WF-REF-0180 |
| PATCH | `/reference/settings` | Set the common settings | WF-ADM-0100, WF-EXP-0020, WF-INTF-0160, WF-REF-0140, WF-REF-0160, WF-REF-0170, WF-REF-0180 |
| GET | `/reference/org-nodes` | Organisation tree | WF-ADM-0100, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-REF-0070, WF-REF-0080, WF-REF-0150 |
| POST | `/reference/org-nodes` | Create an organisation node | WF-REF-0070, WF-REF-0080 |
| PATCH | `/reference/org-nodes/{org_node_id}` | Modify an organisation node | WF-REF-0070, WF-REF-0080, WF-REF-0130 |
| PUT | `/reference/org-nodes/{org_node_id}/activation` | Deactivate or reactivate a node | WF-ADM-0100, WF-REF-0010, WF-REF-0080 |
| GET | `/reference/resource-roles` | Resource roles | WF-ADM-0100, WF-DEV-0020, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-REF-0080, WF-REF-0090, WF-REF-0100, WF-REF-0150 |
| POST | `/reference/resource-roles` | Create a resource role | WF-REF-0030, WF-REF-0040, WF-REF-0080, WF-REF-0090, WF-REF-0100 |
| PATCH | `/reference/resource-roles/{resource_role_id}` | Modify a resource role | WF-REF-0030, WF-REF-0040, WF-REF-0080, WF-REF-0090, WF-REF-0130 |
| PUT | `/reference/resource-roles/{resource_role_id}/activation` | Deactivate or reactivate a resource role | WF-ADM-0100, WF-REF-0010, WF-REF-0020, WF-REF-0080 |
| GET | `/reference/duration-units` | Conversion constants of the duration units | WF-PLA-0160 |
| PUT | `/reference/duration-units` | Set the conversion constants of the duration units | WF-ADM-0100, WF-PLA-0160, WF-REF-0130 |
| GET | `/reference/calendars` | Calendars | WF-ADM-0100, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-REF-0110, WF-REF-0120, WF-REF-0150 |
| POST | `/reference/calendars` | Create a calendar | WF-REF-0110 |
| PATCH | `/reference/calendars/{calendar_id}` | Modify a calendar | WF-REF-0110, WF-REF-0130 |
| PUT | `/reference/calendars/{calendar_id}/default` | Designate the default calendar | WF-ADM-0100, WF-PLA-0010, WF-REF-0120 |
| PUT | `/reference/calendars/{calendar_id}/activation` | Deactivate or reactivate a calendar | WF-ADM-0100, WF-REF-0010, WF-REF-0120 |
| GET | `/reference/cost-types` | Cost types | WF-ADM-0100, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-REF-0030, WF-REF-0150 |
| POST | `/reference/cost-types` | Create a cost type | WF-REF-0030 |
| PATCH | `/reference/cost-types/{cost_type_id}` | Modify a cost type | WF-REF-0030, WF-REF-0130 |
| PUT | `/reference/cost-types/{cost_type_id}/activation` | Deactivate or reactivate a cost type | WF-ADM-0100, WF-CYC-0120, WF-REF-0010, WF-REF-0020, WF-REF-0030, WF-RIS-0010 |
| GET | `/reference/cost-categories` | Cost categories | WF-ADM-0100, WF-DEV-0020, WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-REF-0030, WF-REF-0040, WF-REF-0050, WF-REF-0090, WF-REF-0150 |
| POST | `/reference/cost-categories` | Create a cost category | WF-REF-0040 |
| PATCH | `/reference/cost-categories/{cost_category_id}` | Modify a cost category | WF-REF-0030, WF-REF-0040, WF-REF-0050, WF-REF-0130 |
| PUT | `/reference/cost-categories/{cost_category_id}/activation` | Deactivate or reactivate a cost category | WF-ADM-0100, WF-CYC-0120, WF-REF-0010, WF-REF-0020, WF-REF-0030, WF-RIS-0010 |
| GET | `/reference/hourly-rates` | Hourly rate grid | WF-ADM-0100, WF-ADM-0110, WF-IHM-0060, WF-IHM-0130, WF-REF-0050, WF-REF-0060, WF-REF-0150 |
| GET | `/reference/cost-categories/{cost_category_id}/hourly-rates` | Annual hourly rates of a category | WF-ADM-0100, WF-ADM-0110, WF-DEV-0010, WF-REF-0050, WF-REF-0060 |
| PUT | `/reference/cost-categories/{cost_category_id}/hourly-rates/{year}` | Set the hourly rate of a year | WF-REF-0030, WF-REF-0050, WF-REF-0130 |
| GET | `/reference/actual-cost-mapping` | Mapping of the actual cost extraction | WF-ADM-0100, WF-CRE-0010, WF-REF-0190 |
| PUT | `/reference/actual-cost-mapping` | Set the mapping of the actual cost extraction | WF-ADM-0100, WF-INTF-0080, WF-REF-0190 |

## Projets, cycle de vie, lotissement, contributeurs

`paths/projects.yaml` — 19 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects` | Projects | WF-ADM-0110, WF-IHM-0120, WF-IHM-0130, WF-PRJ-0060, WF-PTF-0030 |
| POST | `/projects` | Create a project | WF-CYC-0010, WF-CYC-0120, WF-PRJ-0060 |
| GET | `/projects/{project_id}` | A project | WF-CYC-0010, WF-PRJ-0010, WF-PRJ-0080 |
| PATCH | `/projects/{project_id}` | Edit the settings of a project | WF-ADM-0110, WF-CYC-0100, WF-PRJ-0040, WF-PRJ-0060, WF-PRJ-0080, WF-PRJ-0090 |
| GET | `/projects/{project_id}/state-transitions` | Dated history of the states | WF-CYC-0090, WF-CYC-0130, WF-PTF-0050 |
| GET | `/projects/{project_id}/next-state` | Next state, trigger and remaining conditions | WF-CYC-0020, WF-CYC-0030, WF-CYC-0050, WF-CYC-0060, WF-PRJ-0010 |
| POST | `/projects/{project_id}/exit` | Manual exit from the lifecycle | WF-ARC-0090, WF-CYC-0060, WF-CYC-0080, WF-CYC-0090, WF-CYC-0130, WF-IHM-0110, WF-IND-0010, WF-PRJ-0060, WF-REV-0020, WF-SEC-0030 |
| GET | `/projects/{project_id}/work-breakdown` | Work breakdown | WF-IHM-0060, WF-IHM-0130, WF-PLA-0170, WF-PRJ-0020 |
| PUT | `/projects/{project_id}/work-breakdown` | Enter the work breakdown | WF-DAT-0080, WF-IHM-0080, WF-IHM-0090, WF-IHM-0110, WF-PLA-0170, WF-PRJ-0020 |
| GET | `/projects/{project_id}/subprojects` | Subprojects | WF-IHM-0060, WF-IHM-0090, WF-IHM-0130, WF-PRJ-0050 |
| POST | `/projects/{project_id}/subprojects` | Create a subproject | WF-CRE-0020, WF-PRJ-0050, WF-PRJ-0060 |
| PATCH | `/projects/{project_id}/subprojects/{subproject_id}` | Edit a subproject | WF-CRE-0020, WF-DAT-0060, WF-INTF-0140, WF-PRJ-0050 |
| DELETE | `/projects/{project_id}/subprojects/{subproject_id}` | Delete a subproject | WF-DAT-0070, WF-DAT-0080, WF-IHM-0090, WF-IHM-0110, WF-PRJ-0050, WF-PRJ-0060, WF-RIS-0010 |
| GET | `/projects/{project_id}/contributors` | Contributors of the project | WF-ADM-0060, WF-IHM-0060, WF-IHM-0110, WF-IHM-0130, WF-PRJ-0060 |
| PUT | `/projects/{project_id}/contributors` | Register or remove contributors | WF-ADM-0060, WF-ADM-0110, WF-IHM-0110, WF-PRJ-0060 |
| GET | `/projects/{project_id}/contributors/suggestions` | Suggested contributors | WF-ADM-0060, WF-PRJ-0070 |
| GET | `/projects/{project_id}/timelines` | Timelines of the project | WF-PLA-0140 |
| POST | `/projects/{project_id}/timelines` | Create a timeline | WF-CYC-0100, WF-PLA-0060, WF-PLA-0140 |
| DELETE | `/projects/{project_id}/timelines/{timeline_id}` | Delete a timeline | WF-CYC-0100, WF-DAT-0080, WF-PLA-0140 |

## Révisions, structures et arbre commun

`paths/revisions.yaml` — 31 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/revisions` | Revision history | WF-IHM-0020, WF-REV-0070, WF-REV-0090 |
| POST | `/projects/{project_id}/revisions` | Open the current revision | WF-CYC-0020, WF-DAT-0010, WF-DAT-0020, WF-PLA-0170, WF-REV-0010, WF-REV-0050, WF-REV-0060, WF-REV-0090, WF-REV-0100, WF-RIS-0060 |
| GET | `/projects/{project_id}/revisions/{revision_id}` | A revision and its snapshot | WF-REV-0030, WF-REV-0090 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}` | Abandon the current revision | WF-CYC-0020, WF-DAT-0010, WF-DAT-0020, WF-IHM-0110, WF-REV-0010, WF-RIS-0020, WF-RIS-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/mark` | Mark the revision | WF-ARC-0090, WF-DAT-0040, WF-DEV-0010, WF-IHM-0080, WF-REV-0020, WF-SEC-0030 |
| PUT | `/projects/{project_id}/reference-revision` | Designate the reference revision | WF-CYC-0030, WF-IHM-0110, WF-REV-0040, WF-SEC-0030 |
| GET | `/projects/{project_id}/revisions/{revision_id}/rate-update` | Proposed rate difference, category by category | WF-REV-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/rate-update` | Apply the rate update | WF-DAT-0020, WF-REF-0130, WF-REV-0060 |
| GET | `/projects/{project_id}/revisions/comparison` | Compare two marked revisions | WF-DAT-0030, WF-IHM-0130, WF-REV-0060, WF-REV-0080 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures` | Cost structures of the revision | WF-DEV-0050, WF-IHM-0090, WF-RAE-0040, WF-REV-0100 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures` | Open a differential | WF-REV-0050, WF-REV-0100, WF-RIS-0030 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}` | Modify the planning start date and the label of a structure | WF-PLA-0010, WF-PLA-0020, WF-REV-0100 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge` | Preliminary report of the merge of a differential | WF-PLA-0030, WF-PLA-0150, WF-PLA-0170, WF-REV-0010, WF-REV-0050 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge` | Merge a differential into the main structure | WF-ARC-0090, WF-DEV-0020, WF-IHM-0080, WF-PLA-0010, WF-PLA-0030, WF-PLA-0150, WF-PLA-0170, WF-REV-0010, WF-REV-0020, WF-REV-0050, WF-REV-0060, WF-SEC-0030 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | Common tree of the structure | WF-DEV-0020, WF-DEV-0050, WF-IHM-0030, WF-IHM-0060, WF-IHM-0130, WF-PLA-0080, WF-PLA-0090, WF-PLA-0110, WF-PLA-0140, WF-PLA-0170, WF-REV-0100, WF-RIS-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | Create a task or an estimate line | WF-CYC-0100, WF-DAT-0020, WF-DEV-0020, WF-DEV-0050, WF-PLA-0010, WF-PLA-0020, WF-PLA-0040, WF-PLA-0050, WF-PLA-0150, WF-PLA-0170, WF-RAE-0040, WF-RAE-0050, WF-REV-0050, WF-RIS-0010 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rows/{row_number}` | The node that carries a row number | WF-ADM-0110, WF-PLA-0080 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}` | Delete a node | WF-DAT-0090, WF-DEV-0040, WF-IHM-0110, WF-PLA-0020, WF-PLA-0040, WF-PLA-0070, WF-PLA-0100, WF-PLA-0160, WF-PLA-0170, WF-RAE-0030, WF-RAE-0040, WF-REV-0050, WF-RIS-0010 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies` | What a computed value depends on | WF-IHM-0030, WF-PLA-0040 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task` | Modify the time facet of a task | WF-IHM-0040, WF-PLA-0010, WF-PLA-0020, WF-PLA-0040, WF-PLA-0050, WF-PLA-0150, WF-PLA-0160, WF-PLA-0170 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line` | Modify the money facet of an estimate line | WF-DEV-0020, WF-DEV-0030, WF-DEV-0040, WF-DEV-0050, WF-IHM-0040, WF-PLA-0010, WF-PRJ-0050, WF-RAE-0040, WF-REV-0050, WF-RIS-0010 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors` | Replace the predecessors of a task | WF-PLA-0030, WF-PLA-0040, WF-PLA-0150, WF-PLA-0160 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress` | Start, complete or reopen a task | WF-IHM-0030, WF-IND-0030, WF-PLA-0040, WF-PLA-0130, WF-RAE-0030 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining` | Re-estimate a line | WF-PLA-0130, WF-RAE-0030, WF-RAE-0040 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/tracking` | Register a task for tracking or remove it | WF-PLA-0060 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move` | Move nodes in the tree | WF-DEV-0040, WF-PLA-0020, WF-PLA-0030, WF-PLA-0040, WF-PLA-0050, WF-PLA-0150, WF-PLA-0170 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview` | Preview of a paste from a spreadsheet | WF-DEV-0050, WF-IHM-0050, WF-PLA-0080, WF-PRJ-0050, WF-RAE-0040 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste` | Apply a paste | WF-IHM-0050, WF-IHM-0110 |
| POST | `/projects/{project_id}/revisions/{revision_id}/undo` | Undo the last change | WF-CRE-0030, WF-IHM-0110, WF-RIS-0020 |
| POST | `/projects/{project_id}/revisions/{revision_id}/redo` | Redo the last undo | WF-IHM-0110 |
| POST | `/projects/{project_id}/revisions/{revision_id}/skeleton` | Generate the planning skeleton from the work breakdown | WF-CYC-0100, WF-DAT-0020, WF-IHM-0110, WF-PLA-0170, WF-PRJ-0030 |

## Indicateurs de devis, de reste à engager et de projet

`paths/analysis.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/estimate-indicators` | Estimate indicators | WF-DEV-0010, WF-DEV-0060, WF-IND-0010, WF-IND-0020, WF-PLA-0170 |
| GET | `/projects/{project_id}/estimate-indicators/missing-rates` | Hourly rates missing for the computation | WF-CYC-0120, WF-DEV-0010, WF-REV-0060 |
| GET | `/projects/{project_id}/workload` | Project workload | WF-DEV-0070 |
| GET | `/projects/{project_id}/remaining-indicators` | Remaining-to-commit indicators | WF-IND-0020, WF-RAE-0020 |
| GET | `/projects/{project_id}/remaining-indicators/startable-tasks` | Kanban tasks, by state | WF-IHM-0090, WF-PLA-0040, WF-RAE-0030 |
| GET | `/projects/{project_id}/indicators` | Earned value indicators | WF-DAT-0040, WF-IND-0010, WF-IND-0080 |
| GET | `/projects/{project_id}/indicators/milestone-tracking` | Time/time diagram | WF-IND-0010, WF-IND-0020, WF-IND-0090 |
| GET | `/projects/{project_id}/indicators/cost-curve` | Cumulative cost curve | WF-DAT-0040, WF-IND-0010, WF-IND-0020, WF-IND-0100, WF-RAE-0040 |
| GET | `/projects/{project_id}/indicators/earned-value-curves` | Earned value curves | WF-DAT-0040, WF-IND-0010, WF-IND-0110 |
| GET | `/projects/{project_id}/indicators/index-history` | Evolution of the indices | WF-DAT-0040, WF-IND-0010, WF-IND-0020, WF-IND-0130, WF-REF-0170 |

## Risques et provisions

`paths/risks.yaml` — 12 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/risks` | Risk register | WF-IHM-0060, WF-IHM-0130, WF-RIS-0020, WF-RIS-0030, WF-RIS-0040 |
| POST | `/projects/{project_id}/risks` | Declare a risk | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0030, WF-RIS-0050 |
| GET | `/projects/{project_id}/risks/{risk_id}` | One risk | WF-RIS-0010, WF-RIS-0020, WF-RIS-0030 |
| PATCH | `/projects/{project_id}/risks/{risk_id}` | Edit the identity of a risk | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0040 |
| DELETE | `/projects/{project_id}/risks/{risk_id}` | Delete a risk | WF-IHM-0110, WF-RIS-0020 |
| PUT | `/projects/{project_id}/risks/{risk_id}/provision` | Change the provision of a risk | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020 |
| GET | `/projects/{project_id}/risks/{risk_id}/reviews` | History of the reviews | WF-PLA-0150, WF-RIS-0010, WF-RIS-0030 |
| POST | `/projects/{project_id}/risks/{risk_id}/reviews` | Review a risk | WF-IHM-0110, WF-RIS-0010, WF-RIS-0020, WF-RIS-0050 |
| GET | `/projects/{project_id}/risks/{risk_id}/occurrence` | Preliminary report of the occurrence of a risk | WF-IHM-0110, WF-RIS-0060 |
| POST | `/projects/{project_id}/risks/{risk_id}/occurrence` | Declare a risk occurred | WF-ARC-0090, WF-DEV-0020, WF-IHM-0110, WF-PLA-0170, WF-RIS-0010, WF-RIS-0020, WF-RIS-0050, WF-RIS-0060, WF-SEC-0030 |
| GET | `/projects/{project_id}/risks/coverage` | Risk coverage | WF-RAE-0020, WF-RIS-0050 |
| GET | `/projects/{project_id}/risks/matrix` | Risk matrix of the project | WF-IHM-0070, WF-REF-0160, WF-RIS-0030, WF-RIS-0040 |

## Coûts réels

`paths/costs.yaml` — 3 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/projects/{project_id}/actual-costs` | Actual costs of the project | WF-CRE-0010, WF-CRE-0040 |
| PUT | `/projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope` | Exclude a line from the tracked scope, or reinstate it | WF-ADM-0100, WF-CRE-0030, WF-SEC-0030 |
| GET | `/projects/{project_id}/cost-imports` | Log of the actual cost imports | WF-CRE-0050 |

## Échanges par fichier

`paths/exchanges.yaml` — 10 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| POST | `/file-uploads` | Upload a file | WF-ARC-0100, WF-DAT-0120 |
| POST | `/chunked-uploads` | Open the chunked upload of a backup | WF-ADM-0160, WF-DAT-0120 |
| PUT | `/chunked-uploads/{chunked_upload_id}/parts/{part_number}` | Upload a chunk | WF-ADM-0160 |
| POST | `/chunked-uploads/{chunked_upload_id}/completion` | Complete the chunked upload | WF-ADM-0160 |
| GET | `/projects/{project_id}/imports` | Imports of the project | WF-ARC-0100, WF-INTF-0080 |
| POST | `/projects/{project_id}/imports` | Open an import and start its analysis | WF-ARC-0090, WF-ARC-0100, WF-CRE-0050, WF-DAT-0120, WF-INTF-0040, WF-INTF-0070, WF-INTF-0080, WF-INTF-0090, WF-INTF-0100, WF-INTF-0120, WF-INTF-0140, WF-PLA-0020, WF-PLA-0150, WF-PLA-0170, WF-PRJ-0050, WF-REF-0190 |
| GET | `/projects/{project_id}/imports/{import_id}` | Report of an import | WF-ARC-0110, WF-CRE-0020, WF-IHM-0090, WF-INTF-0040, WF-INTF-0080, WF-INTF-0100, WF-INTF-0120, WF-INTF-0140, WF-PLA-0020, WF-REF-0190 |
| DELETE | `/projects/{project_id}/imports/{import_id}` | Abandon an import | WF-ARC-0100, WF-DAT-0120, WF-INTF-0080 |
| POST | `/projects/{project_id}/imports/{import_id}/apply` | Apply an import | WF-ARC-0100, WF-CRE-0030, WF-DAT-0110, WF-INTF-0080, WF-INTF-0100, WF-INTF-0140, WF-REF-0190 |
| POST | `/projects/{project_id}/exports` | Request an export | WF-ARC-0040, WF-CYC-0110, WF-DAT-0120, WF-INTF-0050, WF-INTF-0060, WF-INTF-0110, WF-INTF-0120, WF-INTF-0130, WF-INTF-0180, WF-PLA-0020, WF-PLA-0120 |

## Portefeuille

`paths/portfolio.yaml` — 8 opérations

| Méthode | Chemin | Opération | Exigences citées |
|---|---|---|---|
| GET | `/portfolio/projects` | List of the portfolio projects | WF-IHM-0130, WF-PTF-0040 |
| GET | `/portfolio/value` | Order book, pipeline and delivered | WF-PTF-0020, WF-PTF-0050 |
| GET | `/portfolio/workload` | Aggregated workload | WF-PTF-0010, WF-PTF-0060 |
| GET | `/portfolio/performance` | Indices, projections, distribution by zone and quarterly evolution | WF-PTF-0010, WF-PTF-0020, WF-PTF-0070 |
| GET | `/portfolio/cost-structure` | Portfolio cost structure | WF-PTF-0010, WF-PTF-0080 |
| GET | `/portfolio/risks` | Portfolio risks | WF-PTF-0020, WF-PTF-0090, WF-RIS-0050 |
| GET | `/portfolio/cost-curve` | Portfolio S-curve | WF-IND-0100, WF-PTF-0010, WF-PTF-0100 |
| GET | `/portfolio/pilot-health` | Project control health | WF-PTF-0010, WF-PTF-0110, WF-REF-0180 |

## Exigences que le contrat ne cite pas

22 sur 212. Aucune n'est un oubli : ce sont celles qui n'ont pas de
surface d'interface, et il vaut mieux qu'elles n'en aient pas.

| Domaine | Exigences | Pourquoi aucune surface d'API |
|---|---|---|
| ARC | WF-ARC-0010, WF-ARC-0070, WF-ARC-0080 | Choix d'architecture interne : noyau unique, rôles des composants de données, empaquetage, autorité du serveur, absence d'état. Ils se vérifient sur le dépôt et le déploiement. |
| CMP | WF-CMP-0010 | Compatibilité des navigateurs et largeurs d'affichage : propriété du front. |
| DAT | WF-DAT-0050, WF-DAT-0140 | Partitionnement et migrations : propriétés du schéma, invisibles du contrat. |
| EXP | WF-EXP-0010 | Exploitation : environnements, amorçage, mise à jour, perte maximale. Aucune n'est une opération d'API. |
| IHM | WF-IHM-0010, WF-IHM-0100, WF-IHM-0140 | Invariants d'interface : navigation, accessibilité, aide en ligne. Ils vivent dans le front. |
| INTF | WF-INTF-0010, WF-INTF-0020, WF-INTF-0030, WF-INTF-0170 | Les trois usages d'acteurs décrivent le contenu des rôles prédéfinis, servi par le catalogue des permissions ; la règle de traduction vit dans le front. |
| QUA | WF-QUA-0010, WF-QUA-0020, WF-QUA-0030, WF-QUA-0040, WF-QUA-0050, WF-QUA-0060, WF-QUA-0070, WF-QUA-0080 | Chaîne de vérification : tests, analyse statique, jeu de données, mesures. Elle s'exerce sur le contrat, elle n'y figure pas. |
