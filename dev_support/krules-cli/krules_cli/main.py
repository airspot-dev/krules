import os

import click

cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "commands"))


class RootCommands(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__(f"krules_cli.commands.cmd_{name}", None, None, [name])
        except ImportError:
            return
        return getattr(mod, name)


@click.command(cls=RootCommands, help="KRules command line utilities")
def cli():
    pass

