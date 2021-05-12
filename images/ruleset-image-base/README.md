# ruleset-image-base

Package to build and deploy ruleset image base, could be both develop or release.

## Setup environment

First you have to configure **DOCKER_REGISTRY** in your environment:

```
$ export DOCKER_REGISTRY=your-docker-registry
```

## Build develop image

To build a develop version just run:

```
$ make develop
```

This command will build your image and push it to your Docker registry.

Furthermore, it stores the newest image develop version in a file called _.digest_.

So you can retrieve it running:

```
$ cat .digest
gcr.io/airspot/ruleset-image-base@sha256:8dd409aa649d8e20ae7d388c1d1fe01986d6f0af228be2093ea14cd356cc3a43
```

## Build release image

To build a release version it necessary to set a **RELEASE_VERSION**.

Once you did this, you can run:

```
$ make release
```

As the previous one, also this command will build your image and push it to your Docker registry.

Although, in this case digest will not be store in a file because the image was tagged with the
configured **release version** during the build phase.

You can also refer to it just with the **latest** tag.