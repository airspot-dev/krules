import click


class NameValuePairType(click.ParamType):

    name = "name=value"

    def convert(self, value, param, ctx):

        pair = value.split("=")
        if not len(pair) == 2:
            self.fail(f"you must provide a NAME=VALUE pair", param, ctx)
        return pair
