import glob
import inspect
import os
import re
import uuid
import git
from subprocess import run, CalledProcessError

from krules_dev import sane_utils
from sane import recipe
from sane import _Help as Help


def make_enable_apis_recipe(google_apis, **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def enable_google_apis():
        Help.log("Enabling GCP APIs, please wait, this may take several minutes...")
        for api in google_apis:
            Help.log(f"enable {api}...")
            run(f"gcloud services enable {api}", shell=True, check=True, capture_output=True)
        Help.log("Done")


def make_check_gcloud_config_recipe(project_id, region, zone, **recipe_kwargs):
    @recipe(info="Check current gcloud configuration", **recipe_kwargs)
    def check_gcloud_config():
        def _get_prop_cmd(prop):
            return run(
                f"gcloud config get-value {prop}", shell=True, check=True, capture_output=True
            ).stdout.decode("utf8").strip()

        def _set_prop_cmd(prop, value):
            try:
                run(f"gcloud config set {prop} {value}", shell=True, check=True, capture_output=True)
            except CalledProcessError as ex:
                Help.log(ex.stdout.decode("utf8"))
                Help.error(ex.stderr.decode("utf8"))

        Help.log("Check current gcloud configuration")
        # PROJECT
        _project_id = _get_prop_cmd("core/project")
        if _project_id == '':
            _project_id = project_id
            _set_prop_cmd("core/project", project_id)
        if _project_id != project_id:
            Help.error(f"code/project '{_project_id}' does not match '{project_id}'")
        Help.log(f"Using project: {_project_id}")
        # REGION
        _region = _get_prop_cmd("compute/region")
        if _region == '':
            _region = region
            _set_prop_cmd("compute/region", region)
        if _region != region:
            Help.error(f"already set compute/region '{_region}' must match '{region}'")
        Help.log(f"Using region: {_region}")
        # ZONE
        if zone is not None:
            _zone = _get_prop_cmd("compute/zone")
            if _zone == '':
                _zone = zone
                _set_prop_cmd("compute/zone", zone)
            if _zone != zone:
                Help.error(f"already set compute/zone '{_zone}' must match '{zone}'")
            Help.log(f"Using zone: {_zone}")
        # DEPLOY REGION
        _deploy_region = _get_prop_cmd("deploy/region")
        if _deploy_region == '':
            _deploy_region = _region
            _set_prop_cmd("deploy/region", _deploy_region)
        if _deploy_region != _region:
            Help.error(f"already set deploy/region '{_deploy_region}' must match '{_region}'")
        Help.log(f"Using deploy region: {_region}")


def make_set_gke_contexts_recipe(project_name, targets, **recipe_kwargs):
    @recipe(
        info="Set gke kubectl config contexts",
        **recipe_kwargs
    )
    def set_gke_contexts():
        for target in targets:
            context_name = f"gke_{project_name}_{target}"
            project = sane_utils.get_var_for_target("project_id", target, True)
            cluster_name = sane_utils.get_var_for_target("cluster", target, True)
            namespace = sane_utils.get_var_for_target("namespace", target)
            if namespace is None:
                namespace = "default"
            region_or_zone = sane_utils.get_var_for_target("zone", target)
            location_arg = "--zone"
            if region_or_zone is None:
                region_or_zone = sane_utils.get_var_for_target("region", target, True)
                location_arg = "--region"
            Help.log(
                f"Setting context {context_name} for cluster {region_or_zone}/{cluster_name} in project {project} to namespace {namespace}")

            run(
                f"gcloud container clusters get-credentials {cluster_name} {location_arg} {region_or_zone}",
                shell=True,
                check=True,
                capture_output=True
            )
            try:
                run(f"kubectl config delete-context {context_name}", shell=True, check=True, capture_output=True)
            except CalledProcessError:
                pass
            run(
                f"kubectl config rename-context gke_{project}_{region_or_zone}_{cluster_name} {context_name}",
                shell=True,
                check=True,
                capture_output=True
            )
            run(
                f"kubectl config set-context {context_name} --namespace {namespace}",
                shell=True,
                check=True,
                capture_output=True
            )

        run(
            f"kubectl config use-context gke_{project_name}_{targets[0].lower()}",
            shell=True,
            check=True,
            capture_output=True
        )


def make_gcloud_deploy_apply_recipe(templates, region, out_dir=".build", **recipe_kwargs):

    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    def _make_apply_deploy_recipe(j2_template):

        resource_file = os.path.join(out_dir, os.path.split(j2_template)[1].split(".j2")[0])
        resource_older_than_template = (
            Help.file_condition(
                sources=[os.path.join(root_dir, j2_template)],
                targets=[os.path.join(root_dir, resource_file)]
            )
        )

        recipe_kwargs['info'] = f"Apply '{resource_file}'"
        if 'conditions' not in recipe_kwargs:
            recipe_kwargs['conditions'] = []
        recipe_kwargs['conditions'].append(resource_older_than_template)
        recipe_kwargs['name'] = f"gcloud_deploy_apply_{resource_file}"

        @recipe(**recipe_kwargs)
        def render_resource():
            with sane_utils.pushd(root_dir):
                Help.log(f"Applying {resource_file}...")
                try:
                    run(
                        f"gcloud deploy apply --file {resource_file} --region {region}",
                        shell=True,
                        check=True,
                        capture_output=True
                    )
                except CalledProcessError as ex:
                    Help.log(ex.stdout.decode("utf8"))
                    Help.error(ex.stderr.decode("utf8"))

    with sane_utils.pushd(root_dir):
        for f in templates:
            _make_apply_deploy_recipe(f)


def make_ensure_gcs_bucket_recipe(bucket_name, **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def ensure_gcs_bucket():
        gsutil = sane_utils.check_cmd(os.environ.get("GSUTIL_CMD", "gsutil"))
        Help.log(f"Creating bucket gs://{bucket_name}")
        try:
            run(f"{gsutil} mb gs://{bucket_name}", shell=True, check=True, capture_output=True)
        except CalledProcessError as ex:
            if ex.stderr.decode("utf8").find("ServiceException: 409 ") > 0:
                Help.log("  ...bucket already exists")
            else:
                Help.log(ex.stdout.decode("utf8"))
                Help.error(ex.stderr.decode("utf8"))


def make_cloud_deploy_recipes(
        image_base: str,
        baselibs: list | tuple = (),
        sources: list | tuple = (),
        out_dir: str = ".build",
        extra_context_vars: dict = None,
        extra_target_context_vars: dict[str, dict] = None
):

    if extra_context_vars is None:
        extra_context_vars = {}
    if extra_target_context_vars is None:
        extra_target_context_vars = {}
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    targets = [s.lower() for s in re.split(" |,|;", sane_utils.check_env("TARGETS")) if len(s)]

    # making changes to these files will result in a new build
    sane_utils.update_code_hash(
        globs=[
            *sources,
            *list(map(lambda x: f"{os.environ['KRULES_PROJECT_DIR']}/base/libs/{x}/**/*.py", baselibs)),
            os.path.join(root_dir, "k8s", "*.j2"),
            os.path.join(root_dir, "*.j2"),
        ],
        out_dir=os.path.join(root_dir, out_dir),
        output_file=".code.digest"
    )

    sane_utils.make_copy_source_recipe(
        name="prepare_source_files",
        location=root_dir,
        src=sources,
        dst="",
        out_dir=os.path.join(root_dir, out_dir),
        hooks=["prepare_build"],
    )

    sane_utils.make_copy_source_recipe(
        name="prepare_user_baselibs",
        location=os.path.join(sane_utils.check_env("KRULES_PROJECT_DIR"), "base", "libs"),
        src=baselibs,
        dst=".user-baselibs",
        out_dir=os.path.join(root_dir, out_dir),
        hooks=["prepare_build"],
    )

    sane_utils.make_render_resource_recipes(
        globs=[
            "Dockerfile.j2",
            "skaffold.yaml.j2",
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            "project_name": sane_utils.check_env("PROJECT_NAME"),
            "image_base": image_base,
            "user_baselibs": baselibs,
            "project_id": sane_utils.get_var_for_target("project_id", targets[0], True),
            "targets": targets,
            **extra_context_vars
        },
        hooks=[
            'prepare_build'
        ]
    )

    sane_utils.make_render_resource_recipes(
        globs=[
            "pipeline.yaml.j2",
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            "project_name": sane_utils.check_env("PROJECT_NAME"),
            "targets": targets,
            **extra_context_vars
        },
        hooks=[
            'prepare_apply'
        ]
    )

    for target in targets:
        sane_utils.make_render_resource_recipes(
            globs=[
                "k8s/*.j2"
            ],
            context_vars={
                "project_name": sane_utils.check_env("PROJECT_NAME"),
                "app_name": sane_utils.check_env("APP_NAME"),
                "namespace": sane_utils.get_var_for_target("namespace", target),
                "target": target,
                **extra_target_context_vars.get(target, {})
            },
            hooks=[
                'prepare_build'
            ],
            out_dir=f"{out_dir}/k8s/{target}"
        )

    success_file = os.path.join(root_dir, out_dir, ".success")
    code_digest_file = os.path.join(root_dir, out_dir, ".code.digest")
    code_changed = not os.path.exists(success_file) or os.path.exists(code_digest_file) and open(success_file).read() != open(code_digest_file).read()

    @recipe(info="Build the artifact", hook_deps=['prepare_build'], hooks=["prepare_deploy"])
    def build():
        if not code_changed:
            Help.log("No changes detected... Skip build")
            return
        Help.log("Building the artifact")
        artifact_registry = sane_utils.check_env('PROJECT_NAME')
        region = sane_utils.get_var_for_target('region', targets[0])
        project = sane_utils.get_var_for_target('project_id', targets[0])
        repo_name = f"{region}-docker.pkg.dev/{project}/{artifact_registry}"
        try:
            run([
                sane_utils.check_cmd("skaffold"), "build", "--interactive=false",
                "--default-repo", repo_name,
                "-f", os.path.join(root_dir, out_dir, "skaffold.yaml"),
                "--file-output", os.path.join(root_dir, out_dir, "artifacts.json"),
            ], check=True, capture_output=True)
            with open(success_file, "w") as f:
                code_digest = open(code_digest_file, "r").read()
                f.write(code_digest)
        except CalledProcessError as ex:
            Help.log(ex.stdout.decode())
            Help.error(ex.stderr.decode())

    make_gcloud_deploy_apply_recipe(
        region=sane_utils.get_var_for_target('region', targets[0]),
        templates=["pipeline.yaml.j2"],
        hooks=["prepare_deploy"],
        hook_deps=["prepare_apply"]
    )

    @recipe(info="Deploy the artifact", hook_deps=["prepare_deploy"])
    def deploy():
        if not code_changed:
            Help.log("No changes detected... Skip deploy")
            return
        Help.log("Deploying")
        app_name = sane_utils.check_env('APP_NAME')
        repo = git.Repo(search_parent_directories=True)
        git_sha = repo.head.object.hexsha[:7]
        unique = str(uuid.uuid4()).split('-')[0]
        app_version = f"{git_sha}-{unique}"

        try:

            run([
                sane_utils.check_cmd("gcloud"), "deploy", "releases",
                "create", f"{app_name[0]}-{app_version}",
                "--region", sane_utils.get_var_for_target('region', targets[0]),
                "--delivery-pipeline", f"{sane_utils.check_env('PROJECT_NAME')}-{app_name}",
                "--build-artifacts", os.path.join(root_dir, out_dir, "artifacts.json"),
                "--source", out_dir
            ], check=True, capture_output=True)
        except CalledProcessError as ex:
            Help.log(ex.stdout.decode())
            Help.error(ex.stderr.decode())
        Help.log("Deployed!")
