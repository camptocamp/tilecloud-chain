"""Automatically generated file from a JSON schema."""

from typing import TypedDict

DEFAULT_LIMIT_DEFAULT = 1
""" Default value of the field path 'TileCloud-chain host limit configuration default' """


class HostLimit(TypedDict, total=False):
    """
    TileCloud-chain host limit configuration.

    The configuration of the concurrent request limit on a host
    """

    default: int
    """
    Default limit.

    default: 1
    """

    hosts: dict[str, int]
    """ Hosts. """
