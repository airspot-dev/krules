import os
import krules_env
krules_env.init()

from krules_core.providers import (
    subject_factory,
    configs_factory,
    event_router_factory,
)

service_config = configs_factory()["services"][os.environ["CE_SOURCE"]]

# Your code here..
