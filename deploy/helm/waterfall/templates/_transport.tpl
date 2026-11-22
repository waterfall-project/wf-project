{{- /*
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only

The encryption between the services (US-2840, WF-SEC-0010; EP-13, « Le transport »), as
compose.prod.yaml makes it with its service authority. The authority of the platform is the Secret
transport.authority names, or the one the chart makes at the installation (transport.yaml): ca.crt
and ca.key. In each pod that serves in TLS, a container of initialisation issues the certificate of
its server, for the name of its Service, by the command of the Compose, waterfall-authority, as the
user the server runs as; it alone mounts the key of the authority. In every pod, it writes the
roots the clients trust, /trust/root.crt: the root of the platform, followed by the roots of the
data components the operator provides (transport.providedAuthority), when one is.
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
  securityContext:
    runAsUser: {{ index . 2 }}
    runAsGroup: {{ index . 3 }}
  {{- end }}
  command:
    - sh
    - -c
    - |-
      set -eu
      cat /roots/*.crt > {{ include "waterfall.roots" $ }}
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
