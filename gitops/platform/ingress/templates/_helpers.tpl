{{/* Public hostname of a route: <name>.<domain> unless `host` is set. */}}
{{- define "ingress.host" -}}
{{- $r := index .root.Values.routes .name -}}
{{- $r.host | default (printf "%s.%s" .name .root.Values.domain) -}}
{{- end -}}
