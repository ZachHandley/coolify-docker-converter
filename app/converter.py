import yaml
import json
from pydantic import BaseModel


class CoolifyVariable(BaseModel):
    id: str = "$$config_"
    name: str = ""
    label: str = ""
    defaultValue: str = ""
    description: str = ""


class Converter:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Converter()
        return cls._instance

    def __init__(self):
        if Converter._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Converter._instance = self

    def convert_to_coolify_template(self, docker_compose_content):
        with open(file_path, "r") as f:
            appwrite_docker_compose = yaml.safe_load(f)

        # Initialize the Coolify template dictionary

        coolify_template = {
            "templateVersion": "1.0.0",
            "defaultVersion": "1.4.2",  # This can be dynamic
            "type": "appwrite",
            "name": "Appwrite",
            "description": "Your Backend for Frontend",
            "labels": ["backend", "database", "storage"],
            "services": {},
            "variables": [],
        }

        # Fill in the services
        for service_name, service_details in appwrite_docker_compose[
            "services"
        ].items():
            # Determine the service identifier for Coolify
            service_id = (
                f"$$id-{service_name}" if service_name != "appwrite" else "$$id"
            )

            # Create a dictionary for the service
            coolify_service = {
                "name": service_name.capitalize(),
                "image": service_details.get("image", "").replace(
                    "${APPWRITE_VERSION}", "$$core_version"
                ),
                "depends_on": service_details.get("depends_on", []),
                "volumes": service_details.get("volumes", []),
                "environment": [
                    f"{key}=$${{{'secret' if 'PASS' in key or 'SECRET' in key else 'config'}}}_{key}"
                    for key in service_details.get("environment", [])
                ],
            }

            # Add any additional keys that might be relevant (ports, ulimits, etc.)
            for key, value in service_details.items():
                if key not in ["image", "depends_on", "volumes", "environment"]:
                    coolify_service[key] = value

            # Add the service to the Coolify template
            coolify_template["services"][service_id] = coolify_service

        # Fill in the variables
        for service_name, service_details in appwrite_docker_compose[
            "services"
        ].items():
            for env_var in service_details.get("environment", []):
                variable_type = (
                    "secret" if "PASS" in env_var or "SECRET" in env_var else "config"
                )
                coolify_var = {
                    "id": f"$${variable_type}_{env_var}",
                    "name": env_var,
                    "label": env_var,
                    "defaultValue": "",
                    "description": f"{service_name.capitalize()} {env_var} setting.",
                    "required": True,
                }

                coolify_template["variables"].append(coolify_var)

        # Convert to YAML

        coolify_template_yaml = yaml.dump(coolify_template, default_flow_style=False)
        return coolify_template_yaml

    def extract_env_variables(self, file_path: str):
        """
        Extracts all ENV variables from a Docker-Compose YAML file
        """
        env_vars = set()
        with open(file_path, "r") as f:
            docker_compose = yaml.safe_load(f)

        print(f"Docker-compose file: {json.dumps(docker_compose)}")
        for service, config in docker_compose.get("services", {}).items():
            envs = config.get("environment", [])

            # The environment variables can be in either dict or list format
            # Handle both cases
            if isinstance(envs, dict):
                env_vars.update(envs.keys())
            elif isinstance(envs, list):
                for env in envs:
                    # Extract the variable name from "VAR=value" format
                    var_name = env.split("=")[0]
                    env_vars.add(var_name)
        return env_vars

    def extract_from_coolify(self, coolify_file: str) -> list[CoolifyVariable]:
        """
        Extracts all known variables from a Coolify YAML if it exists to make our life easier
        """
        with open(coolify_file, "r") as f:
            docker_compose = yaml.safe_load(f)

        coolify_vars: list[CoolifyVariable] = []
        variables = docker_compose.get("variables", [])
        for variable in variables:
            coolify_vars.append(CoolifyVariable(**variable))

        return coolify_vars

    def format_env_variables(
        self,
        env_vars: set,
        existing_vars: list[CoolifyVariable] = [],
    ):
        """
        Formats the ENV variables into a string that can be used in a Dockerfile
        """
        formatted_vars = "variables:\n"
        if len(existing_vars) > 0:
            for yaml_var in existing_vars:
                if yaml_var.name in env_vars:
                    formatted_vars += f"  - id: {yaml_var.id}\n    name: {yaml_var.name}\n    label: {yaml_var.label}\n    defaultValue: {yaml_var.defaultValue}\n    description: {yaml_var.description}\n"
                    env_vars.remove(yaml_var.name)
        for var in env_vars:
            formatted_vars += f"  - id: $$config_{str(var).lower()}\n    name: {var}\n    label: {var}\n    defaultValue: ''\n    description: ''\n"
        return formatted_vars


file_path = "docker-compose.yaml"
with open(file_path, "r") as f:
    docker_compose = f.read()
env_vars = Converter.get_instance().convert_to_coolify_template(docker_compose)
print(f"Converted docker-compose: {env_vars}")
with open("test-appwrite.yaml", "w+") as f:
    f.write(env_vars)
# coolify_vars = Converter.get_instance().extract_from_coolify(
#     "coolify-example-appwrite.yaml"
# )
# print(f"Extracted Coolify Variables: {coolify_vars}")
# formatted_vars = Converter.get_instance().format_env_variables(env_vars, coolify_vars)
# print(f"Formatted Variables: {formatted_vars}")
