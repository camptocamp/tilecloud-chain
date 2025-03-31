# TileCloud-chain host limit configuration

_The configuration of the concurrent request limit on a host_

## Properties

- <a id="properties/default"></a>**`default`** _(object)_
  - <a id="properties/default/properties/concurrent"></a>**`concurrent`** _(integer)_: Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN_HOST_CONCURRENT` environment variable. Default: `1`.
- <a id="properties/hosts"></a>**`hosts`** _(object)_: Can contain additional properties.
  - <a id="properties/hosts/additionalProperties"></a>**Additional properties** _(object)_
    - <a id="properties/hosts/additionalProperties/properties/concurrent"></a>**`concurrent`** _(integer)_: Limit of concurrent request on the host.

## Definitions
