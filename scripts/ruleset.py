#!/usr/bin/env python
import hashlib
import json
import os
import pprint
import sys
import importlib
import argparse
import re
from pathlib import Path
import logging

import io
import pykube
import subprocess
from io import BytesIO

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)
logger_formatter = logging.Formatter('[%(name)s %(levelname)s]> %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

# import script module
spec = importlib.util.spec_from_file_location("script_module", os.path.join(sys.path[0], "__init__.py"))
script_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = script_module
spec.loader.exec_module(script_module)

parser = argparse.ArgumentParser(description="Manage rulesets")

parser.add_argument("-l", type=int, dest="level", default=logging.INFO, help="logging level")
subparsers = parser.add_subparsers(dest="action", title="actions")

create_parser = subparsers.add_parser("create", help="create ruleset skeleton directory")


def _ruleset_name_type(arg_value, p=re.compile(r"^[0-9a-z\-]+$")):
    if not p.match(arg_value):
        raise argparse.ArgumentTypeError("name can contain only lower letters, numbers and the '-' character")
    return arg_value


create_parser.add_argument("name", type=_ruleset_name_type, help="the path where the ruleset is to be created")
create_parser.add_argument("-p", type=str, default=os.getcwd(), dest="path", help="base dir (default cur dir)")

deploy_parser = subparsers.add_parser("deploy", help="buid and deploy ruleset")
deploy_parser.add_argument("-p", type=str, default=os.getcwd(), dest="path", help="ruleset dir")
deploy_parser.add_argument("-n", type=str, default=os.environ.get("NAMESPACE", None), dest="namespace",
                           help="namespace to deploy to (dafault from env var NAMESPACE if present)")
deploy_parser.add_argument("--docker-registry", type=str, default=os.environ.get("DOCKER_REGISTRY", None),
                           dest="registry",
                           help="docker registry (dafault from env var DOCKER_REGISTRY)")

def _hashed(name, *args, length=10):
    hash = ""
    for arg in args:
        hash += pprint.pformat(arg)
    return "{}-{}".format(name, hashlib.md5(hash.encode("utf8")).hexdigest()[:length])

def _resolve_broker(api, ksvc_sink, namespace):
    global logger
    if ksvc_sink.startswith("broker:"):
        broker = ksvc_sink.split(":")[1]
        try:
            obj = pykube.object_factory(api, "eventing.knative.dev/v1", "Broker").objects(api).filter(
                namespace=namespace
            ).get(name=broker)
        except pykube.exceptions.ObjectDoesNotExist:
            logger.critical(f"broker {broker} not found")
            sys.exit(1)
        ksvc_sink = obj.obj.get("status").get("address").get("url")
        logger.debug(f"ksvc_sink: {ksvc_sink}")
    return ksvc_sink


def cmd_deploy(spec_module, path, namespace, registry):
    global logger
    global script_module

    logger.debug("cmd_deploy for ruleset {} in {}".format(spec_module.name, path))

    if registry is None:
        logger.critical("DOCKER_REGISTRY not set")
        sys.exit(1)

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())
    if namespace is None:
        namespace = api.config.namespace
    logger.debug(f"using namespace {namespace}")

    # Get docker base image
    try:
        cm = pykube.ConfigMap.objects(api).filter(namespace=namespace).get(name="config-krules-project")
    except pykube.exceptions.ObjectDoesNotExist:
        logger.critical("config-krules-project configmap not found")
        sys.exit(1)

    try:
        image_base = cm.obj.get("data", {})["imageBase"]
    except KeyError:
        logger.critical("imageBase not found in config-krules-project configmap")
        sys.exit(1)
    logger.debug(f"imageBase: {image_base}")

    # Build and push the ruleset image
    add_section = io.StringIO("")
    for f in getattr(spec_module, "add_files", ()):
        logger.debug(f"adding file '{f}' to resulting contaner")
        print(f"ADD {f} /app/{f}", file=add_section)
    add_modules = getattr(spec_module, "add_modules", True)
    if add_modules:
        for mdir in [mdir for mdir in os.listdir(path) if os.path.exists(os.path.join(path, mdir, "__init__.py"))]:
            logger.debug(f"adding module '{mdir}' to resulting container")
            print(f"ADD {mdir}/ /app/{mdir}/", file=add_section)
    extra_commands = io.StringIO("")
    for c in getattr(spec_module, "extra_commands", ()):
        logger.debug(f"adding '{c[0]}' command to resulting container")
        print(" ".join(c), file=extra_commands)

    logger.debug("build image locally")
    tag = "{}/{}".format(registry, spec_module.name)
    dockerfile = script_module.dockerfile_skel.format(
        image_base=image_base,
        add_section=add_section.getvalue(),
        extra_commands=extra_commands.getvalue()
    )
    logger.debug(f"Dockerfile:\n{dockerfile}")
    ret = subprocess.run(("docker", "build", path, f"-t{tag}", "-f-"),
                         input=bytes(dockerfile, encoding='utf-8'))
    if ret.returncode > 0:
        logger.critical("docker build failed")
        sys.exit(ret.returncode)
    logger.debug(f"push {tag} image to registry")
    ret = subprocess.run(("docker", "push",  f"{tag}"))
    if ret.returncode > 0:
        logger.critical("docker push failed")
        sys.exit(ret.returncode)
    # retrieve pushed image digest
    ret = subprocess.run(("docker", "inspect", "--format='{{index .RepoDigests 0}}'", tag), capture_output=True)
    if ret.returncode > 0:
        logger.critical("failed to fetch image digest")
        sys.exit(ret.returncode)
    digest = eval(ret.stdout.decode("utf-8"))

    # Create/Update Knative service
    labels = getattr(spec_module, "labels", {"serving.knative.dev/visibility": "cluster-local",
                                             "krules.airspot.dev/type": "ruleset"})
    template_annotations = getattr(spec_module, "template_annotations", {})
    ksvc_sink = _resolve_broker(api, getattr(spec_module, "ksvc_sink", "broker:default"), namespace)
    ksvc_procevents_sink = _resolve_broker(api, getattr(spec_module, "ksvc_procevents_sink", "broker:procevents"), namespace)

    service_account = getattr(spec_module, "service_account", "")
    extra_environ = getattr(spec_module, "environ", {})
    environ = [
        {
            "name": "K_SINK",
            "value": ksvc_sink,
        },
        {
            "name": "K_PROCEVENTS_SINK",
            "value": ksvc_procevents_sink
        }
    ]
    for k, v in extra_environ.items():
        environ.append({
            "name": k,
            "value": v,
        })

    logger.debug(f"service account: {service_account}")

    revision_name = _hashed(spec_module.name, #labels,
                            template_annotations, ksvc_sink, ksvc_procevents_sink, service_account, digest, service_account)
    logger.info(f"Revision name: {revision_name}")

    obj_ref = pykube.object_factory(
        api, "serving.knative.dev/v1", "Service"
    ).objects(api).get_or_none(name=spec_module.name)
    if obj_ref is None:
        logger.debug("creating object..")

        obj = {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": spec_module.name,
                "labels": labels
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": revision_name,
                        "annotations": template_annotations,
                        #"labels": labels
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "ruleset",
                                "image": digest,
                                "env": environ
                            }
                        ]
                    }
                },
            }
        }
        if service_account != "":
            obj["spec"]["template"]["spec"]["serviceAccountName"] = service_account

        pykube.object_factory(api, "serving.knative.dev/v1", "Service")(api, obj).create()
        logger.info(f"Ruleset '{spec_module.name}' created")
    else:
        logger.debug("object exists..")
        obj_ref.obj["metadata"]["labels"] = labels
        obj_ref.obj["spec"]["template"]["metadata"]["name"] = revision_name
        if "anntations" in obj_ref.obj["spec"]["template"]["metadata"]:
            obj_ref.obj["spec"]["template"]["metadata"]["annotations"].update(template_annotations)
        else:
            obj_ref.obj["spec"]["template"]["metadata"]["annotations"] = template_annotations
        containers = obj_ref.obj["spec"]["template"]["spec"]["containers"]
        for container in containers:
            if container["name"] == "ruleset":
                container["image"] = digest
            envs = {e["name"]: e["value"] for e in container["env"]}
            envs["K_SINK"] = ksvc_sink
            envs["K_PROCEVENTS_SINK"] = ksvc_procevents_sink
            envs.update(extra_environ)
            container["env"] = [{"name": k, "value": v} for k, v in envs.items()]

        if service_account != "":
            obj_ref.obj["spec"]["template"]["spec"]["serviceAccountName"] = service_account

        obj_ref.update()
        logger.info(f"Ruleset '{spec_module.name}' updated")

    # Create/Update triggers
    triggers = getattr(spec_module, "triggers", ())
    for trigger in triggers:
        try:
            obj_ref = pykube.object_factory(
                api, "eventing.knative.dev/v1", "Trigger"
            ).objects(api).get_or_none(name=trigger.get("name"))
            if obj_ref is None:
                name=trigger.pop('name')
                logging.debug(f"creating trigger {name}")
                trigger.update({
                    "subscriber": {
                        "ref": {
                            "apiVersion": "serving.knative.dev/v1",
                            "kind": "Service",
                            "name": spec_module.name,
                            "namespace": namespace,
                        }
                    }
                })
                obj = {
                    "apiVersion": "eventing.knative.dev/v1",
                    "kind": "Trigger",
                    "metadata": {
                        "name": name,
                        "namespace": namespace,
                        "labels": {
                            "krules.airspot.dev/owned-by": spec_module.name,
                        },
                    },
                    "spec": trigger,

                }
                if obj["spec"].get("broker") is None:
                    obj["spec"]["broker"] = getattr(spec_module, "triggers_default_broker", "default")
                pykube.object_factory(api, "eventing.knative.dev/v1", "Trigger")(api, obj).create()
                logger.info(f"Trigger {obj['metadata']['name']} created")
            else:
                name = trigger.pop("name")
                trigger["subscriber"] = obj_ref.obj["spec"]["subscriber"]
                obj_ref.obj["spec"].update(trigger)
                obj_ref.update()
                logger.info(f"Trigger {name} updated")
        except Exception as ex:
            logger.error(f"Error processing trigger:\n{trigger}")
            logger.exception(ex)

def main():
    global logger

    args = vars(parser.parse_args())
    logger.setLevel(args.get("level"))

    action = args.get("action")
    if action == "create":
        name = args.get("name")
        ruleset_dir = Path(os.path.join(args.get("path"), name)).resolve()
        Path(ruleset_dir).mkdir(exist_ok=True)
        p_deploy = Path(os.path.join(ruleset_dir, "__deploy__.py"))
        if p_deploy.exists():
            logger.warning("__deploy__.py already exists.. skipped")
        else:
            p_deploy.write_text(
                script_module.deploy_py.format(name=name)
            )
        p_ruleset = Path(os.path.join(ruleset_dir, "ruleset.py"))
        # create empty ruleset function module
        Path(os.path.join(ruleset_dir, "ruleset_functions")).mkdir(exist_ok=True)
        p_init_module = Path(os.path.join(ruleset_dir, "ruleset_functions", "__init__.py"))
        if p_init_module.exists():
            logger.warning("ruleset_functions/__init__.py already exists.. skipped")
        else:
            p_init_module.write_text(
                script_module.ruleset_functions__init__py
            )

        if p_ruleset.exists():
            logger.warning("ruleset.py already exists.. skipped")
        else:
            p_ruleset.write_text(
                script_module.ruleset_py
            )

        p_readme = Path(os.path.join(ruleset_dir, "README.md"))
        if p_readme.exists():
            logger.warning("README.md already exists.. skipped")
        else:
            p_readme.write_text(
                script_module.README.format(name=name)
            )

    elif action == "deploy":
        path = Path(args.get("path")).resolve()
        spec = importlib.util.spec_from_file_location("deploy_spec", os.path.join(path, "__deploy__.py"))
        deploy_spec_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = deploy_spec_module
        spec.loader.exec_module(deploy_spec_module)

        cmd_deploy(deploy_spec_module, path, args.get("namespace"), args.get("registry"))
    else:
        parser.print_help(sys.stderr)


if __name__ == "__main__":
    main()
