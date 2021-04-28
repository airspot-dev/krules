# Documentation generator

With this packet you can generate KRules documentation in your local machine.

## Setup environment

Install requirements running:

```
$ pip install -r requirements.txt
```

## Build documentation site

To start to build documentation first you have to synchronize your local git with the remote one:

```
$ git fetch --all
```

After this you can finally build your doc running:

```
$ make multiversion
```

This command will create a site subdirectory inside **build/html/en** for each tag in this repository
and one for the develop branch.
