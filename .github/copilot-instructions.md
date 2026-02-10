The project must use async-friendly APIs for I/O to don't block the event loop.

- `pathlib` must not be used, use `anyio.Path` instead.
- Converting a non-async function to `async` is allowed, and requires updating all call sites to `await` it.
- `aiofiles` must not be used, use `anyio.Path` instead.
- All disk or network operation must be done with async API; avoid blocking calls on the event loop.
- Don't allow sequential `await` calls in loops; use e.g. `asyncio.gather` or `asyncio.TaskGroup`.

The user documentation in the `tilecloud_chain/USAGE.rst` file should be updated to reflect the changes in the codebase.
