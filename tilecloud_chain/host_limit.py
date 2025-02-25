"""
Automatically generated file from a JSON schema.
"""

from typing import TypedDict

DEFAULT_CONCURRENT_LIMIT_DEFAULT = 1
""" Default value of the field path 'Default values concurrent' """


class DefaultValues(TypedDict, total=False):
    """Default values."""

    concurrent: int
    """
    Default concurrent limit.

    Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN_HOST_CONCURRENT` environment variable.

    default: 1
    """


class Host(TypedDict, total=False):
    """Host."""

    concurrent: int
    """
    Concurrent limit.

    Limit of concurrent request on the host
    """


class HostLimit(TypedDict, total=False):
    """
    TileCloud-chain host limit configuration.

    The configuration of the concurrent request limit on a host
    """

    default: "DefaultValues"
    """ Default values. """

    hosts: dict[str, "Host"]
    """ Hosts. """
