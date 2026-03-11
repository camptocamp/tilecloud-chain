"""
Automatically generated file from a JSON schema.
"""


from typing import TypedDict


DEFAULT_CONCURRENT_LIMIT_DEFAULT = 1
r""" Default value of the field path 'Default values concurrent' """



class DefaultValues(TypedDict, total=False):
    r""" Default values. """

    concurrent: int
    r"""
    Default concurrent limit.

    Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN_HOST_CONCURRENT` environment variable.

    default: 1
    """



class Host(TypedDict, total=False):
    r""" Host. """

    concurrent: int
    r"""
    Concurrent limit.

    Limit of concurrent request on the host
    """



class HostLimit(TypedDict, total=False):
    r"""
    TileCloud-chain host limit configuration.

    The configuration of the concurrent request limit on a host
    """

    default: "DefaultValues"
    r""" Default values. """

    hosts: dict[str, "Host"]
    r""" Hosts. """

