"""
# Start a new project

It can be customized setting up environment variables at two different levels
> Note that all variables can be overridden setting them directly in the calling environment

## Project level
Are defined in **env.project** file and are part of the project itself (included in code repository)

  - **PROJECT_NAME**: Name of the project. If not set defaults to destination directory name
  - **RELEASE_DOCKER_REGISTRY**: Registry from which release image versions are pulled. By defult gcr.io/airspot

## Local development or separate deployment environments
Are defined in **env.local** file which is excluded from the code repository
These variables can be used to distinguish different deployments environments like
for local user *development* or different target environments such as *staging* or *production*

  - **NAMESPACE**: It must be set in order to deploy resources
  - **DOCKER_REGISTRY**: It must be set in order build and push images
  - **KUBECTL_CMD**: Your Kubernetes client. Defaults to **kubectl**
  - **KUBECTL_OPTS**: Any KUBECTL_CMD options. For example "--context=..."
  - **KN_CMD**: Knative client. Defaults to **kn**
  - **KN_OPTS**: Any KN_CMD options. For example "--context=..."





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

    env_project = []
    env_local = []
    out = []
    warns = []

    out.append("Setting up **env.project**")
    if tag is not None and tag.startswith("v"):
        env_project.append(f"RELEASE_VERSION={tag[1:]}")
        out.append(f"- **RELEASE_VERSION**: {tag[1:]}")

    # project name
    project_name = _get_var("PROJECT_NAME", lambda: os.path.split(dest)[-1])
    out.append(f"- **PROJECT_NAME**: {project_name}")
    env_project.append(f"PROJECT_NAME={project_name}")
    # release docker registry
    release_docker_registry = _get_var("RELEASE_DOCKER_REGISTRY", lambda: "gcr.io/airspot")
    out.append(f"- **RELEASE_DOCKER_REGISTRY**: {release_docker_registry}")
    env_project.append(f"RELEASE_DOCKER_REGISTRY={release_docker_registry}")


    open(os.path.join(dest, "env.project"), "w").write("\n".join(env_project))

    out.append("Setting up **env.local**")
    # namespace
    namespace = _get_var("NAMESPACE", lambda: None)
    if namespace is None:
        warns.append("NAMESPACE must be set in env.local!")
        env_local.append(f"#NAMESPACE=")
        out.append(f"- **NAMESPACE**: *not set!*")
    else:
        env_local.append(f"NAMESPACE={namespace}")
        out.append(f"- **NAMESPACE**: {namespace}")
    # docker registry
    docker_registry = _get_var("DOCKER_REGISTRY", lambda: None)
    if docker_registry is None:
        warns.append("DOCKER_REGISTRY must be set in env.local!")
        env_local.append(f"#DOCKER_REGISTRY=")
        out.append(f"- **DOCKER_REGISTRY**: *not set!*")
    else:
        env_local.append(f"DOCKER_REGISTRY={docker_registry}")
        out.append(f"- **DOCKER_REGISTRY**: {docker_registry}")

    # kubectl
    kubectl_cmd = _get_var("KUBECTL_CMD", lambda: "kubectl")
    out.append(f"- **KUBECTL_CMD**: {kubectl_cmd}")
    env_local.append(f"KUBECTL_CMD={kubectl_cmd}")
    # kubectl opts
    kubectl_opts = _get_var("KUBECTL_OPTS", lambda: "")
    out.append(f"- **KUBECTL_OPTS**: {kubectl_opts}")
    env_local.append(f"KUBECTL_OPTS={kubectl_opts}")
    # kn
    kn_cmd = _get_var("KN_CMD", lambda: "kn")
    out.append(f"- **KN_CMD**: {kn_cmd}")
    env_local.append(f"KN_CMD={kn_cmd}")
    # kn opts
    kn_opts = _get_var("KN_OPTS", lambda: "")
    out.append(f"- **KN_OPTS**: {kn_opts}")
    env_local.append(f"KN_OPTS={kn_opts}")

    open(os.path.join(dest, "env.local"), "w").write("\n".join(env_local))

    click.echo(mdv.main("\n\n".join(out)))

    if len(warns):
        click.secho("!!WARNINGS!!", fg="yellow", err=True)
    for warn in warns:
        click.secho(warn, fg="yellow", err=True)

    return True
