"""
# Create a generic service

The following environment variables are set in **.env** file

- **APP_NAME**: It'll be the name of the service. If not set defaults to destination directory name
- **IMAGE_NAME**: Name of the image that will be built. If not set defaults to ${PROJECT_NAME}-${APP_NAME}
- **SERVICE_API**: If set to **base** (default) a standard kubernetes deployment and service (if SERVICE_TYPE!="") will be created.
  If set to **knative** a knative service will be created and by default exposed to the internet.
- **SERVICE_TYPE**: Only when SERVICE_API == "base". Defaults to LoadBalancer.
  If set to an empty string no service will be created (just the deployment).
"""

import mdv
import os

def on_create(ctx, click, dest, env: dict, tag: str = None) -> bool:

    def _get_var(var, default):
        if var in env:
            return env[var]
        elif var in os.environ:
            return os.environ[var]
        else:
            return default()

    env_file = []
    out = []

    # app name
    app_name = _get_var("APP_NAME", lambda: os.path.split(dest)[-1])
    out.append(f"- **APP_NAME**: {app_name}")
    env_file.append(f"APP_NAME={app_name}")
    # image name
    image_name = _get_var("IMAGE_NAME", lambda: "${PROJECT_NAME}-${APP_NAME}")
    out.append(f"- **IMAGE_NAME**: {image_name}")
    env_file.append(f"IMAGE_NAME={image_name}")
    # service api
    service_api = _get_var("SERVICE_API", lambda: "base")
    out.append(f"- **SERVICE_API**: {service_api}")
    env_file.append(f"SERVICE_API={service_api}")
    # service type
    service_type = _get_var("SERVICE_TYPE", lambda: "ClusterIP")
    out.append(f"- **SERVICE_TYPE**: {service_type}")
    env_file.append(f"SERVICE_TYPE={service_type}")

    open(os.path.join(dest, ".env"), "w").write("\n".join(env_file))

    click.echo(mdv.main("\n\n".join(out)))

    return True
