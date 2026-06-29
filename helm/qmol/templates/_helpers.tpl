{{/*
Expand the name of the chart.
*/}}
{{- define "qmol.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "qmol.fullname" -}}
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
{{- define "qmol.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "qmol.labels" -}}
helm.sh/chart: {{ include "qmol.chart" . }}
{{ include "qmol.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "qmol.selectorLabels" -}}
app.kubernetes.io/name: {{ include "qmol.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "qmol.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "qmol.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL fullname helper
*/}}
{{- define "qmol.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "qmol.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Redis fullname helper
*/}}
{{- define "qmol.redis.fullname" -}}
{{- printf "%s-redis-master" (include "qmol.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Database URL
*/}}
{{- define "qmol.databaseUrl" -}}
{{- $pgHost := include "qmol.postgresql.fullname" . }}
{{- $pgUser := .Values.postgres.auth.username }}
{{- $pgDb := .Values.postgres.auth.database }}
{{- if .Values.postgres.auth.existingSecret }}
{{- printf "postgresql+asyncpg://%s:$(DATABASE_PASSWORD)@%s:5432/%s" $pgUser $pgHost $pgDb }}
{{- else }}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" $pgUser "$(DATABASE_PASSWORD)" $pgHost $pgDb }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "qmol.redisUrl" -}}
{{- printf "redis://%s:6379/0" (include "qmol.redis.fullname" .) }}
{{- end }}

{{/*
Pod annotations
*/}}
{{- define "qmol.podAnnotations" -}}
{{- with .Values.podAnnotations }}
{{- toYaml . }}
{{- end }}
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
{{- end }}
