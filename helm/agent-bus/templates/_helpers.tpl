{{/*
Expand the name of the chart.
*/}}
{{- define "agent-bus.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "agent-bus.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "agent-bus.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "agent-bus.labels" -}}
helm.sh/chart: {{ include "agent-bus.chart" . }}
{{ include "agent-bus.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "agent-bus.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agent-bus.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API labels
*/}}
{{- define "agent-bus.api.labels" -}}
{{ include "agent-bus.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Worker labels
*/}}
{{- define "agent-bus.worker.labels" -}}
{{ include "agent-bus.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Orchestrator labels
*/}}
{{- define "agent-bus.orchestrator.labels" -}}
{{ include "agent-bus.labels" . }}
app.kubernetes.io/component: orchestrator
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "agent-bus.postgresql.host" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.host }}
{{- else }}
{{- printf "%s-postgres" (include "agent-bus.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "agent-bus.redis.host" -}}
{{- if .Values.redis.external.enabled }}
{{- .Values.redis.external.host }}
{{- else }}
{{- printf "%s-redis" (include "agent-bus.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Image name
*/}}
{{- define "agent-bus.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
