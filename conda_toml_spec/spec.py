from __future__ import annotations

from abc import ABC
from copy import copy
from pathlib import Path
from pprint import pformat
from textwrap import indent
from typing import Any
from warnings import warn

from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.plugins.types import EnvironmentSpecBase
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)


class TomlSpec(EnvironmentSpecBase):
    """Implementation of conda's EnvironmentSpec which can handle toml files."""

    def __init__(self, filename: str):
        self.filename = filename

    def can_handle(self) -> bool:
        """Return whether the file passed to this class can be parsed.

        Returns
        -------
        bool
            True if the file can be parsed (it exists and is a toml file), False
            otherwise
        """
        if self.filename is None:
            return False

        file = Path(self.filename)
        return file.exists() and file.suffix == "toml"

    @property
    def env(self) -> Environment:
        """Generate an Environment from the provided TOML file."""
        return Environment()


class Urls(BaseModel):
    """A model which holds one or more URLs associated with a package."""
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _validate_urls(cls, data: dict[str, Any]) -> dict[str, AnyHttpUrl]:
        """Check that custom URL key/value pairs are actually URLs.

        Parameters
        ----------
        data : Any
            A dict of {field names: field values}

        Returns
        -------
        dict[str, AnyHttpUrl]
            Validated URLs for each field
        """
        for name, value in data.items():
            if name not in cls.model_fields:
                data[name] = AnyHttpUrl(value)
        return data


class About(BaseModel):
    """A model which stores metadata about an environment."""

    name: str
    revision: str
    description: str
    authors: list[str] = []
    license: str = (
        ""  # SPDX license expression: https://spdx.dev/learn/handling-license-info/
    )
    license_files: list[
        str
    ] = []  # PEP639-compliant expression: https://peps.python.org/pep-0639/#term-license-expression
    urls: Urls


class TomlConfig(BaseModel):
    """A model which stores configuration options for an environment."""

    channels: list[str] = []
    platforms: list[str] = []
    variables: dict[str, str] = {}


def validate_dependencies(deps: dict[str, Any]) -> list[MatchSpec]:
    """Convert a dict of package dependencies to a list of MatchSpec.

    Parameters
    ----------
    deps : dict[str, Any]
        Mapping between {package name: package version}

    Returns
    -------
    list[MatchSpec]
        A list of MatchSpec objects representing the dependencies

    """
    if isinstance(deps, dict):
        specs = []
        for name, version in deps.items():
            specs.append(MatchSpec(name=name, version=version))
        return specs

    raise ValueError(f"Invalid dependencies dict: {deps}")


class Platform(BaseModel):
    """A model which stores a list of dependencies for a platform."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dependencies: list[MatchSpec]

    @field_validator("dependencies", mode="before")
    @classmethod
    def _validate_dependencies(cls, deps: dict[str, Any]) -> list[MatchSpec]:
        """Convert a dict of package dependencies to a list of MatchSpec.

        Parameters
        ----------
        deps : dict[str, Any]
            Mapping between {package name: package version}

        Returns
        -------
        list[MatchSpec]
            A list of MatchSpec objects representing the dependencies
        """
        return validate_dependencies(deps)


class TomlEnvironment(BaseModel):
    """A base class for (de)serialization of a TOML environment file.

    This shouldn't be instantiated directly; instead use one of the child classes, or
    TomlEnvironment.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    about: About
    config: TomlConfig
    system_requirements: list[MatchSpec] = []
    version: int = 1


    @field_validator("system_requirements", mode="before")
    @classmethod
    def _validate_dependencies(cls, deps: dict[str, Any]) -> list[MatchSpec]:
        """Convert a dict of package dependencies to a list of MatchSpec.

        Parameters
        ----------
        deps : dict[str, Any]
            Mapping between {package name: package version}

        Returns
        -------
        list[MatchSpec]
            A list of MatchSpec objects representing the dependencies
        """
        return validate_dependencies(deps)

    @classmethod
    def model_validate(cls, *args, **kwargs):
        if cls not in [TomlSingleEnvironment, TomlMultiEnvironment]:
            try:
                return TomlSingleEnvironment.model_validate(*args, **kwargs)
            except ValidationError:
                return TomlMultiEnvironment.model_validate(*args, **kwargs)

            raise ValidationError

        # If one of the subclasses is trying to validate, pass validation onto
        # the parent.
        return super().model_validate(*args, **kwargs)

class TomlSingleEnvironment(TomlEnvironment):
    """A model which handles single environment files."""
    dependencies: list[MatchSpec] = []
    platform: dict[str, Platform] = {}
    pypi_dependencies: list[MatchSpec] = []

    @field_validator("dependencies", "pypi_dependencies", mode="before")
    @classmethod
    def _validate_dependencies(cls, deps: dict[str, Any]) -> list[MatchSpec]:
        return super()._validate_dependencies(deps)


class Group(BaseModel):
    """A model which stores configuration for a group of dependencies."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: TomlConfig
    dependencies: list[MatchSpec] = []
    description: str | None = None
    platform: dict[str, Platform] = {}
    pypi_dependencies: list[MatchSpec] = []
    system_requirements: list[MatchSpec] = []


class TomlMultiEnvironment(TomlEnvironment):
    """A model which handles multi environment files."""
    groups: dict[str, Group] = {}
    environments: dict[str, list[str]] = {}

    @field_validator("groups", mode="after")
    @classmethod
    def _validate_groups(cls, groups: dict[str, Group]) -> dict[str, Group]:
        """Verify that at least one group is specified."""
        if not groups:
            raise ValueError("At least one group is required in a multi-environment specification.")
        return groups

    @field_validator("environments", mode="after")
    @classmethod
    def _validate_environments(
        cls,
        envs: dict[str, list[str]],
        info: ValidationInfo,
    ) -> dict[str, list[str]]:
        """Verify that >1 env is specified, and that envs refer to specified groups.

        Warn the user if the spec contains a group which is not used by any environment.

        Parameters
        ----------
        envs : dict[str, list[str]]
            Unvalidated environments
        info : ValidationInfo
            Validated information; contains the validated groups

        Returns
        -------
        dict[str, list[str]]
            The validated environments
        """
        if not envs:
            raise ValueError(
                "Multi-environment specifications must contain at least one "
                "environment."
            )

        groups = set(info.data.get('groups', {}))
        extra_groups: set[str] = copy(groups)

        missing_groups = {}
        for env, env_groups in envs.items():
            # If an environment contains an unspecified group, keep track of it
            missing = set(env_groups) - groups
            if missing:
                missing_groups[env] = missing

            # Keep track of which groups are being used by environments, so we can warn
            # about unused ones later on
            extra_groups -= set(env_groups)

        if missing_groups:
            # Let the user know what groups are missing for each problematic environment
            msg = ""
            for key, values in missing_groups.items():
                msg += key
                msg += indent(pformat(values), prefix="  ")
            raise ValueError(
                "Multi-environment specification has environments with undefined "
                f"dependency groups:\n{indent(pformat(msg), prefix='  ')}"
            )

        if extra_groups:
            warn(
                "Some dependency groups were specified which were never used in any"
                "environment. Consider removing these:\n"
                f"{indent(pformat(extra_groups), prefix='  ')}",
                stacklevel=2
            )

        return envs
