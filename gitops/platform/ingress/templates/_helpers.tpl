{{/* Public hostname of a route: <name>.<domain> unless `host` is set. */}}
{{- define "ingress.host" -}}
{{- $r := index .root.Values.routes .name -}}
{{- $r.host | default (printf "%s.%s" .name .root.Values.domain) -}}
{{- end -}}

{{- define "ingress.provider" -}}
{{- $p := .Values.global.gatewayProvider -}}
{{- if not (has $p (list "istio" "envoy" "external")) -}}
{{- fail (printf "global.gatewayProvider must be istio, envoy or external (got %q)" $p) -}}
{{- end -}}
{{- $p -}}
{{- end -}}

{{/* GatewayClass: explicit value, else the provider's own class. */}}
{{- define "ingress.className" -}}
{{- $p := include "ingress.provider" . -}}
{{- if .Values.gateway.className -}}{{ .Values.gateway.className }}
{{- else if eq $p "istio" -}}istio
{{- else if eq $p "envoy" -}}envoy
{{- else -}}{{ fail "gateway.className is required with gatewayProvider: external" }}
{{- end -}}
{{- end -}}

{{/*
What differs between implementations, for the provider-neutral Service:
the labels on the Envoy pods each one runs for our Gateway, and the ports they
listen on (Envoy Gateway shifts privileged ports by +10000; Istio binds them).
*/}}
{{- define "ingress.podSelector" -}}
{{- $p := include "ingress.provider" . -}}
{{- if .Values.localService.selector -}}
{{ toYaml .Values.localService.selector }}
{{- else if eq $p "istio" -}}
gateway.networking.k8s.io/gateway-name: {{ .Values.gateway.name }}
{{- else if eq $p "envoy" -}}
gateway.envoyproxy.io/owning-gateway-name: {{ .Values.gateway.name }}
gateway.envoyproxy.io/owning-gateway-namespace: {{ .Release.Namespace }}
{{- else -}}
{{ fail "localService.selector is required with gatewayProvider: external" }}
{{- end -}}
{{- end -}}

{{- define "ingress.targetPorts" -}}
{{- $p := include "ingress.provider" . -}}
{{- if .Values.localService.targetPorts -}}
{{ toYaml .Values.localService.targetPorts }}
{{- else if eq $p "envoy" -}}
{ http: 10080, https: 10443 }
{{- else -}}
{ http: 80, https: 443 }
{{- end -}}
{{- end -}}
