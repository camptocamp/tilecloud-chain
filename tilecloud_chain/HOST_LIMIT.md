# TileCloud-chain host limit configuration

*The configuration of the concurrent request limit on a host*

## Properties

- <a id="properties/default"></a>**`default`** *(object)*
  - <a id="properties/default/properties/concurrent"></a>**`concurrent`** *(integer)*: Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN__HOST_CONCURRENT` environment variable).
- <a id="properties/hosts"></a>**`hosts`** *(object)*: Can contain additional properties.
  - <a id="properties/hosts/additionalProperties"></a>**Additional properties** *(object)*
    - <a id="properties/hosts/additionalProperties/properties/concurrent"></a>**`concurrent`** *(integer)*: Limit of concurrent request on the host.
## Definitions

