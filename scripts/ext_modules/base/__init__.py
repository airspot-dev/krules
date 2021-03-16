
deploy__add_files = [
    "ruleset.py",
    "ipython_config.py",
]

deploy__labels = [
    ("serving.knative.dev/visibility", "cluster-local"),
    ("krules.airspot.dev/type", "ruleset"),
    ("krules.airspot.dev/ruleset", "{name}"),
]

deploy__environ = [
    ("PUBLISH_PROCEVENTS_LEVEL", "2"),
    ("PUBLISH_PROCEVENTS_FILTERS", "*"),
]

ishell__exec_lines = [
    "import krules_env, env",
    "krules_env.init()",
    "env.init()",
    "from krules_core.providers import subject_factory",
    "from krules_core.providers import event_router_factory",
    "router = event_router_factory()",
    "configs = configs_factory()",
]
