"""
# Bootstrap a Django customizable instance equipped with useful KRules extensions

The following environment variables are set in **.env** file

- **APP_NAME**: It'll be the name of the ruleset service. If not set defaults to destination directory name
- **IMAGE_NAME**: Name of the image that will be built. If not set defaults to ${PROJECT_NAME}-${APP_NAME}
- **SERVICE_API**: If set to **base** (default) a standard kubernetes deployment and service will be created.
  If set to **knative** a knative service will be created with cluster-local visibility
- **SERVICE_TYPE**: Only when SERVICE_API=="base". Defaults to 'LoadBalancer'
- **SITE_NAME**: Django site name. Defaults to 'djsite'.
- **CONFIGURATION_KEY**: Defaults to 'django'. It can be useful if you want to have multiple django instances
  to distinguish their injected configuration.

Depending on the target environment, the following variables are also set for database support.
__You must set at least one to "1"!__

- **DJANGO_BACKEND_POSTGRESQL**: PostgreSQL support
- **DJANGO_BACKEND_MYSQL=1**: MySql support

Also, as some additional rulesets will be deployed it is possible to set this variable as well

- **RULESETS_SERVICE_TYPE**: Defaults to 'base'
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

    env_file = []
    env_local_file = []
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
    if service_api != "knative":
        service_type = _get_var("SERVICE_TYPE", lambda: "LoadBalancer")
        out.append(f"- **SERVICE_TYPE**: {service_type}")
        env_file.append(f"SERVICE_TYPE={service_type}")
    # site name
    site_name = _get_var("SITE_NAME", lambda: "djsite")
    out.append(f"- **SITE_NAME**: {site_name}")
    env_file.append(f"SITE_NAME={site_name}")
    # configuration key
    configuration_key = _get_var("CONFIGURATION_KEY", lambda: "django")
    out.append(f"- **CONFIGURATION_KEY**: {configuration_key}")
    env_file.append(f"CONFIGURATION_KEY={configuration_key}")

    open(os.path.join(dest, ".env"), "w").write("\n".join(env_file))

    # postgresql support
    django_backend_postgresql = _get_var("DJANGO_BACKEND_POSTGRESQL", lambda: "0")
    out.append(f"- **DJANGO_BACKEND_POSTGRESQL**: {django_backend_postgresql}")
    env_local_file.append(f"DJANGO_BACKEND_POSTGRESQL={django_backend_postgresql}")
    # mysql support
    django_backend_mysql = _get_var("DJANGO_BACKEND_MYSQL", lambda: "0")
    out.append(f"- **DJANGO_BACKEND_MYSQL**: {django_backend_mysql}")
    env_local_file.append(f"DJANGO_BACKEND_MYSQL={django_backend_mysql}")

    if django_backend_postgresql == "0" and django_backend_mysql == "0":
        out.append("\n\n**__!!WARNING: AT LEAST ONE DATABASE BACKEND IS REQUIRED!!__**")

    open(os.path.join(dest, ".env.local"), "w").write("\n".join(env_local_file))

    click.echo(mdv.main("\n\n".join(out)))

    return True