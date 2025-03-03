"""Module includes filters for dealing with errors in tiles."""

from tilecloud import Tile


class MaximumConsecutiveErrors:
    """
    Create a filter that limit the consecutive errors.

    Raises a :class:`TooManyErrors` exception when there are ``max_consecutive_errors``
    consecutive errors.

        max_consecutive_errors:
        The max number of permitted consecutive errors. Once
        exceeded a :class:`TooManyErrors` exception is raised.
    """

    def __init__(self, max_consecutive_errors: int) -> None:
        self.max_consecutive_errors = max_consecutive_errors
        self.consecutive_errors = 0

    def __call__(self, tile: Tile) -> Tile:
        """Call the filter."""
        if tile and tile.error:
            self.consecutive_errors += 1
            if self.consecutive_errors > self.max_consecutive_errors:
                if isinstance(tile.error, Exception):
                    raise TooManyError(tile) from tile.error
                raise TooManyError(tile)
        else:
            self.consecutive_errors = 0
        return tile


class MaximumErrorRate:
    """
    Create a filter that limit the error rate.

    Raises a :class:`TooManyErrors` exception when the total error rate exceeds ``max_error_rate``.

    max_error_rate:
       The maximum error rate. Once exceeded a :class:`TooManyErrors`
       exception is raised.
    min_tiles:
       The minimum number of received tiles before a :class:`TooManyErrors`
       exception can be raised. Defaults to 8.
    """

    def __init__(self, max_error_rate: float, min_tiles: int = 8) -> None:
        self.max_error_rate = max_error_rate
        self.min_tiles = min_tiles
        self.tile_count = 0
        self.error_count = 0

    def __call__(self, tile: Tile) -> Tile:
        """Call the filter."""
        self.tile_count += 1
        if tile and tile.error:
            self.error_count += 1
            if (
                self.tile_count >= self.min_tiles
                and self.error_count >= self.max_error_rate * self.tile_count
            ):
                if isinstance(tile.error, Exception):
                    raise TooManyError(tile) from tile.error
                raise TooManyError(tile)
        return tile


class TooManyError(RuntimeError):
    """TooManyErrors exception class."""

    def __init__(self, tile: Tile) -> None:
        self.last_tile = tile
        super().__init__(
            f"Too many errors, last tile in error {tile.tilecoord} {tile.formated_metadata}\n{tile.error}",
        )
