import pulumi
from pulumi_azure_native import resources, web


class StaticWebAppComponent(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        location: str,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("StaticWebApp", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)
        tags = {
            "environment": pulumi.get_stack(),
            "project": pulumi.get_project(),
            "managed-by": "pulumi",
        }

        self.resource_group = resources.ResourceGroup(
            f"{name}-rg",
            resource_group_name=f"{name}-rg",
            location=location,
            tags=tags,
            opts=child_opts,
        )
        self.static_web_app = web.StaticSite(
            f"{name}-static",
            name=f"{name}-static",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            sku=web.SkuDescriptionArgs(name="Free", tier="Free"),
            public_network_access="Enabled",
            tags=tags,
            opts=child_opts,
        )
        self.outputs = {
            "resource_group_name": self.resource_group.name,
            "static_web_app_name": self.static_web_app.name,
            "static_web_app_url": pulumi.Output.concat(
                "https://",
                self.static_web_app.default_hostname,
            ),
        }
        self.register_outputs(self.outputs)
