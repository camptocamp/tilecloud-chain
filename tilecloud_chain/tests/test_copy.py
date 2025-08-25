import os
import shutil
from pathlib import Path

import requests

from tilecloud_chain import copy_
from tilecloud_chain.tests import CompareCase


class TestGenerate(CompareCase):
    def setUp(self) -> None:
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):
        os.chdir(Path(__file__).parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")
        Path("/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/").mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        os.chdir(Path(__file__).parent.parent.parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")

    def test_copy(self) -> None:
        with Path("/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png").open("w") as f:
            f.write("test image")

        for d in ("-d", "-q", "-v"):
            self.assert_cmd_equals(
                cmd=f".build/venv/bin/generate-copy {d} -c tilegeneration/test-copy.yaml src dst",
                main_func=copy_.main,
                regex=True,
                expected=(
                    """The tile copy of layer 'point_hash' is finish
Nb copy tiles: 1
Nb errored tiles: 0
Nb dropped tiles: 0
Total time: 0:00:[0-9][0-9]
Total size: 10 o
Time per tile: [0-9]+ ms
Size per tile: 10(.0)? o

"""
                    if d != "-q"
                    else ""
                ),
                empty_err=True,
            )
        with Path("/tmp/tiles/dst/1.0.0/point_hash/default/21781/0/0/0.png").open() as f:
            assert f.read() == "test image"

    def test_process(self) -> None:
        for d in ("-vd", "-q", "-v", ""):
            response = requests.get(
                "http://mapserver:8080/?STYLES=default&SERVICE=WMS&FORMAT=\
image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&VERSION=1.1.1&BBOX=\
%28560800.0%2C+158000.0%2C+573600.0%2C+170800.0%29&LAYERS=point&SRS=EPSG%3A21781",
            )
            response.raise_for_status()
            with Path("/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png").open("wb") as out:
                out.write(response.content)
            statinfo = Path(
                "/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png",
            ).stat()
            assert statinfo.st_size == 755

            self.assert_cmd_equals(
                cmd=f".build/venv/bin/generate-process {d} -c "
                "tilegeneration/test-copy.yaml --cache src optipng",
                main_func=copy_.process,
                regex=True,
                expected=(
                    """The tile process of layer 'point_hash' is finish
Nb process tiles: 1
Nb errored tiles: 0
Nb dropped tiles: 0
Total time: 0:00:[0-9][0-9]
Total size: 103 o
Time per tile: [0-9]+ ms
Size per tile: 103(.0)? o

"""
                    if d != "-q"
                    else ""
                ),
                empty_err=True,
            )
            statinfo = Path(
                "/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png",
            ).stat()
            assert statinfo.st_size == 103
