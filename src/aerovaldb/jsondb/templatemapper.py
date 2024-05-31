import abc
from aerovaldb.utils import async_and_sync
from packaging.version import Version
from typing import Callable

VersionProvider = Callable[[str, str], Version]


class SkipMapper(Exception):
    """
    Exception raised when a TemplateMapper does not want to or
    can't handle a request.
    """

    pass


class TemplateMapper(abc.ABC):
    """
    This class is a base class for objects that implement a
    file path template selection algorithm. Inheriting
    implementations should implement the __call_ function,
    and raising SkipMapper if the implementation can't or
    won't handle the request.
    """

    @async_and_sync
    async def __call__(self, *args, version_provider: VersionProvider, **kwargs) -> str:
        raise NotImplementedError


class DataVersionToTemplateMapper(TemplateMapper):
    """
    This class returns its provided template if the
    data version read from a config file matches
    the configured bounds of this class.
    """

    def __init__(
        self,
        template: str,
        *,
        min_version: str | None = None,
        max_version: str | None = None,
    ):
        self.min_version = None
        self.max_version = None

        if min_version is not None:
            self.min_version = Version(min_version)
        if max_version is not None:
            self.max_version = Version(max_version)

        self.template = template

    @async_and_sync
    async def __call__(self, *args, version_provider: VersionProvider, **kwargs) -> str:
        version = await version_provider(kwargs["project"], kwargs["experiment"])
        if self.min_version is not None and version < self.min_version:
            raise SkipMapper
        if self.max_version is not None and version > self.max_version:
            raise SkipMapper

        return self.template


class PriorityDataVersionToTemplateMapper(TemplateMapper):
    """
    This class takes a list of templates, trying them in turn
    and returning the first template that fits the provided
    parameters.
    """

    def __init__(self, templates: list[str]):
        self.templates = templates

    @async_and_sync
    async def __call__(self, *args, version_provider: VersionProvider, **kwargs) -> str:
        selected_template = None
        for t in self.templates:
            try:
                t.format(**kwargs)
                selected_template = t
                break
            except:
                continue

        if selected_template is None:
            raise SkipMapper

        return selected_template