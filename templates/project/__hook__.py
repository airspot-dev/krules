"""
# Start a new project

It can be customized setting up environment variables at two different levels

## Project level
Are defined in **env.project** file and are part of the project itself (included in code repository)

  - **PROJECT_NAME**: Name of the project


## Local development or separate deployment environments
Are defined in **env.local** file which is excluded from the code repository
These variables can be used to distinguish different deployments environments like
for local user *development* or different target environemnts such as *staging* or *production*

  - **NAMESPACE**: It must be set in order to deploy resources

---

> Note that all variables can be overridden setting them directly in the caller environment

"""
import os
import mdv


def on_create(ctx, click, dest, env: dict) -> bool:

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
    # project name
    project_name = _get_var("PROJECT_NAME", lambda: os.path.split(dest)[-1])
    out.append(f"- **PROJECT_NAME**: {project_name}")
    env_project.append(f"PROJECT_NAME={project_name}")

    open(os.path.join(dest, "env.project"), "w").write("\n".join(env_project))

    out.append("Setting up **env.local**")
    # namespace
    namespace = _get_var("NAMESPACE", lambda: None)
    if namespace is None:
        warns.append("NAMESPACE must be set in env.local!")
        env_local.append(f"#NAMESPACE=")
    else:
        env_local.append(f"NAMESPACE={namespace}")
    out.append(f"- **NAMESPACE**: *not set!*")

    open(os.path.join(dest, "env.project"), "w").write("\n".join(env_project))

    click.echo(mdv.main("\n".join(out)))

    if len(warns):
        click.secho("!!WARNINGS!!", fg="yellow", err=True)
    for warn in warns:
        click.secho(warn, fg="yellow", err=True)

    return True
