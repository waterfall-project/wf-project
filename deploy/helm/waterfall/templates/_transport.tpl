{{- /*
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only

The encryption between the services (US-2840, WF-SEC-0010; EP-13, « Le transport »), as
compose.prod.yaml makes it with its service authority. The authority of the platform is the Secret
transport.authority names, or the one the chart makes at the installation (transport.yaml): ca.crt
and ca.key. In each pod of the API, Keycloak and the front, a container of initialisation issues the
certificate of its server, for the name of its Service, by the command of the Compose,
waterfall-authority, as the user the server runs as; it alone mounts the key of the authority. The
data components and the supervision — PostgreSQL, Redis, the storage, Prometheus, Alertmanager and
Grafana — have none: their pods must not depend on the version of Waterfall, whose image an upgrade
changes, or every upgrade would restart them (US-2850, #4089, option C). Each mounts the Secret of
its certificate, which the hook of certificates.yaml writes when it is missing or close to its end.
In every other pod, the container of initialisation writes the roots the clients trust,
/trust/root.crt: the root of the platform, followed by the roots of the
data components the operator provides (transport.providedAuthority), when one is; each root
followed by a line feed, that a file which does not end with one is not glued to the next.
*/ -}}

{{/* The file of the roots every client of a pod checks its servers against. */}}
{{- define "waterfall.roots" -}}/trust/root.crt{{- end -}}

{{/* The Secret of the authority of the platform: the operator's, or the one the chart makes. */}}
{{- define "waterfall.authority" -}}
{{- .Values.transport.authority | default (include "waterfall.name" (list . "authority")) -}}
{{- end -}}

{{/* Whether a data component is the operator's: its certificate is checked against the roots of
transport.providedAuthority, without which the rendering stops — never against another root. */}}
{{- define "waterfall.provided" -}}
{{- if or (not .Values.postgresql.enabled) (not .Values.redis.enabled) (not .Values.storage.enabled) -}}
{{- required "transport.providedAuthority: the Secret whose key ca.crt holds the roots the certificates of the data components the operator provides are checked against (postgresql, redis or storage has enabled false)" .Values.transport.providedAuthority -}}
{{- end -}}
{{- end -}}

{{/* The container of initialisation of a pod: the roots its clients trust, and, for a pod that
serves in TLS, the key and the certificate of its server, in the folder of its name, owned by the
user it runs as, the key readable by it alone: (list $) for a client alone, or
(list $ "component" uid gid). */}}
{{- define "waterfall.transportInit" -}}
{{- $ := index . 0 -}}
{{- $served := gt (len .) 1 -}}
- name: transport
  image: {{ include "waterfall.image" (list $ "waterfall") }}
  imagePullPolicy: {{ $.Values.images.pullPolicy }}
  {{- if $served }}
  {{- include "waterfall.containerSecurity" (dict "runAsUser" (index . 2) "runAsGroup" (index . 3)) | nindent 2 }}
  {{- else }}
  {{- include "waterfall.containerSecurity" (dict) | nindent 2 }}
  {{- end }}
  command:
    - sh
    - -c
    - |-
      set -eu
      for root in /roots/*.crt; do cat "$root"; echo; done > {{ include "waterfall.roots" $ }}
      {{- if $served }}
      exec waterfall-authority --provided=/authority --kept=/tmp/authority --trust=/tmp/trust --certificates=/certificates {{ printf "%s:%v:%v" (include "waterfall.name" (list $ (index . 1))) (index . 2) (index . 3) }}
      {{- end }}
  volumeMounts:
    - name: roots
      mountPath: /roots
      readOnly: true
    - name: trust
      mountPath: /trust
    {{- if $served }}
    - name: authority
      mountPath: /authority
      readOnly: true
    - name: certificates
      mountPath: /certificates
    {{- end }}
{{- end -}}

{{/* Where a container reads the roots of the pod. */}}
{{- define "waterfall.trustMount" -}}
- name: trust
  mountPath: /trust
  readOnly: true
{{- end -}}

{{/* Where a server reads its certificate and its key, those of its name alone, and the root of the
platform beside them: (list $ "component"). */}}
{{- define "waterfall.tlsMount" -}}
- name: certificates
  mountPath: /tls
  subPath: {{ include "waterfall.name" (list (index . 0) (index . 1)) }}
  readOnly: true
{{- end -}}

{{/* The volumes of the encryption of a pod: the roots, and for a pod that serves in TLS the
authority and its certificates: (list $) or (list $ "serves"). */}}
{{- define "waterfall.transportVolumes" -}}
{{- $ := index . 0 -}}
{{- $provided := include "waterfall.provided" $ -}}
- name: roots
  projected:
    sources:
      - secret:
          name: {{ include "waterfall.authority" $ }}
          items:
            - key: ca.crt
              path: platform.crt
      {{- with $provided }}
      - secret:
          name: {{ . }}
          items:
            - key: ca.crt
              path: provided.crt
      {{- end }}
- name: trust
  emptyDir:
    medium: Memory
    sizeLimit: 1Mi
{{- if gt (len .) 1 }}
- name: authority
  secret:
    secretName: {{ include "waterfall.authority" $ }}
    items:
      - key: ca.crt
        path: ca.crt
      - key: ca.key
        path: ca.key
- name: certificates
  emptyDir:
    medium: Memory
    sizeLimit: 1Mi
{{- end }}
{{- end -}}

{{/* The Secret of the certificate of a data component or of the supervision (US-2850): tls.key,
tls.crt for the name of its Service, and ca.crt, the root of the platform, which its own clients
read. The hook of certificates.yaml writes it: (list $ "postgres"). */}}
{{- define "waterfall.certificate" -}}
{{- printf "%s-tls" (include "waterfall.name" .) -}}
{{- end -}}

{{/* The volume of that Secret in its pod, readable by the user and the group of the pod alone: the
server runs in its fsGroup, which Kubernetes gives the files. (list $ "postgres"). */}}
{{- define "waterfall.certificateVolume" -}}
- name: certificates
  secret:
    secretName: {{ include "waterfall.certificate" . }}
    # 0440: PostgreSQL refuses a key that others may read.
    defaultMode: 288
{{- end -}}

{{/* Where a data component reads its certificate, its key and the root of the platform. */}}
{{- define "waterfall.certificateMount" -}}
- name: certificates
  mountPath: /tls
  readOnly: true
{{- end -}}

{{/* The workloads whose certificates the hook writes, those of the components the chart deploys:
statefulsets/<name> or deployments/<name>, in JSON. */}}
{{- define "waterfall.certified" -}}
{{- $ := . -}}
{{- $certified := list -}}
{{- range $component := list (list "postgres" "statefulsets" $.Values.postgresql.enabled) (list "redis" "deployments" $.Values.redis.enabled) (list "storage" "statefulsets" $.Values.storage.enabled) (list "prometheus" "statefulsets" $.Values.prometheus.enabled) (list "alertmanager" "deployments" true) (list "grafana" "deployments" true) -}}
{{- if index $component 2 -}}
{{- $certified = append $certified (printf "%s/%s" (index $component 1) (include "waterfall.name" (list $ (index $component 0)))) -}}
{{- end -}}
{{- end -}}
{{- toJson $certified -}}
{{- end -}}
