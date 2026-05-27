{{/*
=============================================================================
Nautobot ConfigMap Data Templates
=============================================================================
Named templates for Nautobot ConfigMap data sections, used in both ConfigMap
definitions and Deployment checksum annotations. This ensures pods
automatically restart when ConfigMap content changes.

Usage in ConfigMap:
  data:
  {{- include "nv-config-manager.configmap.<name>" . | nindent 2 }}

Usage in Deployment annotation:
  checksum/<name>: {{ include "nv-config-manager.configmap.<name>" . | sha256sum }}
=============================================================================
*/}}

{{/*
Nautobot environment ConfigMap data
*/}}
{{- define "nv-config-manager.configmap.nautobot-env" -}}
{{- $natsName := include "nv-config-manager.componentName" (dict "root" . "component" "nats") -}}
NAUTOBOT_ALLOWED_HOSTS: "*"
# CSRF_TRUSTED_ORIGINS is required for Django 4.0+ when behind HTTPS proxy
# Include the external gateway URL and internal service URL for cluster-internal writes
NAUTOBOT_CSRF_TRUSTED_ORIGINS: "https://{{ tpl .Values.nautobot.gateway.hostname . }},http://{{ .Values.nautobot.name }}-nv-config-manager"
NAUTOBOT_DEBUG: "{{ .Values.nautobot.server.debug }}"
NAUTOBOT_LOG_LEVEL: "{{ .Values.nautobot.server.logLevel }}"
NAUTOBOT_DB_ENGINE: "django.db.backends.postgresql"
NAUTOBOT_DB_HOST: "{{ tpl .Values.nautobot.server.db.host . }}"
NAUTOBOT_DB_PORT: "{{ .Values.nautobot.server.db.port }}"
NAUTOBOT_DB_NAME: "{{ .Values.nautobot.server.db.name }}"
NAUTOBOT_DB_USER: "nautobot"
NAUTOBOT_DB_TIMEOUT: "300"
# Use shared Redis instance
NAUTOBOT_REDIS_HOST: "{{ include "nv-config-manager.redisHost" . }}"
NAUTOBOT_REDIS_PORT: "{{ .Values.externalServices.redis.port }}"
NAUTOBOT_REDIS_SSL: "{{ .Values.externalServices.redis.ssl }}"
NAUTOBOT_METRICS_ENABLED: "{{ .Values.nautobot.metrics.enabled }}"
NAUTOBOT_CREATE_SUPERUSER: "true"
NAUTOBOT_SUPERUSER_NAME: "{{ ((.Values.nautobot).admin).username | default "admin" }}"
NAUTOBOT_SUPERUSER_EMAIL: "{{ ((.Values.nautobot).admin).email | default "admin@example.com" }}"
NATS_HOST: "{{ include "nv-config-manager.natsServer" . }}"
NV_CONFIG_MANAGER_DEPLOYMENT_TYPE: "all"
NV_CONFIG_MANAGER_TEMPORAL_URL: "https://{{ .Values.gateway.baseHostname }}"
NAUTOBOT_PLUGINS: "nautobot_fsus,nautobot_kiwi,nautobot_broker_nats,nautobot_firewall_models,nautobot_design_builder,nautobot_bgp_models"
# Ensure Python uses UTF-8 encoding for file I/O
PYTHONIOENCODING: "utf-8"
LC_ALL: "C.UTF-8"
LANG: "C.UTF-8"
{{- if .Values.nautobot.customJobs.enabled }}
# Custom jobs are mounted to NAUTOBOT_ROOT/jobs/
NAUTOBOT_JOBS_ROOT: "/opt/nautobot/jobs"
# JOBS_ROOT must be on PYTHONPATH for multi-module job packages to import correctly.
# Nautobot's import_modules_privately only temporarily adds JOBS_ROOT during startup scanning,
# but job packages need intra-package imports at runtime when executed via API/Celery.
PYTHONPATH: "/opt/nautobot/jobs:/usr/local/lib/python3.11/dist-packages:/app"
{{- end }}
{{- if .Values.spiffe.enabled }}
# SPIFFE JWT-SVID validation (nv_config_manager_auth.jwt_authentication)
SPIFFE_JWKS_URI: {{ .Values.spiffe.jwksUri | default "/var/run/secrets/spiffe/bundle.json" | quote }}
SPIFFE_AUDIENCES: "spiffe://{{ .Values.spiffe.trustDomain }}"
{{- end }}
{{- if or .Values.oidc.enabled .Values.gateway.auth.jwt.providers }}
# Multi-provider JWT authentication (nv_config_manager_auth.jwt_authentication)
# JSON array of trusted JWT issuers.  OIDC provider has user_provider=true
# so browser users get individual Django accounts from JWT claims.
NV_CONFIG_MANAGER_JWT_PROVIDERS: {{ include "nv-config-manager.nautobot.jwtProviders" . | squote }}
{{- end }}
{{- if .Values.oidc.enabled }}
# Cookie name for browser JWT extraction
NV_CONFIG_MANAGER_JWT_COOKIE: {{ .Values.oidc.cookieName | default "NVConfigManagerAccessToken" | quote }}
{{- end }}
{{- with .Values.nautobot.rbac.superuserGroups }}
# Group/role names that grant Nautobot superuser status (nv_config_manager_auth.jwt_authentication).
# Reconciled against the JWT groups claim on every login.
NV_CONFIG_MANAGER_SUPERUSER_GROUPS: {{ join "," . | quote }}
{{- end }}
{{- end -}}

{{/*
Nautobot uwsgi ConfigMap data
*/}}
{{- define "nv-config-manager.configmap.nautobot-config" -}}
uwsgi.ini: |
  [uwsgi]
  ; The IP address (typically localhost) and port that the web server should listen on
  http-socket = 0.0.0.0:8003
  
  ; The number of worker processes
  processes = {{ .Values.nautobot.server.uwsgi.processes }}
  
  ; The number of threads per worker
  threads = {{ .Values.nautobot.server.uwsgi.threads }}
  
  ; Buffer size
  buffer-size = {{ .Values.nautobot.server.uwsgi.bufferSize }}
  
  ; Enable the master process
  master = true
  
  ; Set the harakiri timeout
  harakiri = {{ .Values.nautobot.server.uwsgi.harakiri }}
  
  ; The WSGI module to load
  module = nautobot.core.wsgi:application
  
  ; Listen queue size
  listen = {{ .Values.nautobot.server.uwsgi.listen }}
  
  ; Log format
  log-format = [pid: %(pid)|app: -|req: -/-] %(addr) (%(user)) {%(vars) vars in %(pktsize) bytes} [%(ctime)] %(method) %(uri) => generated %(rsize) bytes in %(msecs) msecs (%(proto) %(status)) %(headers) headers in %(hsize) bytes (%(switches) switches on core %(core))
  
  ; Disable logging (nautobot handles its own logging)
  disable-logging = true
  
  ; Enable stats
  stats = 127.0.0.1:1717
{{- end -}}
