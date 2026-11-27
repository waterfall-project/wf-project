{{- /*
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only

The external locations of the backups (US-2910, WF-ADM-0170, #4655): one file in JSON, a Secret since
it holds the keys of the S3 storages, which the API — it lists and tests the locations — and the worker
— it copies to them — both mount and name by WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE, as
compose.prod.yaml does: the same file in both, or a copy would find its location unreachable. The
Secret is the one backups.externalLocations.existingSecret names, under the key locations.json, or
the one the chart makes from backups.externalLocations.locations. Neither: nothing is mounted, and
the installation offers no copy. A share is mounted by the operator, in both pods, by
backups.externalLocations.volumes and volumeMounts (docs/exploitation/copie-externe.md).
*/ -}}

{{/* The name of the Secret, empty when no location is declared. */}}
{{- define "waterfall.externalLocationsSecret" -}}
{{- $given := .Values.backups.externalLocations -}}
{{- if $given.existingSecret -}}
{{- $given.existingSecret -}}
{{- else if $given.locations -}}
{{- include "waterfall.name" (list . "external-locations") -}}
{{- end -}}
{{- end -}}

{{/* The variable that names the file, in the API and the worker. */}}
{{- define "waterfall.externalLocationsEnvironment" -}}
{{- if include "waterfall.externalLocationsSecret" . }}
- name: WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE
  value: /etc/waterfall/external-locations/locations.json
{{- end }}
{{- end -}}

{{/* The mounts of the pod: the file, then the shares the operator mounts. */}}
{{- define "waterfall.externalLocationsMounts" -}}
{{- if include "waterfall.externalLocationsSecret" . }}
- name: external-locations
  mountPath: /etc/waterfall/external-locations
  readOnly: true
{{- end }}
{{- with .Values.backups.externalLocations.volumeMounts }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* The volumes of the pod: the Secret, readable by the group of the user of the image, then the
volumes of the shares the operator declares. */}}
{{- define "waterfall.externalLocationsVolumes" -}}
{{- with include "waterfall.externalLocationsSecret" . }}
- name: external-locations
  secret:
    secretName: {{ . }}
    defaultMode: 0440
    items:
      - key: locations.json
        path: locations.json
{{- end }}
{{- with .Values.backups.externalLocations.volumes }}
{{ toYaml . }}
{{- end }}
{{- end -}}
