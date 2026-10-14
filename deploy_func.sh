cd infrastructure
pulumi up -y
function_app_name=$(pulumi stack output function_app_name)
cd ..
cd source/function-app
func azure functionapp publish "$function_app_name" \
  --python \
  --build remote
cd .. 