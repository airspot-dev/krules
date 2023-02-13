"""
# Create a new ruleset leveraging Google Cloud Deploy Deployment Pipeline

The following environment variables are set in **.env** file

- **APP_NAME**: It'll be the name of the ruleset service. If not set defaults to destination directory name
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
    out = []

    # app name
    app_name = _get_var("APP_NAME", lambda: os.path.split(dest)[-1])
    out.append(f"- **APP_NAME**: {app_name}")
    env_file.append(f"APP_NAME={app_name}")

    open(os.path.join(dest, ".env"), "w").write("\n".join(env_file))

    click.echo(mdv.main("\n\n".join(out)))

    return True