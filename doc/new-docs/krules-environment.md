# The KRules environment

> ***NOTE: This document is for advanced users. If you need to learn the basics, why don't you check [the basic concepts](./concepts) or the [getting started guide](./getting-started)?***

The Krules framework comes with a predefined set of environment variables you can configure in different ways, let's see what they are and what is their purpose.

## Setting up the environment

To set up the environment you have multiple ways:

1. The standard `export VARIABLE="value" approach`: This sets an environment variable which will be captured by the build process
2. `env.local` and `env.project` files:
  Think of them as you think as the `.env` file (dotenv approach) in which the `env.local` file is used for local development while `env.project` represents the environment of the destination cluster. 

With environments, the following priority applies:

```
environment variable > variable in env.local > variable in env.project
```

## Environment Reference

The KRules environment variable can be summarized by the following table

| Variable Name            | Required | Default value        | Description 
|--------------------------|----------|----------------------|--------------------
| `"NAMESPACE"`            | true     | `""`                 | The name of the Kubernetes namespace in which the framework runs 
| `"DOCKER_REGISTRY"`      | true     | `""`                 | The URL of the docker registry from where to push the built images of the various components of the framework (including the built rulesets)
| `"INSTALL_IPYTHON"`      | false    | `""`                 | Installs [IPython](https://ipython.org) if set to `"1"`, does not otherwise
| `"KUBECTL_CMD"`          | false    | `"$(which kubectl)"` | The path of the `kubectl` executable in your system
| `"KUBECTL_OPTS"`         | false    | `""`                 | The `kubectl` executable custom flags
| `"KN_CMD"`               | false    | `"$(which kn)"`      | The path of the `kn` executable in your system
| `"KN_OPTS"`              | false    | `""`                 | The `kn` executable custom flags
| `"SUPPORTS_MYSQL"`       | false    | `""`                 | Enables the support for MySQL database clusters
| `"SUPPORTS_POSTGRESQL"`  | false    | `""`                 | Enables the support for MySQL database clusters