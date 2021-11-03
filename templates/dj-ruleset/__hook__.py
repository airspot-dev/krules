"""
# Bootstrap a ruleset using the Django environment

- **APP_NAME**: It'll be the name of the ruleset service. If not set defaults to 'django-' prefixed destination directory name
- **IMAGE_NAME**: Name of the image that will be built. If not set defaults to ${PROJECT_NAME}-${APP_NAME}
- **SERVICE_API**: If set to **base** (default) a standard kubernetes deployment and service will be created.
  If set to **knative** a knative service will be created with cluster-local visibility
- **SERVICE_TYPE**: Only when SERVICE_API=="base". Defaults to 'LoadBalancer'

**NOTE**: if you are creating the ruleset in a subfolder of the Django instance created by its template,
the following variables will bi inherited:
- **DJANGO_BACKEND_POSTGRESQL**
- **DJANGO_BACKEND_MYSQL=1**
- **SITE_NAME**
- **CONFIGURATION_KEY**

If you want to place the folder somewhere else in the project you will need to make sure that at least the database
 support is specified according to the reference Django instance.
 Eventually you can set the variables at the root of the project.
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

    env_override_file = []
    out = []

    # app name
    app_name = _get_var("APP_NAME", lambda: "django-{}".format(os.path.split(dest)[-1]))
    out.append(f"- **APP_NAME**: {app_name}")
    env_override_file.append(f"APP_NAME={app_name}")
    # image name
    image_name = _get_var("IMAGE_NAME", lambda: "${PROJECT_NAME}-${APP_NAME}")
    out.append(f"- **IMAGE_NAME**: {image_name}")
    env_override_file.append(f"IMAGE_NAME={image_name}")
    # service api
    service_api = _get_var("SERVICE_API", lambda: "base")
    out.append(f"- **SERVICE_API**: {service_api}")
    env_override_file.append(f"SERVICE_API={service_api}")
    # service type
    if service_api != "knative":
        service_type = _get_var("SERVICE_TYPE", lambda: "LoadBalancer")
        out.append(f"- **SERVICE_TYPE**: {service_type}")
        env_override_file.append(f"SERVICE_TYPE={service_type}")

    open(os.path.join(dest, ".env"), "w").write("\n".join(env_override_file))

    return True
