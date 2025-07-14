from pathlib import Path
from typing import Any

import pytest

try:
    from tomllib import loads
except ImportError:
    from tomli import loads


@pytest.fixture
def single_environment_dict() -> dict[str, Any]:
    """Return a single environment toml file, parsed into a dict.

    Returns
    -------
    dict[str, Any]
        The toml environment file, parsed into a dict
    """
    with open(Path(__file__).parent / "assets" / "single_environment.toml") as f:
        return loads(f.read())


@pytest.fixture
def multi_environment_dict() -> dict[str, Any]:
    """Return a multi environment toml file, parsed into a dict.

    Returns
    -------
    dict[str, Any]
        The toml environment file, parsed into a dict
    """
    with open(Path(__file__).parent / "assets" / "multi_environment.toml") as f:
        return loads(f.read())


@pytest.fixture
def multi_environment_dict2() -> dict[str, Any]:
    """Return another multi environment toml file, parsed into a dict.

    Returns
    -------
    dict[str, Any]
        The toml environment file, parsed into a dict
    """
    with open(Path(__file__).parent / "assets" / "multi_environment2.toml") as f:
        return loads(f.read())
