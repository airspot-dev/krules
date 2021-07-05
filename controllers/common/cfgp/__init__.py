import copy
import pprint
import re
import typing
from typing import Any

import yaml

import jsonpath_rw_ext as jp


def _hashed(*args, length=10):
    import hashlib
    hash = ""
    for arg in args:
        hash += pprint.pformat(arg)
    return str(hashlib.md5(hash.encode("utf8")).hexdigest()[:length])


def apply_configuration(configuration: dict, dest: dict, root_expr: str, preserve_name: bool, _log=[]):

    _log.append(
        ("dest_before", copy.deepcopy(dest))
    )

    configuration_name = configuration.get("metadata").get("name")
    configuration_key = configuration.get("spec").get("key")
    destination_name = dest.get("metadata", {}).get("name")
    configuration_hash = _hashed(
        configuration["spec"].get("data", {}),
        configuration["spec"].get("container", {}),
        configuration["spec"].get("volumes", {}),
    )

    annotations = dest.get("metadata", {}).setdefault("annotations", {})
    prev_applied = yaml.load(annotations.setdefault("config.krules.airspot.dev/applied", "{}"), Loader=yaml.SafeLoader)
    prev_configuration_hash = prev_applied.get(configuration_name)

    if prev_configuration_hash == configuration_hash:
        return

    cm_name = "{}-{}".format(
        configuration.get("metadata", {}).get("name"),
        _hashed(
            configuration["spec"].get("data", {}),
        )
    )

    mount_path = "/krules/config/" + "/".join(configuration_key.split("."))

    template = jp.match1(root_expr, dest)
    _log.append(("root_expr", root_expr))
    _log.append(("dest", dest))
    _log.append(("template", template))
    if not preserve_name:
        new_name = f"{destination_name}-{_hashed(prev_applied, configuration_name, configuration_hash)}"
        template.get("metadata", {})["name"] = new_name

    if configuration.get("spec").get("container") is not None:
        # get target image name
        container_name = configuration["spec"]["container"].get("name")
        # if no name get the first element
        # it's ok to get an exception if no containers are found
        target = None
        if container_name is None:
            target = template["spec"]["containers"][0]
        else:
            container: dict
            for container in template["spec"]["containers"]:
                if container.get("name") == container_name:
                    target = container
        if target is None:
            raise ValueError("container {} not found".format(container_name))

        # volume mount
        mounts = target.setdefault("volumeMounts", [])
        found = False
        for m in mounts:
            if m["name"] == configuration.get("metadata").get("name"):
                found = True
                break
        if not found:
            mounts.append({
                "name": configuration.get("metadata").get("name"),
                "mountPath": mount_path
            })

        # preserve list elements in container section
        conf = configuration["spec"]["container"]
        for k, v in target.items():
            if isinstance(v, type([])) and k in conf:
                if k == "env":
                    target_d = {d["name"]: d for d in target[k]}
                    conf_d = {d["name"]: d for d in conf[k]}
                    env = []
                    all_names = set(list(target_d.keys()) + list(conf_d.keys()))
                    for name in all_names:
                        if name in conf_d:
                            env.append(conf_d[name])
                        else:
                            env.append(target_d[name])
                    conf[k] = env
                else:
                    if v not in conf[k]:
                        for el in v:
                            if el not in conf[k]:
                                conf[k].append(el)

        target.update(conf)

    # volumes
    cm_volume = {
        "name": configuration.get("metadata").get("name"),
        "configMap": {
            "name": cm_name
        }
    }

    found = False
    volumes = template["spec"].setdefault("volumes", [])
    volume: dict
    for volume in volumes:
        if volume["name"] == configuration.get("metadata").get("name"):
            volume.update(cm_volume)
            found = True
            break
    if not found:
        volumes.append(cm_volume)

    extra_volumes = configuration["spec"].get("extraVolumes", [])
    volumes.extend(extra_volumes)

    prev_applied[configuration_name] = configuration_hash
    annotations["config.krules.airspot.dev/applied"] = yaml.dump(prev_applied, Dumper=yaml.SafeDumper)

