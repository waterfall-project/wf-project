{{- /*
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only

What every template of the chart shares: the names, the labels, the images, the addresses, and the
environments compose.prod.yaml writes once as its anchors (x-back-environment and the others). A
template names a component by its name in compose.prod.yaml — front, api, postgres… —, which is the
suffix of its objects and the value of its label app.kubernetes.io/component.
*/ -}}

{{/*
The prefix of every object: the release, followed by the name of the chart unless it holds it. At
most 28 characters, so that the longest name of a CronJob, which Kubernetes bounds to 52 (its Jobs
add eleven to the 63 of a label), stays under it with its suffix, "-scheduler-identity-sync".
*/}}
{{- define "waterfall.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 28 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 28 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* The name of the object of a component: (list $ "api"). */}}
{{- define "waterfall.name" -}}
{{- printf "%s-%s" (include "waterfall.fullname" (index . 0)) (index . 1) -}}
{{- end -}}

{{/* The labels that select the pods of a component: (list $ "api"). */}}
{{- define "waterfall.selector" -}}
app.kubernetes.io/name: {{ (index . 0).Chart.Name }}
app.kubernetes.io/instance: {{ (index . 0).Release.Name }}
app.kubernetes.io/component: {{ index . 1 }}
{{- end -}}

{{/* Every label of an object of a component: (list $ "api"). */}}
{{- define "waterfall.labels" -}}
{{ include "waterfall.selector" . }}
app.kubernetes.io/version: {{ (index . 0).Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ (index . 0).Release.Service }}
helm.sh/chart: {{ printf "%s-%s" (index . 0).Chart.Name (index . 0).Chart.Version }}
{{- end -}}

{{/* An image the chain publishes, by its name: (list $ "waterfall"). */}}
{{- define "waterfall.image" -}}
{{- $images := (index . 0).Values.images -}}
{{- printf "%s/%s:%s" $images.registry (index . 1) (required "images.tag: the tag of the images the chain published" $images.tag) -}}
{{- end -}}

{{/* An image of a third party, read from the mirror when one is given: (list $ "postgres:…"). */}}
{{- define "waterfall.thirdParty" -}}
{{- printf "%s%s" (index . 0).Values.images.mirror (index . 1) -}}
{{- end -}}

{{/* What every pod shares: no variable of the services of the namespace — a service named
waterfall-api would give WATERFALL_API_PORT to every container —, and the secrets of the registries. */}}
{{- define "waterfall.podDefaults" -}}
enableServiceLinks: false
{{- with .Values.images.pullSecrets }}
imagePullSecrets:
{{- range . }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end -}}

{{/* The address the browser reaches the platform at. */}}
{{- define "waterfall.address" -}}
{{- $platform := .Values.platform -}}
{{- $domain := required "platform.domain: where the browser reaches the platform" $platform.domain -}}
{{- if $platform.httpsPort -}}
{{- printf "https://%s:%v" $domain $platform.httpsPort -}}
{{- else -}}
{{- printf "https://%s" $domain -}}
{{- end -}}
{{- end -}}

{{/* The name of the Secret that holds the passwords and the secrets. */}}
{{- define "waterfall.secret" -}}
{{- .Values.secrets.existingSecret | default (include "waterfall.name" (list . "secrets")) -}}
{{- end -}}

{{/* The keys of that Secret: the names of production.env.example. */}}
{{- define "waterfall.secretKeys" -}}
WATERFALL_POSTGRES_ADMIN_PASSWORD WATERFALL_POSTGRES_PASSWORD WATERFALL_SERVICE_DATABASE_PASSWORD WATERFALL_BACKUP_DATABASE_PASSWORD WATERFALL_KEYCLOAK_DATABASE_PASSWORD WATERFALL_REDIS_PASSWORD WATERFALL_KEYCLOAK_ADMIN_PASSWORD WATERFALL_FRONT_CLIENT_SECRET WATERFALL_SERVICE_CLIENT_SECRET WATERFALL_INSTALLATION_CLIENT_SECRET WATERFALL_SERVER_ACTIONS_KEY WATERFALL_STORAGE_SECRET WATERFALL_STORAGE_RPC_SECRET
{{- end -}}

{{/* A variable read from that Secret, under its own name or another: (list $ "KEY") or
(list $ "KEY" "NAME"). Declared before the variables that cite it as $(KEY). */}}
{{- define "waterfall.secretEnv" -}}
- name: {{ index . (sub (len .) 1) }}
  valueFrom:
    secretKeyRef:
      name: {{ include "waterfall.secret" (index . 0) }}
      key: {{ index . 1 }}
{{- end -}}

{{/* The data components: the service of the chart's own, or the address of the operator's. A
component the operator provides (enabled: false) is reached at its host and port, with the
passwords of the Secret, which holds the same keys. */}}
{{- define "waterfall.postgresHost" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "waterfall.name" (list . "postgres") -}}
{{- else -}}
{{- required "postgresql.host: the address of the PostgreSQL the operator provides (postgresql.enabled is false)" .Values.postgresql.host -}}
{{- end -}}
{{- end -}}
{{- define "waterfall.postgresPort" -}}
{{- if .Values.postgresql.enabled -}}5432{{- else -}}{{- .Values.postgresql.port | default 5432 | int -}}{{- end -}}
{{- end -}}
{{/* The host and the port, as a URL writes them. */}}
{{- define "waterfall.postgresAddress" -}}
{{- printf "%s:%s" (include "waterfall.postgresHost" .) (include "waterfall.postgresPort" .) -}}
{{- end -}}
{{- define "waterfall.redisAddress" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s:6379" (include "waterfall.name" (list . "redis")) -}}
{{- else -}}
{{- printf "%s:%d" (required "redis.host: the address of the Redis the operator provides (redis.enabled is false)" .Values.redis.host) (.Values.redis.port | default 6379 | int) -}}
{{- end -}}
{{- end -}}
{{- define "waterfall.redisUrl" -}}
{{- printf "redis://:$(WATERFALL_REDIS_PASSWORD)@%s/0" (include "waterfall.redisAddress" .) -}}
{{- end -}}
{{- define "waterfall.storageAddress" -}}
{{- if .Values.storage.enabled -}}
{{- printf "http://%s:3900" (include "waterfall.name" (list . "storage")) -}}
{{- else -}}
{{- required "storage.address: the address of the object storage the operator provides (storage.enabled is false)" .Values.storage.address -}}
{{- end -}}
{{- end -}}

{{/* The database of Waterfall and Redis, as the role of the service — or as the owner of the
tables, waterfall, with (list $ "owner") — (x-back-environment, #701). */}}
{{- define "waterfall.backEnvironment" -}}
{{- $ := index . 0 -}}
{{- $host := include "waterfall.postgresAddress" $ -}}
{{ include "waterfall.secretEnv" (list $ "WATERFALL_REDIS_PASSWORD") }}
{{- if eq (index . 1) "owner" }}
{{ include "waterfall.secretEnv" (list $ "WATERFALL_POSTGRES_PASSWORD") }}
- name: WATERFALL_DATABASE_URL
  value: {{ printf "postgresql://waterfall:$(WATERFALL_POSTGRES_PASSWORD)@%s/waterfall" $host | quote }}
{{- else }}
{{ include "waterfall.secretEnv" (list $ "WATERFALL_SERVICE_DATABASE_PASSWORD") }}
- name: WATERFALL_DATABASE_URL
  value: {{ printf "postgresql://waterfall_service:$(WATERFALL_SERVICE_DATABASE_PASSWORD)@%s/waterfall" $host | quote }}
{{- end }}
- name: WATERFALL_REDIS_URL
  value: {{ include "waterfall.redisUrl" $ | quote }}
{{- end -}}

{{/* Keycloak as the browser reaches it, and inside the cluster, for its keys and its
administration API, as its service account (x-keycloak-client-environment). */}}
{{- define "waterfall.keycloakClientEnvironment" -}}
- name: WATERFALL_KEYCLOAK_ADDRESS
  value: {{ printf "%s/auth" (include "waterfall.address" .) | quote }}
- name: WATERFALL_KEYCLOAK_BACKCHANNEL
  value: {{ printf "http://%s:8080/auth" (include "waterfall.name" (list . "keycloak")) | quote }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_SERVICE_CLIENT_SECRET") }}
{{- end -}}

{{/* The object storage, and the bucket of the backups (x-storage-environment). */}}
{{- define "waterfall.storageEnvironment" -}}
- name: WATERFALL_STORAGE_ADDRESS
  value: {{ include "waterfall.storageAddress" . | quote }}
- name: WATERFALL_STORAGE_ACCESS_KEY
  value: {{ .Values.storage.accessKey | quote }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_STORAGE_SECRET") }}
- name: WATERFALL_BACKUPS_BUCKET
  value: backups
{{- end -}}

{{/* The database of Keycloak, as its owner (x-keycloak-database). */}}
{{- define "waterfall.keycloakDatabase" -}}
- name: KC_DB_URL
  value: {{ printf "jdbc:postgresql://%s/keycloak" (include "waterfall.postgresAddress" .) | quote }}
- name: KC_DB_USERNAME
  value: keycloak
{{ include "waterfall.secretEnv" (list . "WATERFALL_KEYCLOAK_DATABASE_PASSWORD" "KC_DB_PASSWORD") }}
{{- end -}}

{{/* The application of the realm (compose.prod.yaml, keycloak-realm): Keycloak, its database and
its administrator, the addresses of the front and the secrets of the clients, and the folder where
the service of the restoration asks for it again (#955). */}}
{{- define "waterfall.realmEnvironment" -}}
{{ include "waterfall.keycloakDatabase" . }}
- name: KEYCLOAK_URL
  value: {{ printf "http://%s:8080/auth" (include "waterfall.name" (list . "keycloak")) | quote }}
- name: KEYCLOAK_USER
  value: admin
{{ include "waterfall.secretEnv" (list . "WATERFALL_KEYCLOAK_ADMIN_PASSWORD" "KEYCLOAK_PASSWORD") }}
- name: WATERFALL_FRONT_ADDRESS
  value: {{ include "waterfall.address" . | quote }}
- name: WATERFALL_FRONT_BACKCHANNEL
  value: {{ printf "http://%s:3000" (include "waterfall.name" (list . "front")) | quote }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_FRONT_CLIENT_SECRET") }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_SERVICE_CLIENT_SECRET") }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_INSTALLATION_CLIENT_SECRET") }}
- name: WATERFALL_REALM_REQUESTS
  value: /realm-requests
{{- end -}}

{{/* PostgreSQL as its administrator, postgres: the steps of initialisation alone (x-administrator). */}}
{{- define "waterfall.administrator" -}}
- name: PGHOST
  value: {{ include "waterfall.postgresHost" . }}
- name: PGPORT
  value: {{ include "waterfall.postgresPort" . | quote }}
- name: PGUSER
  value: {{ .Values.postgresql.adminUser | quote }}
{{ include "waterfall.secretEnv" (list . "WATERFALL_POSTGRES_ADMIN_PASSWORD" "PGPASSWORD") }}
{{- end -}}

{{/* A container that waits until a role signs in to its database, which it can once the steps
of the database have made it — the role of the service, after the migrations (#701): the
dependencies of compose.prod.yaml on service-database-role and keycloak-database, here.
(list $ "role" "database" "KEY OF ITS PASSWORD"). */}}
{{- define "waterfall.waitForDatabase" -}}
{{- $ := index . 0 -}}
- name: wait-for-database
  image: {{ include "waterfall.thirdParty" (list $ $.Values.postgresql.image) }}
  imagePullPolicy: IfNotPresent
  command:
    - sh
    - -c
    - |-
      until psql --no-psqlrc --quiet --command='SELECT 1' >/dev/null 2>&1; do
        echo "waiting for $PGUSER to sign in to $PGDATABASE"
        sleep 2
      done
  env:
    - name: PGHOST
      value: {{ include "waterfall.postgresHost" $ }}
    - name: PGPORT
      value: {{ include "waterfall.postgresPort" $ | quote }}
    - name: PGUSER
      value: {{ index . 1 }}
    - name: PGDATABASE
      value: {{ index . 2 }}
{{ include "waterfall.secretEnv" (list $ (index . 3) "PGPASSWORD") | indent 4 }}
{{- end -}}

{{/* A container that waits until Keycloak answers 200 at a port and a path, its status line read
as compose.prod.yaml reads it — its readiness, 9000 /auth/health/ready, answers 503 while the
schema migrates (#1079): (list $ "9000" "/auth/health/ready"). */}}
{{- define "waterfall.waitForKeycloak" -}}
{{- $ := index . 0 -}}
- name: wait-for-keycloak
  image: {{ include "waterfall.image" (list $ "keycloak") }}
  imagePullPolicy: {{ $.Values.images.pullPolicy }}
  command:
    - bash
    - -c
    - |-
      until (exec 3<>"/dev/tcp/$KEYCLOAK_HOST/$KEYCLOAK_PORT" \
          && printf 'GET %s HTTP/1.0\r\nHost: %s\r\n\r\n' "$KEYCLOAK_PATH" "$KEYCLOAK_HOST" >&3 \
          && head -n 1 <&3 | grep -q ' 200 ') 2>/dev/null; do
        echo "waiting for Keycloak to answer $KEYCLOAK_PATH"
        sleep 3
      done
  env:
    - name: KEYCLOAK_HOST
      value: {{ include "waterfall.name" (list $ "keycloak") }}
    - name: KEYCLOAK_PORT
      value: {{ index . 1 | quote }}
    - name: KEYCLOAK_PATH
      value: {{ index . 2 | quote }}
{{- end -}}

{{/* When the steps of the database and the migrations run at the installation: after it, for the
PostgreSQL of the chart, which the cluster has not before; before it, for the operator's, which is
there already. Before each upgrade in both cases. */}}
{{- define "waterfall.migrationEvents" -}}
{{- if .Values.postgresql.enabled -}}post-install,pre-upgrade{{- else -}}pre-install,pre-upgrade{{- end -}}
{{- end -}}

{{/* The annotations of a hook: (list "post-install,pre-upgrade" weight). The Job of the last run is
kept until the next, its log with it — the link of the bootstrap is in it. */}}
{{- define "waterfall.hook" -}}
helm.sh/hook: {{ index . 0 }}
helm.sh/hook-weight: {{ index . 1 | quote }}
helm.sh/hook-delete-policy: before-hook-creation
{{- end -}}
