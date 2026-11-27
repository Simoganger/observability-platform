#!/usr/bin/env bash
# End-to-end SSO check: logs into Grafana and Argo CD through Keycloak the way a
# browser does (redirect → Keycloak login form → callback) and asserts the role
# each demo user ends up with.
#   scripts/sso-smoke-test.sh                       # kind defaults
#   DOMAIN=example.com GATEWAY_IP=1.2.3.4 USERS="alice:Admin" scripts/sso-smoke-test.sh
set -euo pipefail
DOMAIN="${DOMAIN:-127.0.0.1.nip.io}"
GATEWAY_IP="${GATEWAY_IP:-127.0.0.1}"
# user:expected-grafana-role (sre-team → Admin, stakeholders → Viewer)
USERS="${USERS:-alice:Admin bob:Viewer}"
PASS="${DEMO_USER_PASSWORD:-$(kubectl -n keycloak get secret keycloak-secrets -o jsonpath='{.data.DEMO_USER_PASSWORD}' | base64 -d)}"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
JAR=""
c() {
  curl -sS -k --max-time 30 -b "$JAR" -c "$JAR" \
    --resolve "grafana.$DOMAIN:443:$GATEWAY_IP" \
    --resolve "argocd.$DOMAIN:443:$GATEWAY_IP" \
    --resolve "keycloak.$DOMAIN:443:$GATEWAY_IP" "$@"
}

# login <start-url> <user>: start the OIDC flow, submit Keycloak's form, follow back to the app.
login() {
  local page action
  page="$(c -L "$1")"
  action="$(grep -o '<form[^>]*id="kc-form-login"[^>]*>' <<<"$page" | grep -o 'action="[^"]*"' \
            | sed -e 's/^action="//' -e 's/"$//' -e 's/&amp;/\&/g')"
  [ -n "$action" ] || { echo "✘ no Keycloak login form behind $1"; return 1; }
  c -L -o /dev/null --data-urlencode "username=$2" --data-urlencode "password=$PASS" "$action"
}

fail=0
check() { # check <description> <actual> <expected>
  if [ "$2" = "$3" ]; then echo "  ✔ $1: $2"; else echo "  ✘ $1: got '$2', want '$3'"; fail=1; fi
}

echo "OIDC discovery:"
JAR="$TMP/anon"
check "issuer" "$(c "https://keycloak.$DOMAIN/realms/observability/.well-known/openid-configuration" | jq -r .issuer)" \
      "https://keycloak.$DOMAIN/realms/observability"

for entry in $USERS; do
  user="${entry%%:*}"; want="${entry##*:}"
  echo "$user:"

  JAR="$TMP/$user-grafana"
  login "https://grafana.$DOMAIN/login/generic_oauth" "$user"
  check "Grafana role" "$(c "https://grafana.$DOMAIN/api/user/orgs" | jq -r '.[0].role // "none"')" "$want"

  JAR="$TMP/$user-argocd"
  login "https://argocd.$DOMAIN/auth/login" "$user"
  check "Argo CD login" "$(c "https://argocd.$DOMAIN/api/v1/session/userinfo" | jq -r .loggedIn)" "true"
  [ "$want" = "Admin" ] && can=yes || can=no
  check "Argo CD may sync apps" \
        "$(c "https://argocd.$DOMAIN/api/v1/account/can-i/applications/sync/observability/demo-shop" | jq -r .value)" "$can"
done

[ "$fail" -eq 0 ] && echo "SSO OK" || { echo "SSO FAILED"; exit 1; }
