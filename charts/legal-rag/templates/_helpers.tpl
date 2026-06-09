{{- define "legal-rag.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "legal-rag.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "legal-rag.labels" -}}
helm.sh/chart: {{ include "legal-rag.chart" .root | quote }}
app.kubernetes.io/name: {{ include "legal-rag.name" .root | quote }}
app.kubernetes.io/instance: {{ .root.Release.Name | quote }}
app.kubernetes.io/component: {{ .component | quote }}
app.kubernetes.io/managed-by: {{ .root.Release.Service | quote }}
{{- end -}}

{{- define "legal-rag.selectorLabels" -}}
app: {{ .component | quote }}
{{- end -}}

{{- define "legal-rag.image" -}}
{{- $tag := default .root.Values.global.imageTag .image.tag -}}
{{- printf "%s:%s" .image.repository $tag -}}
{{- end -}}

{{- define "legal-rag.secretEnv" -}}
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secret.name }}
      key: DB_PASSWORD
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secret.name }}
      key: JWT_SECRET_KEY
- name: QDRANT_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secret.name }}
      key: QDRANT_URL
- name: QDRANT_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secret.name }}
      key: QDRANT_API_KEY
{{- end -}}

{{- define "legal-rag.podSecurityContext" -}}
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
{{- end -}}

{{- define "legal-rag.containerSecurityContext" -}}
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
{{- end -}}

{{- define "legal-rag.cloudSqlProxy" -}}
- name: cloud-sql-proxy
  image: {{ .Values.cloudSqlProxy.image }}
{{ include "legal-rag.containerSecurityContext" . | indent 2 }}
  args:
    - --unix-socket=/cloudsql
    - $(CLOUD_SQL_CONNECTION_NAME)
  env:
    - name: CLOUD_SQL_CONNECTION_NAME
      valueFrom:
        configMapKeyRef:
          name: legal-rag-config
          key: CLOUD_SQL_CONNECTION_NAME
  volumeMounts:
    - name: cloudsql
      mountPath: /cloudsql
  resources:
{{ toYaml .Values.cloudSqlProxy.resources | indent 4 }}
{{- end -}}
