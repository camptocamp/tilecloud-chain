import os

from testfixtures import LogCapture

from tilecloud_chain import controller
from tilecloud_chain.tests import CompareCase


class TestConfig(CompareCase):
    def setUp(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    def test_int_grid(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-int-grid.yaml --dump-config",
                main_func=controller.main,
            )
            log_capture.check()
