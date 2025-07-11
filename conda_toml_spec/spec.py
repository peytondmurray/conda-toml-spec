from collections import defaultdict
from pathlib import Path
from typing import Any

from conda.env.env import Environment
from conda.models.match_spec import MatchSpec
from conda.plugins.types import EnvironmentSpecBase
from pydantic import AnyHttpUrl, BaseModel, field_validator, model_validator


class TomlSpec(EnvironmentSpecBase):
    def can_handle(self):
        if self.filename is None:
            return False

        file = Path(self.filename)
        return file.exists() and file.suffix == 'toml'

    def env(self):
        return Environment()


class Urls(BaseModel):
    homepage: AnyHttpUrl | None

    class Config:  # noqa: D106
        extra = 'allow'

    @model_validator(mode="before")
    @classmethod
    def validate_urls(cls, data: dict[str, Any]) -> dict[str, AnyHttpUrl]:
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
            if name not in cls.__fields__:
                data[name] = AnyHttpUrl(value)
        return data

class About(BaseModel):
    name: str
    revision: str
    description: str
    authors: list[str] = []
    license: str = "" # SPDX license expression: https://spdx.dev/learn/handling-license-info/
    license_files: list[str] = [] # PEP639-compliant expression: https://peps.python.org/pep-0639/#term-license-expression
    urls: Urls


class Config(BaseModel):
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
    dependencies: list[MatchSpec]

    class Config:
        arbitrary_types_allowed = True

    @field_validator("dependencies", mode="before")
    @classmethod
    def _validate_dependencies(cls, raw_dependencies: Any) -> list[MatchSpec]:
        return validate_dependencies(raw_dependencies)


class TomlEnvironment(BaseModel):
    version: int = 1
    about: About
    config: Config
    system_requirements: list[MatchSpec] = []
    dependencies: list[MatchSpec] = []
    platform: dict[str, Platform] = {}
    pypi_dependencies: list[MatchSpec] = []

    class Config:
        arbitrary_types_allowed = True

    @field_validator("system_requirements", "dependencies", "pypi_dependencies", mode="before")
    @classmethod
    def _validate_dependencies(cls, raw_dependencies: Any) -> list[MatchSpec]:
        return validate_dependencies(raw_dependencies)
