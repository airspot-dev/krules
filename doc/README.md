# Documentation generator

With this packet you can generate 

## Setup environment

Install requirements running:

```
$ pip install -r requirements.txt
```

## Build documentation site

To build documentation site run:

```
$ make multiversion
```

This command will create a site subdirectory inside **build/html** for each tag in this repository
and one for the develop branch.

Each file which compose documentations is located in **source** folder.
