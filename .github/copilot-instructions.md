The project must use async-friendly APIs for I/O to don't block the event loop.

- `pathlib` must not be used, use `anyio.Path` instead.
- Converting a non-async function to `async` is allowed, and requires updating all call sites to `await` it.
- `aiofiles` must not be used, use `anyio.Path` instead.
- All disk or network operation must be done with async API; avoid blocking calls on the event loop.
- Don't allow sequential `await` calls in loops; use e.g. `asyncio.gather` or `asyncio.TaskGroup`.

## Bash

Use the long parameter names for clarity and maintainability.

## Documentation

The user documentation in the `tilecloud_chain/USAGE.rst` file should be updated to reflect the changes in the codebase.

## Tests

The new functionalities should be reasonably tested in the `tilecloud_chain/tests/` folder.

Test files in `tilecloud_chain/tests/` may not follow the rules concerning `async` requirements, as there are no performance requirements.
