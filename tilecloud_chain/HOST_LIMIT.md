# TileCloud-chain host limit configuration

_The configuration of the concurrent request limit on a host_

## Properties

- **`default`** _(object)_
  - **`concurrent`** _(integer)_: Default limit of concurrent request on the same host (can be set with the `TILECLOUD_CHAIN_HOST_CONCURRENT` environment variable. Default: `1`.
- **`hosts`** _(object)_: Can contain additional properties.
  - **Additional properties** _(object)_
    - **`concurrent`** _(integer)_: Limit of concurrent request on the host.

## Definitions
