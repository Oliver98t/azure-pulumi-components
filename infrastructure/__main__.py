import pulumi

from pulumi_components.function_app import FunctionAppComponent

base_name = f"{pulumi.get_project()}-function-app".lower()
location = pulumi.Config("azure-native").get("location") or "WestUS2"

function_app = FunctionAppComponent(
    name=base_name,
	location=location,
)

pulumi.export("resource_group_name", function_app.resource_group.name)
pulumi.export("storage_account_name", function_app.storage_account.name)
pulumi.export(
	"application_insights_name",
	function_app.application_insights.name,
)
pulumi.export("service_plan_name", function_app.service_plan.name)
pulumi.export("function_app_name", function_app.function_app.name)
pulumi.export(
	"function_app_url",
	pulumi.Output.concat(
		"https://",
		function_app.function_app.default_host_name,
	),
)

