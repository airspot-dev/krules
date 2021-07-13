"""
# Create a new ruleset

The following environment variables are set in **.env** file

- **APP_NAME**: It'll be the name of the ruleset service. If not set defaults to destination directory name
- **IMAGE_NAME**: Name of the image that will be built. If not set defaults to ${PROJECT_NAME}-${APP_NAME}
- **SERVICE_API**: If set to **base** (default) a standard kubernetes deployment and service (ClusterIP) will be created.
  If set to **knative** a knative service will be created with cluster-local visibility
"""
import os
import mdv


def on_create(ctx, click, dest, env: dict, tag: str = None) -> bool:

    def _get_var(var, default):
        if var in env:
            return env[var]
        elif var in os.environ:
            return os.environ[var]
        else:
            return default()

    env = []
    out = []

    # app name
    app_name = _get_var("APP_NAME", lambda: os.path.split(dest)[-1])
    out.append(f"- **APP_NAME**: {app_name}")
    env.append(f"APP_NAME={app_name}")
    # image name
    image_name = _get_var("IMAGE_NAME", lambda: "${PROJECT_NAME}-${APP_NAME}")
    out.append(f"- **IMAGE_NAME**: {image_name}")
    env.append(f"IMAGE_NAME={image_name}")
    # service api
    service_api = _get_var("SERVICE_API", lambda: "base")
    out.append(f"- **SERVICE_API**: {service_api}")
    env.append(f"SERVICE_API={service_api}")

    open(os.path.join(dest, ".env"), "w").write("\n".join(env))

    click.echo(mdv.main("\n\n".join(out)))
