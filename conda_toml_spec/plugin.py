from conda import plugins

from . import spec


@plugins.hookimpl
def conda_environment_specifiers():
    yield plugins.CondaEnvSpec(
        name="random",
        environment_spec=spec.TomlSpec,
    )
