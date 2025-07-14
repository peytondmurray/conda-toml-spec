import pytest

from conda_toml_spec import spec


def test_parse_single_environment(single_environment_dict):
    """Test that a single environment file can be parsed."""
    env = spec.TomlSingleEnvironment.model_validate(single_environment_dict)
    assert isinstance(env, spec.TomlSingleEnvironment)
    assert env.version == 1


@pytest.mark.parametrize(
    "fixture",
    [
        "multi_environment_dict",
        "multi_environment_dict2",
    ]
)
def test_parse_multi_environment2(request, fixture):
    """Test that multi-environment files can be parsed."""
    env = spec.TomlMultiEnvironment.model_validate(request.getfixturevalue(fixture))
    assert isinstance(env, spec.TomlMultiEnvironment)
    assert env.version == 1


@pytest.mark.parametrize(
    ("fixture", "expected_class"),
    [
        ("single_environment_dict", spec.TomlSingleEnvironment),
        ("multi_environment_dict", spec.TomlMultiEnvironment),
        ("multi_environment_dict2", spec.TomlMultiEnvironment),
    ]
)
def test_parse_toml_environment(request, fixture, expected_class):
    """Ensure that TomlEnvironment can parse both single and multi environments."""
    env = spec.TomlEnvironment.model_validate(request.getfixturevalue(fixture))
    assert isinstance(env, expected_class)
    assert env.version == 1
