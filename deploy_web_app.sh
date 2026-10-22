#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

web_app_name=$(cd infrastructure && pulumi stack output web-app-web_app_name)
resource_group=$(cd infrastructure && pulumi stack output web-app-resource_group_name)

package_dir=$(mktemp -d)
trap 'rm -f "$package_dir/app.zip"; rmdir "$package_dir"' EXIT

(
  cd source/web-app
  zip -qr "$package_dir/app.zip" . \
    -x '.venv/*' '*/.venv/*' 'venv/*' '*/venv/*' \
       '.git/*' '*/.git/*' '__pycache__/*' '*/__pycache__/*' \
       '.pytest_cache/*' '*/.pytest_cache/*' \
       'node_modules/*' '*/node_modules/*' '.env*' '*/.env*'
)

az webapp deploy \
  --name "$web_app_name" \
  --resource-group "$resource_group" \
  --src-path "$package_dir/app.zip" \
  --type zip \
  --async true \
  --track-status false

printf '\nDeployment submitted asynchronously; build and startup are not yet verified.\n'
printf 'Check deployment status (3 = failed, 4 = successful):\n'
printf 'az webapp log deployment list --name %q --resource-group %q --query %q --output json\n' \
  "$web_app_name" "$resource_group" \
  '[0].{id:id,status:status,complete:complete,start:start_time,end:end_time}'
printf '\nCheck deployment logs:\n'
printf 'az webapp log deployment show --name %q --resource-group %q\n' \
  "$web_app_name" "$resource_group"