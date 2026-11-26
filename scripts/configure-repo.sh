#!/usr/bin/env bash
# One-time personalisation after forking:
#   scripts/configure-repo.sh <github-owner> <dockerhub-user>
# Replaces the CHANGE_ME placeholders (repo URLs, runbook links, image names).
set -euo pipefail
GH_OWNER="${1:?usage: $0 <github-owner> <dockerhub-user>}"
DH_USER="${2:?usage: $0 <github-owner> <dockerhub-user>}"
cd "$(dirname "$0")/.."

files=$(grep -rl "CHANGE_ME" --include='*.yaml' --include='*.yml' --include='*.md' --include='Dockerfile' \
        gitops apps .github docs README.md 2>/dev/null || true)
for f in $files; do
  # image names first (DockerHub), then GitHub URLs
  sed -i.bak -e "s#docker.io/CHANGE_ME/#docker.io/${DH_USER}/#g" \
             -e "s#github.com/CHANGE_ME/#github.com/${GH_OWNER}/#g" "$f"
  rm -f "$f.bak"
done
# CODEOWNERS teams → @<owner>/sre, @<owner>/shop (adjust to your real teams)
sed -i.bak "s#@CHANGE_ME/#@${GH_OWNER}/#g" .github/CODEOWNERS && rm -f .github/CODEOWNERS.bak
echo "Configured for github.com/${GH_OWNER} and docker.io/${DH_USER}."
echo "Remaining CHANGE_ME placeholders (cluster names for the 'existing' env — edit by hand):"
grep -rn "CHANGE_ME" gitops | grep -v "^Binary" || echo "  none"
