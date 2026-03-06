The project must use async-friendly APIs for I/O to don't block the event loop.

- `pathlib` must not be used, use `anyio.Path` instead.
- Converting a non-async function to `async` is allowed, and requires updating all call sites to `await` it.
- `aiofiles` must not be used, use `anyio.Path` instead.
- All disk or network operation must be done with async API; avoid blocking calls on the event loop.
- Don't allow sequential `await` calls in loops; use e.g. `asyncio.gather` or `asyncio.TaskGroup`.

## Environment variables

The environment variable should not be accessed directly (except the one defined by an other project), they should be defined in the `Settings` class in `tilecloud_chain/settings.py` and accessed through the `settings` object.

## Commit messages

The commit messages should be clear and descriptive, we don't use the conventional commits format,
the commit message should start with a capital letter.

## Bash

Use the long parameter names for clarity and maintainability.

## Development

Copy `docker-compose.override.sample.yaml` to `docker-compose.override.yaml` and use it for development.
It contains comments that can be used to activate development features.

## Documentation

The user documentation in the `tilecloud_chain/USAGE.rst` file should be updated to reflect the changes in the codebase.

All the environment variable defined in `tilecloud_chain/settings.py` should also be documented in the `tilecloud_chain/USAGE.md`.

The changes in the codebase that affect the user should be documented in the `CHANGELOG.md`.

## Tests

The new functionalities should be reasonably tested in the `tilecloud_chain/tests/` folder.

Test files in `tilecloud_chain/tests/` may not follow the rules concerning `async` requirements, as there are no performance requirements.

To run the tests, use the `make tests` command.

## Python Code Quality

To check the code quality, use the `make checks` command.

- Ensure all Python code complies with:
  - Ruff rules configured for the project.
  - Formatter validations.
  - The oldest supported Python version (check `pyproject.toml`).
  - Use modern syntax.
