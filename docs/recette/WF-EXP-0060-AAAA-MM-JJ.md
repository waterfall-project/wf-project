# Procès-verbal de recette — WF-EXP-0060-A, test de restauration périodique

> **Gabarit, non rempli.** Pour tenir la recette, copier ce fichier sous le nom
> `WF-EXP-0060-<date de la recette>.md` (par exemple `WF-EXP-0060-2026-12-03.md`), retirer cet
> encadré, puis remplir chaque champ « Constaté » au fil de la procédure. Un fichier par exigence,
> nommé par son identifiant et daté (EP-13, « Conception », « La chaîne et la publication ») : le
> rapport de couverture le lit à la place d'un test, et le tient pour périmé s'il est antérieur à
> la version précédente de l'exigence (WF-QUA-0010).

## L'exigence

`WF-EXP-0060-A` (§4.6.4, F0), Vérif : « Vérifiée en recette. Un test de restauration mensuel est
exécuté, et son résultat daté est consultable. Le test échoue et le signale si le nombre de projets
restaurés diffère de celui de la sauvegarde. L'environnement du test n'est joignable par aucun
utilisateur et n'existe plus après le test. »

La recette se tient sur un cluster Kubernetes installé par le chart, la préproduction du tableau 11
de la spécification (décision de l'auteur du 2026-11-18). Elle constate l'exécution **planifiée**
du test : aucune commande ne le lance à la main. Le fonctionnement du test lui-même est décrit dans
[le test de restauration](../exploitation/test-de-restauration.md).

## Les conditions

| | Constaté |
|---|---|
| Date de la recette | |
| Tenue par | |
| Version de Waterfall (écran d'état) | |
| Version du chart, étiquette des images | |
| Cluster : distribution, version de Kubernetes, plugin réseau | |
| Espace de noms et nom de la release | |
| Valeurs `restoreTest` en vigueur (`helm get values --all`) | |

Le plugin réseau doit appliquer les politiques réseau (NetworkPolicy) : le noter ci-dessus.

Dans les commandes qui suivent, `NS` est l'espace de noms de l'installation et `RELEASE` le préfixe
de ses objets (`waterfall` pour la release `waterfall`) ; `psql` désigne
`kubectl -n NS exec statefulset/RELEASE-postgres -- psql --username=postgres --dbname=waterfall`,
ou le client de l'exploitant si PostgreSQL est fourni.

## La procédure

### 1. Ce que le chart a posé

```
kubectl -n NS get networkpolicy,role,rolebinding,configmap \
  -l app.kubernetes.io/component=restore-test
kubectl -n NS get cronjob RELEASE-scheduler \
  -o jsonpath='{.spec.jobTemplate.spec.template.spec.serviceAccountName}'
kubectl -n NS get deployment RELEASE-worker -o jsonpath='{.spec.template.spec.serviceAccountName}'
kubectl -n NS get role RELEASE-restore-test -o yaml
kubectl -n NS get rolebinding RELEASE-restore-test -o jsonpath='{.subjects[*].name}'
kubectl -n NS get networkpolicy RELEASE-restore-test -o jsonpath='{.spec.egress}'
```

Attendu : la politique réseau, le rôle, sa liaison et le ConfigMap `RELEASE-restore-test` existent ;
la commande planifiée tourne sous le compte `RELEASE-scheduler`, seul sujet de la liaison ; le
worker n'a pas de compte de service propre (sortie vide : le compte `default`, sans droit) ; le rôle
ne permet que `create` sur `jobs` ; chaque règle de sortie de la politique réseau porte un `to` —
le DNS du cluster, le PostgreSQL et le stockage de la production —, aucune n'en est dépourvue.

Constaté :

### 2. La sauvegarde planifiée vérifiée que le test restaurera

Laisser passer l'heure de la sauvegarde planifiée (01:00, temps universel, par défaut), puis :

```
psql -c "SELECT taken_at, origin, verification FROM backup ORDER BY taken_at DESC LIMIT 3"
```

Attendu : une sauvegarde `scheduled`, `passed`.

Constaté :

### 3. Le dépôt planifié du test

Dans les cinq minutes qui suivent la sauvegarde planifiée vérifiée (la première d'une installation,
puis tous les `restoreTest.interval` secondes) :

```
psql -c "SELECT id, status, requested_by, submitted_at, result FROM background_task \
  WHERE kind = 'restore_test' ORDER BY submitted_at DESC LIMIT 3"
kubectl -n NS logs -l app.kubernetes.io/component=scheduler --tail=-1 | grep restore_test.job_
kubectl -n NS get jobs,pods -l app.kubernetes.io/component=restore-test -o wide
```

Attendu : une tâche `restore_test` inscrite par la plateforme (`requested_by` nul), réussie, son
résultat nommant le Job `RELEASE-restore-test-<8 caractères>` ; le journal de la commande planifiée
dit `restore_test.job_made` pour ce Job (tant que Kubernetes garde le Job de la CronJob) ; ce Job et
son pod existent, le pod en cours d'exécution.

Constaté (heure du dépôt, nom du Job) :

### 4. Pendant le test : personne ne joint l'environnement

Le pod en cours d'exécution, son API démarrée (`kubectl -n NS logs <pod> -c api`) :

```
kubectl -n NS get pod <pod> -o jsonpath='{.status.podIP}'
kubectl -n NS get services -o wide
kubectl -n NS run probe --image=<image waterfall de l'installation> --restart=Never --rm \
  --attach --command -- python3 -c "import socket
for port in (5432, 8000, 8080, 9000):
    try:
        socket.create_connection(('<IP du pod>', port), timeout=3).close(); print(port, 'joint')
    except OSError as error:
        print(port, 'refusé', error)"
```

Puis, depuis le pod du test, joindre le PostgreSQL de la production et une adresse qu'aucune règle
ne nomme, sur un port pourtant permis — par exemple l'adresse d'un pod de l'espace de noms qui
n'est pas le PostgreSQL, ou une adresse hors du cluster, sur le port 5432 :

```
kubectl -n NS exec <pod> -c api -- python3 -c "import socket
for host in ('RELEASE-postgres', '<IP-autre-pod>', '<adresse-hors-cluster>'):
    try:
        socket.create_connection((host, 5432), timeout=3).close(); print(host, 'joint')
    except OSError as error:
        print(host, 'refusé', error)"
```

Attendu : aucun Service ne sélectionne le pod du test (aucun sélecteur ne porte
`app.kubernetes.io/component: restore-test`) ; depuis un autre pod de l'espace de noms, aucun des
ports du PostgreSQL (5432), de l'API (8000) et de Keycloak (8080, 9000) n'est joint ; l'ingress
n'a aucune route vers lui ; depuis le pod du test, le PostgreSQL de la production est joint, les
deux autres adresses ne le sont pas.

Constaté :

### 5. Après le test : l'environnement n'existe plus, le résultat est consultable

```
kubectl -n NS get jobs,pods,pvc -l app.kubernetes.io/component=restore-test
psql -c "SELECT started_at, finished_at, backup_taken_at, succeeded, projects, marked_revisions, \
  cost_lines, identity_accounts, failure FROM restore_test ORDER BY finished_at DESC LIMIT 1"
```

Puis ouvrir l'écran d'état du système, avec un compte qui porte la permission de le consulter.

Attendu : ni Job, ni pod, ni volume du test ne reste ; le test est inscrit, `succeeded` vrai, ses
décomptes ceux de la sauvegarde ; l'écran d'état présente, à la ligne « Test de restauration », la
date de fin du test et son résultat, « Réussie ».

Constaté (date présentée, résultat, décomptes) :

### 6. Le test échoue et le signale si le nombre de projets diffère

Ce point ne se provoque pas sur le cluster de recette, dont il faudrait altérer une sauvegarde. La
chaîne le joue à chaque lot, sur une plateforme jetable : le test échoue, inscrit `projects_differ`,
et l'écran d'état présente l'échec (`backend/tests/test_restore_trial.py`,
`test_the_test_fails_and_says_so_when_the_projects_restored_are_not_those_of_the_backup` ;
`backend/tests/test_restore_test_status.py`, `test_a_failed_test_is_said_failed_on_the_screen`).

Constaté (l'exécution de la chaîne qui les a joués, sur la version recettée) :

### 7. Le mois suivant (facultatif)

Trente jours après le premier, la commande planifiée dépose le test suivant, sans intervention.

Constaté (date du second dépôt) :

## La conclusion

| Phrase du Vérif | Étape | Conforme |
|---|---|---|
| Un test de restauration mensuel est exécuté | 3, 7 | |
| son résultat daté est consultable | 5 | |
| Le test échoue et le signale si le nombre de projets diffère | 6 | |
| L'environnement du test n'est joignable par aucun utilisateur | 4 | |
| et n'existe plus après le test | 5 | |

Écarts constatés, et les issues ouvertes :

Recette prononcée le :                    par :
