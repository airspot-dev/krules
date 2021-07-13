"""
# Start a new project

It can be customized setting up environment variables at two different levels
> Note that all variables can be overridden setting them directly in the calling environment

## Project level
Are defined in **env.project** file and are part of the project itself (included in code repository)

  - **PROJECT_NAME**: Name of the project. If not set defaults to destination directory name
  - **SUBJECTS_BACKENDS**: Defaults to **redis**. *mongodb* is also supported. They can be either be specified as single\
  or multiple choice (comma or space separated). In the latter case you need to adjust accordingly the **base/env.py**\
  file to specify the criterion by which one provider is used as an alternative to the other (usually according to the subject name).
  Note that in order to complete the configuration you also need to set up the relative provider in **base/k8s**
  - **SUPPORTS_POSTGRESQL**: defaults to **0** (disabled). Set to *1* to build postgresql support for all ruleset contaners
  - **SUPPORTS_MYSQL**: defaults to **0** (disabled). Set to *1* to build mysql support for all ruleset contaners

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
    # subjects backend
    subjects_backend = _get_var("SUBJECTS_BACKENDS", lambda: "redis")
    out.append(f"- **SUBJECTS_BACKENDS**: {subjects_backend}")
    env_project.append(f"SUBJECTS_BACKENDS={subjects_backend}")
    # postgresql support
    supports_postgresql = _get_var("SUPPORTS_POSTGRESQL", lambda: "0")
    out.append(f"- **SUPPORTS_POSTGRESQL**: {supports_postgresql}")
    env_project.append(f"SUPPORTS_POSTGRESQL={supports_postgresql}")
    # mysql support
    supports_mysql = _get_var("SUPPORTS_MYSQL", lambda: "0")
    out.append(f"- **SUPPORTS_MYSQL**: {supports_mysql}")
    env_project.append(f"SUPPORTS_MYSQL={supports_mysql}")


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

    open(os.path.join(dest, "env.local"), "w").write("\n".join(env_project))

    click.echo(mdv.main("\n\n".join(out)))

    if len(warns):
        click.secho("!!WARNINGS!!", fg="yellow", err=True)
    for warn in warns:
        click.secho(warn, fg="yellow", err=True)

    return True
