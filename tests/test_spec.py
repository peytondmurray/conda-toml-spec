from conda_toml_spec import spec


def test_parse_single_environment(single_environment_dict):
    env = spec.TomlEnvironment.model_validate(single_environment_dict)
    breakpoint()
    assert env.version == 1
