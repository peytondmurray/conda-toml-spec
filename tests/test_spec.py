from conda_toml_spec import spec


def test_parse_single_environment(single_environment_dict):
    """Test that a single environment file can be parsed."""
    env = spec.TomlSingleEnvironment.model_validate(single_environment_dict)
    assert env.version == 1


def test_parse_multi_environment(multi_environment_dict):
    """Test that a single environment file can be parsed."""
    env = spec.TomlSingleEnvironment.model_validate(multi_environment_dict)
    assert env.version == 1


def test_parse_multi_environment2(multi_environment_dict2):
    """Test that a single environment file can be parsed."""
    env = spec.TomlSingleEnvironment.model_validate(multi_environment_dict2)
    assert env.version == 1
