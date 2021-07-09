"""
##Start a new project
===

It can be customized setting up environment variables at two different levels

1. **Project level**: are defined in **env.project** and are part of the project itself (included in code repository)

- **PROJECT_NAME**: Name of the project
- **NAMESPACE**: It is mandatory

"""


def on_create(ctx, click, dest, env: dict) -> bool:
    import pdb;
    pdb.set_trace()
    return True
