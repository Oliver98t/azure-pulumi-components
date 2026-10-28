import pulumi

from pulumi_components.function_app import FunctionAppComponent
from pulumi_components.static_web_app import StaticWebAppComponent
from pulumi_components.web_app import WebAppComponent

def export_component_outputs(prefix_name: str, outputs: dict):
	for output in outputs:
		pulumi.export(f"{prefix_name}-{output}", outputs[output])

base_name = f"{pulumi.get_project()}".lower()
location = pulumi.Config("azure-native").get("location") or "WestUS2"

# function app test
#####################################################################
function_app = FunctionAppComponent(
    name=f"{base_name}-function-app",
	location=location,
)
#####################################################################

# static web app test
#####################################################################
static_web_app = StaticWebAppComponent(
    name=f"{base_name}-frontend",
    location=location,
)
#####################################################################

# web app app test
#####################################################################
network_stack = pulumi.StackReference(
    f"{pulumi.get_organization()}/azure-pulumi-infrastructure/{pulumi.get_stack()}"
)

subnet_id = network_stack.require_output("subnet_id")
print(str(static_web_app.outputs['static_web_app_url']))
web_app = WebAppComponent(
    name=f"{base_name}-web-app",
    location=location,
    subnet_id=subnet_id,
    allowed_origins=str(static_web_app.outputs['static_web_app_url'])
)
#####################################################################

export_component_outputs("function-app", function_app.ouptuts)
export_component_outputs("web-app", web_app.outputs)
export_component_outputs("static-web-app", static_web_app.outputs)