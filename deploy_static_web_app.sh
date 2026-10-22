#!/usr/bin/env bash
set -euo pipefail
set +x

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

static_web_app_name=$(cd infrastructure && pulumi stack output static-web-app-static_web_app_name)
resource_group=$(cd infrastructure && pulumi stack output static-web-app-resource_group_name)

if [[ -z "$static_web_app_name" || -z "$resource_group" ]]; then
  printf 'Static Web App stack outputs are empty. Deploy the infrastructure first.\n' >&2
  exit 1
fi

cd source/frontend
npm ci
npm run build

if [[ ! -s dist/index.html ]]; then
  printf 'Frontend build is missing dist/index.html; deployment cancelled.\n' >&2
  exit 1
fi

deployment_token=$(az staticwebapp secrets list \
  --name "$static_web_app_name" \
  --resource-group "$resource_group" \
  --query properties.apiKey \
  --output tsv \
  --only-show-errors)

if [[ -z "$deployment_token" || "$deployment_token" == "null" || "$deployment_token" == "None" ]]; then
  printf 'Azure did not return a Static Web App deployment token.\n' >&2
  exit 1
fi

SWA_CLI_DEPLOYMENT_TOKEN="$deployment_token" npm run deploy
unset deployment_token
