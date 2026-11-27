{{/*
A component is rendered when it is enabled AND, if it is tied to a Gateway API
implementation (`gatewayProvider`), that implementation is the selected one.
Usage: include "root.enabled" (dict "c" $c "g" $.Values.global) → "true" or ""
*/}}
{{- define "root.enabled" -}}
{{- if and .c.enabled (or (not .c.gatewayProvider) (eq .c.gatewayProvider .g.gatewayProvider)) -}}true{{- end -}}
{{- end -}}
