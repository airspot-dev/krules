import glob
import inspect
import io
import json
import logging
import os
import pprint
import sys
import re
import uuid
from typing import Callable

import git
from subprocess import run, CalledProcessError

import sh
from structlog.contextvars import bind_contextvars, clear_contextvars, unbind_contextvars

from krules_dev import sane_utils
from .base import recipe
from sane import _Help as Help
from .deprecated import _run

logger = logging.getLogger("__sane__")

import structlog
log = structlog.get_logger()


def make_enable_apis_recipe(google_apis, project_id, **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def enable_google_apis():
        gcloud = sane_utils.get_cmd_from_env("gcloud").bake(project=project_id)

        log.debug(f"Enabling GCP APIs, this may take several minutes...", project_id=project_id)
        for api in google_apis:
            log.debug(f"enable API...", api=api)
            gcloud.services.enable(api)


def make_check_gcloud_config_recipe(project_id, region, zone, **recipe_kwargs):
    @recipe(info="Check current gcloud configuration", **recipe_kwargs)
    def check_gcloud_config():
        gcloud = sane_utils.get_cmd_from_env("gcloud").bake(project=project_id)

        log.debug("Checking gcloud configuration", project_id=project_id, region=region, zone=zone)
        def _get_prop_cmd(prop):
            return gcloud.config('get-value', prop).strip()
            #return run(
            #    f"gcloud config get-value {prop}", shell=True, check=True, capture_output=True
            #).stdout.decode("utf8").strip()

        def _set_prop_cmd(prop, value):
            return gcloud.config.set(prop, value)
            #_run(f"gcloud config set {prop} {value}", check=True)

        # PROJECT
        action="read"
        _project_id = _get_prop_cmd("core/project")
        if _project_id == '':
            _project_id = project_id
            _set_prop_cmd("core/project", project_id)
            action="set"
        if _project_id != project_id:
            log.error("MATCH FAILED", property="core/project", configured=_project_id, received=project_id)
            #logger.error(f"code/project '{_project_id}' does not match '{project_id}'")
            sys.exit(-1)
        log.info(f"OK", project_id_=project_id, action=action)
        # REGION
        action="read"
        _region = _get_prop_cmd("compute/region")
        if _region == '':
            _region = region
            _set_prop_cmd("compute/region", region)
            action="set"
        if _region != region:
            log.error("MATCH FAILED", property="compute/region", configured=_region, received=region)
            sys.exit(-1)
        log.info(f"OK", region=_region, action=action)
        # ZONE
        if zone is not None:
            action="read"
            _zone = _get_prop_cmd("compute/zone")
            if _zone == '':
                _zone = zone
                _set_prop_cmd("compute/zone", zone)
                action="set"
            if _zone != zone:
                log.error("MATCH FAILED", property="compute/zone", configured=_zone,
                          received=zone)
                sys.exit(-1)
            log.info(f"OK", zone=_zone, action=action)


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
            log.info(
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
                logger.info(f"Applying {resource_file}...")
                _run(
                    f"gcloud deploy apply --file {resource_file} --region {region} --project {sane_utils.check_env('PROJECT_ID')}",
                    check=True,
                )

    with sane_utils.pushd(root_dir):
        for f in templates:
            _make_apply_deploy_recipe(f)


def make_ensure_billing_enabled(project_id, **recipe_kwargs):

    @recipe(**recipe_kwargs)
    def check_billing():
        log.debug("Ensuring billing enabled...")
        if not os.path.exists(f"billing-{project_id}"):
            out = run(
                f"{sane_utils.check_cmd('gcloud')} beta billing projects describe {project_id}",
                shell=True, capture_output=True
            )
            if b"billingEnabled: true" in out.stdout:
                with open(f"billing-{project_id}", "wb") as f:
                    f.write(out.stdout)
            else:
                log.error(f"You must enable billing for this project ", project=project_id)
                sys.exit(-1)
        else:
            log.debug(f"Billing enabled")


def make_ensure_gcs_bucket_recipe(bucket_name, project_id, location="EU", **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def ensure_gcs_bucket():
        gsutil = sh.Command(
            sane_utils.check_cmd(os.environ.get("GSUTIL_CMD", "gsutil"))
        )
        bind_contextvars(
            bucket=bucket_name, project=project_id, location=location
        )
        log.debug(f"Try to create gcs bucket", )
        #out = io.StringIO()
        #logging.getLogger('sh').setLevel(logging.DEBUG)
        #def _custom_log(ran, call_args, pid=None):
        #    log.debug("_>", ran=ran, pid=pid)

        try:
            gsutil.mb(
                "-l", location, "-p", project_id, f"gs://{bucket_name}",
                #_log_msg=_custom_log
                #_out=out, _err=out
            )
            log.info("gcs bucket created")
        except Exception as ex:
            log.debug("the bucket has not been created (maybe it already exists)", exit_code=ex.exit_code)

        clear_contextvars()
        # ret_code = _run(
        #     f"{gsutil} mb -l {location} -p {project_id} gs://{bucket_name}",
        #     check=False,
        #     err_to_stdout=True,
        #     errors_log_level=logging.DEBUG
        # )
        # if ret_code == 1:
        #     log.debug("the bucket has not been created (maybe it already exists)", retcode=ret_code)


def make_ensure_artifact_registry_recipe(repository_name, project_id, location="europe", format="DOCKER", **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def ensure_artifact_registry():

        repository_resource_name = f"projects/{project_id}/locations/{location}/repositories/{repository_name}"

        import google.auth.transport.requests
        import google.auth
        import urllib3
        creds, _ = google.auth.default()
        if creds.token is None:
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
        parent = f"projects/{project_id}/locations/{location}"
        headers = {"X-Goog-User-Project": project_id, "Authorization": f"Bearer {creds.token}"}
        api_url = f"https://artifactregistry.googleapis.com/v1/{parent}/repositories"

        http = urllib3.PoolManager()
        logger.debug("Checking repositories...")
        resp = http.request("GET", api_url, headers=headers)
        repos = json.loads(resp.data).get("repositories", [])

        for repo in repos:
            if repo["name"] == repository_resource_name:
                logger.debug(f"Repository {repository_name} already exists")
                return
        try:
            http.request(
                "POST", f"{api_url}?repositoryId={repository_name}", headers=headers, body=json.dumps({"format": format})
            )
        except Exception as ex:
            logger.error(f"Error creating repository {repository_name}: {ex}")
            return
        logger.info(f"Repository {repository_name} created")


def make_cloud_deploy_recipes(
        image_base: str,
        baselibs: list | tuple = (),
        sources: list | tuple = (),
        out_dir: str = ".build",
        extra_context_vars: dict = None,
        extra_target_context_vars: dict[str, dict] = None
):
    use_cloudrun = int(os.environ.get("USE_CLOUDRUN", "0"))
    use_clouddeploy = int(os.environ.get("USE_CLOUDDEPLOY", "0"))
    if use_clouddeploy:
        logger.info("using Google Cloud Deploy")
        if "USE_CLOUDBUILD" in os.environ and not int(os.environ["USE_CLOUDBUILD"]):
            logger.warning("USE_CLOUDBUILD is set to False but USE_CLOUDDEPLOY is set to True so USE_CLOUDBUILD will be overridden")
        use_cloudbuild = True
    else:
        use_cloudbuild = int(os.environ.get("USE_CLOUDBUILD", "0"))
        if use_cloudbuild:
            logger.info("using Google Cloud Build")
        
    if extra_context_vars is None:
        extra_context_vars = {}
    if extra_target_context_vars is None:
        extra_target_context_vars = {}

    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    targets = [s.lower() for s in re.split(" |,|;", os.environ.get("TARGETS", "default")) if len(s)]

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
            "Dockerfile.j2"
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            "project_name": sane_utils.check_env("PROJECT_NAME"),
            "image_base": image_base,
            "user_baselibs": baselibs,
            "project_id": sane_utils.get_var_for_target("project_id", targets[0], True),
            "targets": targets,
            "sources": sources,
            **extra_context_vars
        },
        hooks=[
            'prepare_build'
        ]
    )

    sane_utils.make_render_resource_recipes(
        globs=[
            "skaffold.yaml.j2"
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            "project_id": sane_utils.get_var_for_target("project_id", targets[0], True),
            "targets": targets,
            "use_clouddeploy": use_clouddeploy,
            "use_cloudbuild": use_cloudbuild,
            "use_cloudrun": use_cloudrun,
            ** extra_context_vars
        },
        hooks=[
            'prepare_build'
        ]
    )

    if use_clouddeploy:
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
                "project_id": sane_utils.get_var_for_target("project_id", targets[0], True),
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

    if use_clouddeploy:
        @recipe(info="Build the artifact", hook_deps=['prepare_build'], hooks=["prepare_deploy"])
        def build():
            if str(os.environ.get("BUILD_ARTIFACTS")) == "0":
                return
            if not code_changed:
                logger.info("No changes detected... Skip build")
                return
            logger.info("Building the artifact")
            artifact_registry = sane_utils.check_env('PROJECT_NAME')
            region = sane_utils.get_var_for_target('region', targets[0])
            project = sane_utils.get_var_for_target('project_id', targets[0])
            repo_name = f"{region}-docker.pkg.dev/{project}/{artifact_registry}"
            with sane_utils.pushd(os.path.join(root_dir, out_dir)):
                _run([
                    sane_utils.check_cmd("skaffold"), "build", "--interactive=false",
                    "--default-repo", repo_name,
                    # "-f", os.path.join(root_dir, out_dir, "skaffold.yaml"),
                    "--file-output", os.path.join(root_dir, out_dir, "artifacts.json"),
                ])
            with open(success_file, "w") as f:
                code_digest = open(code_digest_file, "r").read()
                f.write(code_digest)

        make_gcloud_deploy_apply_recipe(
            region=sane_utils.get_var_for_target(
                'CLOUDDEPLOY_REGION', targets[0], default=sane_utils.get_var_for_target('region', targets[0])
            ),
            templates=["pipeline.yaml.j2"],
            hooks=["prepare_deploy"],
            hook_deps=["prepare_apply"]
        )

        deploy_hook_deps = ["prepare_deploy"]
    else:
        deploy_hook_deps = ["prepare_build"]

    @recipe(info="Deploy the artifact [GCP]", hook_deps=deploy_hook_deps)
    def deploy():
        if use_clouddeploy:
            if not code_changed:
                logger.info("No changes detected... Skip deploy")
                return
            logger.info("Deploying")
            app_name = sane_utils.check_env('APP_NAME')
            repo = git.Repo(search_parent_directories=True)
            git_sha = repo.head.object.hexsha[:7]
            unique = str(uuid.uuid4()).split('-')[0]
            app_version = f"{git_sha}-{unique}"
            region = sane_utils.get_var_for_target('region', targets[0])
            if str(os.environ.get("BUILD_ARTIFACTS")) == "0":
                _run([
                    sane_utils.check_cmd("gcloud"), "deploy", "releases",
                    "create", f"{app_name[0]}-{app_version}",
                    "--project", sane_utils.get_var_for_target('PROJECT_ID', targets[0]),
                    "--region", sane_utils.get_var_for_target('CLOUDDEPLOY_REGION', targets[0], default=region),
                    "--delivery-pipeline", f"{sane_utils.check_env('PROJECT_NAME')}-{app_name}",
                    "--skaffold-file", os.path.join(root_dir, out_dir, "skaffold.yaml"),
                    "--source", out_dir
                ], check=True)
            else:
                _run([
                    sane_utils.check_cmd("gcloud"), "deploy", "releases",
                    "create", f"{app_name[0]}-{app_version}",
                    "--project", sane_utils.get_var_for_target('PROJECT_ID', targets[0]),
                    "--region", sane_utils.get_var_for_target('CLOUDDEPLOY_REGION', targets[0], default=region),
                    "--delivery-pipeline", f"{sane_utils.check_env('PROJECT_NAME')}-{app_name}",
                    "--build-artifacts", os.path.join(root_dir, out_dir, "artifacts.json"),
                    "--source", out_dir
                ], check=True)
            logger.info("Deployed!")
        else:
            repo_name = os.environ.get("IMAGE_REPOSITORY")
            if repo_name is None:
                artifact_registry = sane_utils.check_env('PROJECT_NAME')
                region = sane_utils.get_var_for_target('region', targets[0])
                project = sane_utils.get_var_for_target('project_id', targets[0])
                repo_name = f"{region}-docker.pkg.dev/{project}/{artifact_registry}"
            with sane_utils.pushd(os.path.join(root_dir, out_dir)):
                _run([
                    sane_utils.check_cmd("skaffold"), "run",
                    "--default-repo", repo_name,
                    # "-f", os.path.join(root_dir, out_dir, "skaffold.yaml"),
                    "-p", os.environ.get("TARGET", targets[0]),
                ])


def make_target_deploy_recipe(
        image_base: str | Callable,
        baselibs: list | tuple = (),
        sources: list | tuple = (),
        out_dir: str = ".build",
        extra_context_vars: dict = None,
        extra_target_context_vars: dict[str, str] = None,
):

    selected_target, targets = sane_utils.get_targets_info()

    bind_contextvars(
        target=selected_target
    )

    use_cloudrun = int(sane_utils.get_var_for_target("USE_CLOUDRUN", selected_target, default="0"))
    if use_cloudrun:
        log.debug("using CloudRun to deploy")
    else:
        log.debug("using Kubernetes to deploy")

    use_cloudbuild = int(sane_utils.get_var_for_target("USE_CLOUDBUILD", selected_target, default="0"))
    if use_cloudbuild:
        log.debug("using Google Cloud Build"),

    if extra_context_vars is None:
        extra_context_vars = {}
    if extra_target_context_vars is None:
        extra_target_context_vars = {}

    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    #targets = [s.lower() for s in re.split(" |,|;", os.environ.get("TARGETS", "default")) if len(s)]
    
    sources_ext = []
    origins = []
    for source in sources:
        if isinstance(source, str):
            sources_ext.append(
                {
                    "origin": source,
                    "destination": f"/app/{source}"
                }
            )
            origins.append(source)
        else:
            sources_ext.append(
                {
                    "origin": source[0],
                    "destination": source[1]
                }
            )
            origins.append(source[0])
    # making changes to these files will result in a new build
    sane_utils.update_code_hash(
        globs=[
            *origins,
            *list(map(lambda x: f"{sane_utils.check_env('KRULES_PROJECT_DIR')}/base/libs/{x}/**/*.py", baselibs)),
            os.path.join(root_dir, "k8s", "*.j2"),
            os.path.join(root_dir, "*.j2"),
        ],
        out_dir=os.path.join(root_dir, out_dir),
        output_file=".code.digest"
    )

    sane_utils.make_copy_source_recipe(
        name="prepare_source_files",
        info="Copy the source files within the designated context to prepare for the container build.",
        location=root_dir,
        src=origins,
        dst="",
        out_dir=os.path.join(root_dir, out_dir),
        hooks=["prepare_build"],
    )

    sane_utils.make_copy_source_recipe(
        name="prepare_user_baselibs",
        info="Copy base libraries within the designated context to prepare for the container build.",
        location=os.path.join(sane_utils.check_env("KRULES_PROJECT_DIR"), "base", "libs"),
        src=baselibs,
        dst=".user-baselibs",
        out_dir=os.path.join(root_dir, out_dir),
        hooks=["prepare_build"],
    )

    sane_utils.make_render_resource_recipes(
        globs=[
            "Dockerfile.j2"
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            "project_name": sane_utils.check_env("PROJECT_NAME"),
            "image_base": callable(image_base) and image_base() or image_base,
            "user_baselibs": baselibs,
            "project_id": sane_utils.get_var_for_target("project_id", selected_target, True),
            "target": selected_target,
            "sources": sources_ext,
            **extra_context_vars
        },
        hooks=[
            'prepare_build'
        ]
    )

    skaffold_targets = []
    for t in targets:

        project_id = sane_utils.get_var_for_target("project_id", t)
        use_cloudrun = int(sane_utils.get_var_for_target("use_cloudrun", t, default="0"))
        use_cloudbuild = int(sane_utils.get_var_for_target("use_cloudbuild", t, default="0"))
        region = sane_utils.get_var_for_target("region", t, default=None)
        if use_cloudrun and region is None:
            log.error("You must specify a region if using CloudRun")
            sys.exit(-1)
        namespace = sane_utils.get_var_for_target("namespace", t, default="default")
        kubectl_opts = sane_utils.get_var_for_target("kubectl_opts", t, default=None)
        if kubectl_opts:
            kubectl_opts = re.split(" ", kubectl_opts)
        else:
            kubectl_opts = []

        skaffold_targets.append({
            "name": t,
            "project_id": project_id,
            "use_cloudrun": use_cloudrun,
            "use_cloudbuild": use_cloudbuild,
            "region": region,
            "namespace": namespace,
            "kubectl_opts": kubectl_opts,
        })

    sane_utils.make_render_resource_recipes(
        globs=[
            "skaffold.yaml.j2"
        ],
        context_vars=lambda: {
            "app_name": sane_utils.check_env("APP_NAME"),
            #"project_id": sane_utils.get_var_for_target("project_id", target, True),
            "targets": skaffold_targets,
            #"use_cloudrun": use_cloudrun,
            **extra_context_vars
        },
        hooks=[
            'prepare_build'
        ]
    )

    for t in targets:
        extra_target_context = {
            k: sane_utils.get_var_for_target(
                target=t, name=v, mandatory=True
            ) for k,v in extra_target_context_vars.items()
        }
        sane_utils.make_render_resource_recipes(
            globs=[
                "k8s/*.j2"
            ],
            context_vars={
                "project_name": sane_utils.check_env("PROJECT_NAME"),
                "app_name": sane_utils.check_env("APP_NAME"),
                "namespace": sane_utils.get_var_for_target("namespace", t, default="default"),
                "target": t,
                "project_id": sane_utils.get_var_for_target("project_id", t, True),
                **extra_target_context,
                **extra_context_vars
            },
            hooks=[
                'prepare_build'
            ],
            out_dir=f"{out_dir}/k8s/{t}"
        )

    success_file = os.path.join(root_dir, out_dir, ".success")
    code_digest_file = os.path.join(root_dir, out_dir, ".code.digest")
    code_changed = not os.path.exists(success_file) or os.path.exists(code_digest_file) and open(success_file).read() != open(code_digest_file).read()

    @recipe(info="Deploy the artifact", hook_deps=["prepare_build"])
    def deploy():

        bind_contextvars(
            target=selected_target
        )

        if not code_changed:
            log.debug("No changes detected... Skip deploy")
            return

        repo_name = sane_utils.get_var_for_target("DOCKER_REGISTRY", selected_target)
        log.debug("Get DOCKER_REGISTRY from env", value=repo_name)
        if repo_name is None:
            artifact_registry = sane_utils.check_env('PROJECT_NAME')
            region = sane_utils.get_var_for_target('region', selected_target)
            project = sane_utils.get_var_for_target('project_id', selected_target)
            repo_name = f"{region}-docker.pkg.dev/{project}/{artifact_registry}"
            log.debug("Using project artifact registry", value=repo_name)
        with sane_utils.pushd(os.path.join(root_dir, out_dir)):
            skaffold = sh.Command(
                sane_utils.check_cmd("skaffold")
            )

            log.debug("Running skaffold" )
            skaffold.run(
                default_repo=repo_name,
                profile=selected_target,
            )
            log.info("Deployed")


def make_cloud_build_recipe(
        artifact_registry, image_name, project,
        on_build_success=lambda digest: None, dockerfile_path=".", **recipe_kwargs):
    @recipe(**recipe_kwargs)
    def push_image_to_registry():
        logger.info(f"Start building {artifact_registry}/{image_name}...")
        out = {"stdout": [], "stderr": []}
        gcloud = sane_utils.check_cmd("gcloud")
        _run(
            f"{gcloud} builds submit -t {artifact_registry}/{image_name} {dockerfile_path} --project {project} --format 'value(results.images[0].digest)'",
            captures=out, check=True, err_to_stdout=True
        )
        digest = out["stdout"][-1].replace("\n", "")
        on_build_success(f"{artifact_registry}/{image_name}@{digest}")
