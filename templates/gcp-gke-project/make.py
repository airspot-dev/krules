#!/usr/bin/env python3
import re
import subprocess
import sys

from sane import *
from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(ROOT_DIR))

from krules_dev import sane_utils
from krules_dev.sane_utils import google

sane_utils.load_env()

run = lambda cmd: subprocess.run(cmd, shell=True, check=True, capture_output=True)

PROJECT_NAME = sane_utils.check_env("PROJECT_NAME").strip()

TARGETS = [s.lower() for s in re.split(" |,|;", sane_utils.check_env("TARGETS")) if len(s)]

TF_BACKEND = f"{sane_utils.get_var_for_target('PROJECT_ID', TARGETS[0], True)}-tfstate"

if len(TARGETS) != 2:
    Help.error("You need to define a TARGET variable with exactly two values separated by ';' (eg: \"dev;test\")")

TARGET_DICTS = sane_utils.get_target_dicts(TARGETS, (
    "project_id",
    "region",
    "zone",
    "cluster",
    "namespace",
    ("location", lambda target:
    sane_utils.get_var_for_target("zone", target, default=sane_utils.get_var_for_target("region", target))),
    ("require_approval", "false"),
))

sane_utils.google.make_enable_apis_recipe([
    "storage.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
])

sane_utils.google.make_check_gcloud_config_recipe(
    project_id=sane_utils.get_var_for_target('PROJECT_ID', TARGETS[0], True),
    region=sane_utils.get_var_for_target('REGION', TARGETS[0], True),
    zone=sane_utils.get_var_for_target('ZONE', TARGETS[0]),
)


@recipe(
    info="Create terraform.tfvars.json file",
    name="create_tf_vars",
    hooks=[
        "prepare_tf"
    ],
)
def create_tf_vars(
        out_file="terraform/terraform.tfvars.json",
        content=lambda: {
            "project_name": PROJECT_NAME,
            "primary_target": TARGET_DICTS[0],
            "targets": {e["name"]: e for e in TARGET_DICTS},
            "all_projects": list(set([sane_utils.get_var_for_target("project_id", target, True) for target in TARGETS])),
            # "ingestion_topic_basename": sane_utils.check_env("INGESTION_TOPIC_BASENAME").strip(), # See base/terraform/pubsub.tf
        }
):
    import json
    with open(os.path.join(ROOT_DIR, out_file), 'w') as of:
        json.dump(content(), of, indent=4)


sane_utils.make_render_resource_recipes(
    globs=[
        "terraform/*.tf.j2",
        "terraform/backend.hcl.j2",
    ],
    context_vars={
        "project_name": PROJECT_NAME,
        "targets": TARGET_DICTS,
        "all_projects": set([sane_utils.get_var_for_target("project_id", target, True) for target in TARGETS]),
        "tf_backend_bucket": TF_BACKEND,
        # "ingestion_topic_basename": sane_utils.check_env("INGESTION_TOPIC_BASENAME").strip(), # See base/terraform/pubsub.tf
    },
    hooks=[
        "prepare_tf"
    ],
    out_dir="terraform/"
)

sane_utils.google.make_ensure_gcs_bucket_recipe(
    bucket_name=TF_BACKEND,
    hooks=[
        "prepare_tf"
    ]
)

sane_utils.make_run_terraform_recipe(
    manifests_dir=os.path.join(ROOT_DIR, "terraform"),
    init_params=["-backend-config=backend.hcl"],
    hook_deps=[
        "prepare_tf"
    ]
)

sane_utils.google.make_set_gke_contexts_recipe(
    project_name=PROJECT_NAME,
    targets=TARGETS,
)

sane_utils.make_render_resource_recipes(
    globs=[
        f"targets.yaml.j2"
    ],
    context_vars={
        "project_name": PROJECT_NAME,
        "targets": TARGET_DICTS,
    },
    hooks=[
        "prepare_base_deploy_resources"
    ],
    out_dir="."
)

sane_utils.google.make_gcloud_deploy_apply_recipe(
    region=sane_utils.get_var_for_target('region', TARGETS[0], True),
    templates=["targets.yaml.j2"],
    out_dir=".",
    hook_deps=[
        "prepare_base_deploy_resources"
    ],
    hooks=[
        "prepare_gcp_base_deploy"
    ]
)


@recipe(hook_deps=["prepare_gcp_base_deploy"], info="apply gcloud deploy target")
def prepare_targets():
    pass


sane_utils.make_clean_recipe(
    globs=[
        "terraform/backend.hcl",
        "terraform/terraform.tfvars.json",
        "terraform/.terraform*",
        "terraform/terraform.tfplan",
        "terraform/terraform.tfstate*",
        "targets.yaml",
    ]
)


sane_run()