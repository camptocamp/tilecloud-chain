import os
from pathlib import Path

import pytest
from testfixtures import LogCapture

from tilecloud_chain import controller
from tilecloud_chain.tests import CompareCase


class TestConfig(CompareCase):
    def setup_method(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setup_class(cls):  # noqa
        os.chdir(Path(__file__).parent)

    @classmethod
    def teardown_class(cls):  # noqa
        os.chdir(Path(__file__).parent.parent.parent)

    @pytest.mark.asyncio
    async def test_int_grid(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-int-grid.yaml --dump-config",
                main_func=controller.async_main,
            )
            log_capture.check()
