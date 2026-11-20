{{- /*
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only

What the supervision writes (US-2880, WF-OBS-0030): the configuration of Prometheus, the rules of the
alerts with the thresholds of the values, and the capacities the API declares of the spaces, from
which the metrics say what is left (#4229). A value that is not what it must be stops the rendering,
naming it: an alert at a threshold nobody chose is worse than none.
*/ -}}

{{/* A whole number above zero, given as a number or a string: (list "name.of.the.value" value). */}}
{{- define "waterfall.wholeNumber" -}}
{{- $given := toString (index . 1) -}}
{{- if not (regexMatch "^[1-9][0-9]*$" $given) -}}
{{- fail (printf "%s: a whole number above zero, not %q" (index . 0) $given) -}}
{{- end -}}
{{- $given -}}
{{- end -}}

{{/* A ratio above 0, at most 1, as compose.prod.yaml reads one: (list "name.of.the.value" value). */}}
{{- define "waterfall.ratio" -}}
{{- $given := toString (index . 1) -}}
{{- if not (regexMatch "^(0?\\.[0-9]*[1-9][0-9]*|1(\\.0*)?)$" $given) -}}
{{- fail (printf "%s: a ratio above 0, at most 1, not %q" (index . 0) $given) -}}
{{- end -}}
{{- $given -}}
{{- end -}}

{{/* The bytes of a size of a volume, a quantity of Kubernetes — 10Gi, 500M, 1073741824 —:
(list "name.of.the.value" size). */}}
{{- define "waterfall.bytes" -}}
{{- $given := toString (index . 1) -}}
{{- if not (regexMatch "^[1-9][0-9]*(Ki|Mi|Gi|Ti|Pi|k|M|G|T|P)?$" $given) -}}
{{- fail (printf "%s: a size in bytes, or followed by Ki, Mi, Gi, Ti, Pi, k, M, G, T or P, not %q" (index . 0) $given) -}}
{{- end -}}
{{- $units := dict "" 1 "Ki" 1024 "Mi" 1048576 "Gi" 1073741824 "Ti" 1099511627776 "Pi" 1125899906842624 "k" 1000 "M" 1000000 "G" 1000000000 "T" 1000000000000 "P" 1000000000000000 -}}
{{- $number := regexFind "^[0-9]+" $given -}}
{{- $unit := trimPrefix $number $given -}}
{{- mul (atoi $number) (get $units $unit) -}}
{{- end -}}

{{/* The capacities of the spaces, which the API declares: the sizes of the volumes of PostgreSQL and
of the object storage (x-capacities). */}}
{{- define "waterfall.capacities" -}}
- name: WATERFALL_DATABASE_CAPACITY_BYTES
  value: {{ include "waterfall.bytes" (list "postgresql.persistence.size" .Values.postgresql.persistence.size) | quote }}
- name: WATERFALL_STORAGE_CAPACITY_BYTES
  value: {{ include "waterfall.bytes" (list "storage.persistence.size" .Values.storage.persistence.size) | quote }}
{{- end -}}

{{/* The rules of the alerts, the model of the Compose with the thresholds of the values. */}}
{{- define "waterfall.alertRules" -}}
{{- $thresholds := .Values.prometheus.thresholds -}}
{{- $age := include "waterfall.wholeNumber" (list "prometheus.thresholds.taskQueueAgeSeconds" $thresholds.taskQueueAgeSeconds) -}}
{{- $window := include "waterfall.wholeNumber" (list "prometheus.thresholds.errorRateWindowSeconds" $thresholds.errorRateWindowSeconds) -}}
{{- $storage := include "waterfall.ratio" (list "prometheus.thresholds.storageUsage" $thresholds.storageUsage) -}}
{{- $errors := include "waterfall.ratio" (list "prometheus.thresholds.errorRate" $thresholds.errorRate) -}}
{{- .Files.Get "files/prometheus-alerts.yml"
  | replace "${WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS}" $age
  | replace "${WATERFALL_ERROR_RATE_WINDOW_SECONDS}" $window
  | replace "${WATERFALL_STORAGE_USAGE_THRESHOLD}" $storage
  | replace "${WATERFALL_ERROR_RATE_THRESHOLD}" $errors
  | trimSuffix "\n" -}}
{{- end -}}

{{/* What Prometheus collects: the jobs of the Compose (prometheus.yml), each component found by its
headless Service in the namespace of the release. */}}
{{- define "waterfall.prometheusConfiguration" -}}
{{- $port := include "waterfall.wholeNumber" (list "metrics.port" .Values.metrics.port) -}}
global:
  scrape_interval: 15s
  evaluation_interval: 15s
rule_files:
  - alerts.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: [{{ printf "%s:9093" (include "waterfall.name" (list $ "alertmanager")) }}]
scrape_configs:
{{- range $component := list "front" "api" "worker" }}
  - job_name: {{ $component }}
    {{- if eq $component "api" }}
    metrics_path: /api/v1/metrics
    {{- end }}
    dns_sd_configs:
      - names: [{{ printf "%s.%s.svc" (include "waterfall.name" (list $ (printf "%s-metrics" $component))) $.Release.Namespace }}]
        type: A
        port: {{ ternary "8000" $port (eq $component "api") }}
{{- end }}
{{- end -}}
