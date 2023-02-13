"""
# Start a new project leveraging the Google Cloud Platform build and deployment tools.

It uses Cloud Build and Cloud Deploy to manage two different deployment targets.

In this provided configuration the two environments are located in two different namespaces on the same cluster, but it can be adjusted to work with different cluster and different project

It can be customized setting up environment variables at two different levels
> Note that all variables can be overridden setting them directly in the calling environment

## Project level
Are defined in **env.project** file and are part of the project itself (included in code repository)

  - **PROJECT_NAME**: Name of the project. If not set defaults to destination directory name
  - **RELEASE_DOCKER_REGISTRY**: Registry from which release image versions are pulled. By default, gcr.io/airspot

## Local development or separate deployment environments
Are defined in **env.local** file which is excluded from the code repository
These variables can be used to distinguish different deployments environments like
for local user *development* or different target environments such as *staging* or *production*

  - **TARGETS**: String containing targets name separated by ";" " " or ","
  - **PROJECT_ID**: Your GCP project ID
  - **REGION**: Your GKE cluster region
  - **ZONE**: Your GKE cluster zone
  - **CLUSTER**: Your GKE cluster name




"""
import os
import re

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
    # targets
    env_targets = _get_var("TARGETS", lambda: None)
    targets = []
    if env_targets is None:
        out.append(f"- **TARGETS**: *not set, dev;stable will be used*")
        env_local.append(f"TARGETS=\"dev;stable\"")
    else:
        targets = re.split(" |,|;", env_targets)
        if len(targets) == 1 and len(targets) == 0:
            warns.append("At least 1 target must be set!")
        env_local.append(f"TARGETS={env_targets}")
        out.append(f"- **TARGETS**: {env_targets}")

    # project_id
    project_id = _get_var("PROJECT_ID", lambda: None)
    if project_id is None:
        warns.append("PROJECT_ID must be set in env.local!")
        env_local.append(f"#PROJECT_ID=")
        out.append(f"- **PROJECT_ID**: *not set!*")
    else:
        env_local.append(f"PROJECT_ID={project_id}")
        out.append(f"- **PROJECT_ID**: {project_id}")
    # region
    region = _get_var("REGION", lambda: None)
    if region is None:
        warns.append("REGION must be set in env.local!")
        env_local.append(f"#REGION=")
        out.append(f"- **REGION**: *not set!*")
    else:
        env_local.append(f"REGION={region}")
        out.append(f"- **REGION**: {region}")
    # zone
    zone = _get_var("ZONE", lambda: None)
    if zone is None:
        warns.append("ZONE must be set in env.local!")
        env_local.append(f"#ZONE=")
        out.append(f"- **ZONE**: *not set!*")
    else:
        env_local.append(f"ZONE={zone}")
        out.append(f"- **ZONE**: {zone}")
    # cluster
    cluster = _get_var("CLUSTER", lambda: None)
    if cluster is None:
        warns.append("CLUSTER must be set in env.local!")
        env_local.append(f"#CLUSTER=")
        out.append(f"- **CLUSTER**: *not set!*")
    else:
        env_local.append(f"CLUSTER={cluster}")
        out.append(f"- **CLUSTER**: {cluster}")

    for index, target in enumerate(targets):
        env_local.append(f"{target.upper()}_NAMESPACE={project_name}-{target}")
        if index > 0:
            env_local.append(f"#{target.upper()}_REQUIRE_APPROVAL=\"true\"")

    open(os.path.join(dest, "env.local"), "w").write("\n".join(env_local))

    click.echo(mdv.main("\n\n".join(out)))

    if len(warns):
        click.secho("!!WARNINGS!!", fg="yellow", err=True)
    for warn in warns:
        click.secho(warn, fg="yellow", err=True)

    return True
