c.InteractiveShellApp.exec_lines = [
    'import krules_env, env',
    'krules_env.init()',
    'env.init()',
    'from krules_core.providers import subject_factory',
    'from krules_core.providers import event_router_factory',
    'router = event_router_factory()',
]