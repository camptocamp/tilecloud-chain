# TileCloud-chain host limit configuration

*The configuration of the concurrent request limit on a host*

## Properties

- **`default`** *(object)*
  - **`concurrent`** *(integer)*: Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN_HOST_CONCURRENT` environment variable. Default: `1`.
- **`hosts`** *(object)*: Can contain additional properties.
  - **Additional properties** *(object)*
    - **`concurrent`** *(integer)*: Limit of concurrent request on the host.
## Definitions

