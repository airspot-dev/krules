import importlib
import shutil

import click
import os
import tempfile
import git
import sys
import mdv

from . import NameValuePairType


@click.group(help="Deal with code templates")
@click.option("-r", "--remote-url", help="KRules repo url (default: https://github.com/airspot-dev/krules)", default="https://github.com/airspot-dev/krules")
@click.option("-b", "--branch", help="KRules repo branch (default: main)", default="main")
@click.option("-d", "--templates-dir", help="Path of the directory containing templates in the repo (default: templates)", default="templates")
@click.pass_context
def scaffold(ctx, remote_url, branch, templates_dir):
    cur_dir = os.getcwd()
    temp_dir = tempfile.TemporaryDirectory()
    ctx.obj = {
        "cur_dir": cur_dir,
    }
    os.chdir(temp_dir.name)
    repo = git.Repo.init(temp_dir.name)
    repo.config_writer().set_value("core", "sparsecheckout", "true").release()
    with open(os.path.join(temp_dir.name, ".git", "info", "sparse-checkout"), "w") as f:
        f.write(templates_dir)
    remote = repo.create_remote("origin", remote_url)
    try:
        remote.fetch()
        branch_ref = getattr(remote.refs, branch, None)
        if branch_ref is None:
            click.secho(f"branch {branch} does not exists", fg="red", err=True)
            sys.exit(-1)
        repo.create_head('master', branch_ref)  # create local branch "master" from remote banch
        repo.heads.master.checkout()
        # get current tag (release version)
        for tag in repo.tags:
            if tag.commit.hexsha == repo.head.commit.hexsha:
                click.echo(f"Current tag: {tag}")
                open(os.path.join(temp_dir.name, ".tag"), "w").write(tag.name)
                break
    except git.exc.GitCommandError as ex:
        click.secho(ex, fg="red", err=True)
        sys.exit(-1)
    local_templates_dir = os.path.join(temp_dir.name, templates_dir)
    if not os.path.exists(local_templates_dir) or not os.path.isdir(local_templates_dir):
        click.secho("source repository does not contains a templates location", fg="red", err=True)
        sys.exit(-1)
    ctx.obj["temp_dir"] = temp_dir


def __hook_template_module(templates_folder, name):
    target = os.path.join(templates_folder, name)
    template_spec_file = os.path.join(target, "__hook__.py")
    if os.path.exists(template_spec_file):
        spec = importlib.util.spec_from_file_location(f"hook_template_{name}_spec", template_spec_file)
        spec_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = spec_module
        spec.loader.exec_module(spec_module)
        return spec_module
    return None



@scaffold.command(help="Checkout template in destination folder")
@click.argument("template")
@click.argument("dest", default=".")
@click.option("-e", "--env", help="environment variables (accept multiple)", multiple=True, default=[],
              type=NameValuePairType())
@click.pass_context
def create(ctx, template, dest, env):
    tag = None
    if os.path.exists(os.path.join(ctx.obj['temp_dir'].name, ".tag")):
        tag = open(os.path.join(ctx.obj['temp_dir'].name, ".tag"), "r").read()
    local_templates_dir = os.path.join(ctx.obj['temp_dir'].name, ctx.parent.params["templates_dir"])
    if template not in os.listdir(local_templates_dir):
        click.secho(f"template {template} does not exists", fg="red", err=True)
        sys.exit(-1)
    dest = os.path.join(ctx.obj['cur_dir'], dest)
    if os.path.exists(dest):
        dest = os.path.join(dest, template)
        if os.path.exists(dest):
            click.secho(f"{dest} already exists", fg="red", err=True)
            sys.exit(-1)
    try:
        shutil.copytree(os.path.join(local_templates_dir, template), dest)
    except Exception as ex:
        click.secho(ex, fg="red", err=True)
        shutil.rmtree(dest)
        sys.exit(-1)
    hook_mod = __hook_template_module(os.path.split(dest)[0], os.path.split(dest)[1])
    got_errors = False
    if hook_mod is not None and hasattr(hook_mod, "on_create"):
        env_d = {}
        for name, value in env:
            env_d[name.upper()] = value
        got_errors = not hook_mod.on_create(ctx, click, dest, env_d, tag)
        os.unlink(os.path.join(dest, "__hook__.py"))
        shutil.rmtree(os.path.join(dest, "__pycache__"), ignore_errors=True)
    if got_errors:
        shutil.rmtree(dest)
        click.secho("Hook got errors", fg="red", err=True)
        sys.exit(-1)

    click.secho("Done", fg="green")


@scaffold.command(help="Show available templates")
@click.pass_context
def list(ctx):
    local_templates_dir = os.path.join(ctx.obj['temp_dir'].name, ctx.parent.params["templates_dir"])
    out = []
    for template in os.listdir(local_templates_dir):
        if not os.path.isdir(os.path.join(local_templates_dir, template)):
            continue
        hook_mod = __hook_template_module(local_templates_dir, template)
        abstract = ""
        doc_lines = hook_mod.__doc__.strip("\n# ").splitlines()
        if len(doc_lines):
            abstract = doc_lines[0]
        out.append(" ".join((f"**{template}**".ljust(15), abstract)))
    click.echo(mdv.main("\n\n".join(out)))

@scaffold.command(help="Get info about template")
@click.argument("template")
@click.pass_context
def info(ctx, template):
    local_templates_dir = os.path.join(ctx.obj['temp_dir'].name, ctx.parent.params["templates_dir"])
    if template not in os.listdir(local_templates_dir):
        click.secho(f"template {template} does not exists", fg="red", err=True)
        sys.exit(-1)
    hook_mod = __hook_template_module(local_templates_dir, template)
    click.echo(mdv.main(hook_mod.__doc__.strip()))
