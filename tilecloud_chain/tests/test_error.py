import os

from testfixtures import LogCapture

from tilecloud_chain import controller, generate
from tilecloud_chain.tests import CompareCase


class TestError(CompareCase):
    def setUp(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    def test_resolution(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_resolutions.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "ERROR", "The resolution 0.1 * resolution_scale 5 is not an integer."),
            )

    def test_mapnik_grid_meta(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_mapnik_grid_meta.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    "The layer 'b' is of type Mapnik/Grid, that can't support matatiles.",
                )
            )

    def test_type(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -v -c tilegeneration/wrong_type.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_type.yaml:10:10 grids.swissgrid_2.srs: {} is not of type 'string' (rule: properties.grids.additionalProperties.properties.srs.type)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3.srs: 'epsg:21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4.srs: 'epsg21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'srs' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'srs' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:22:3 layers: 'hi!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.propertyNames.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!.wmts_style: 'yo!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.wmts_style.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!.wmts_style: 'yo!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.wmts_style.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'layers' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'url' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.default: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.default.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.default: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.default.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.name: 'DATE!' does not match '(?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.name.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.name: 'DATE!' does not match '(?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.name.pattern)
-- tilegeneration/wrong_type.yaml:27:19 layers.hi!.dimensions.0.generate.0: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.generate.items.pattern)
-- tilegeneration/wrong_type.yaml:27:19 layers.hi!.dimensions.0.generate.0: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.generate.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.0: '2005!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.0: '2005!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.1: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.1: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.2: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.2: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:29:9 layers.hi!.dimensions.1.default: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.default.type)
-- tilegeneration/wrong_type.yaml:29:9 layers.hi!.dimensions.1.default: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.default.type)
-- tilegeneration/wrong_type.yaml:2:3 grids.swissgrid_6: None is not of type 'object' (rule: properties.grids.additionalProperties.type)
-- tilegeneration/wrong_type.yaml:2:3 grids: 'swissgrid!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$' (rule: properties.grids.propertyNames.pattern)
-- tilegeneration/wrong_type.yaml:31:19 layers.hi!.dimensions.1.generate.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.generate.items.type)
-- tilegeneration/wrong_type.yaml:31:19 layers.hi!.dimensions.1.generate.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.generate.items.type)
-- tilegeneration/wrong_type.yaml:32:17 layers.hi!.dimensions.1.values.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.type)
-- tilegeneration/wrong_type.yaml:32:17 layers.hi!.dimensions.1.values.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.type)
-- tilegeneration/wrong_type.yaml:3:5 grids.swissgrid_1.resolution_scale: 5.5 is not of type 'integer' (rule: properties.grids.additionalProperties.properties.resolution_scale.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.0: 'a' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.1: 'b' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.2: 'c' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:6:10 grids.swissgrid_1.srs: ['EPSG:21781'] is not of type 'string' (rule: properties.grids.additionalProperties.properties.srs.type)""",  # noqa
                )
            )

    def test_zoom_errors(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-nosns.yaml -l point --zoom 4,10",
                main_func=generate.main,
            )
            log_capture.check_present(
                (
                    "tilecloud_chain",
                    "WARNING",
                    "zoom 10 is greater than the maximum zoom 4 of grid swissgrid_5 of layer point, ignored.",
                ),
                (
                    "tilecloud_chain",
                    "WARNING",
                    "zoom 4 corresponds to resolution 5 "
                    "is smaller than the 'min_resolution_seed' 10 of layer point, ignored.",
                ),
            )

    def test_wrong_srs_auth(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs_auth.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs_auth.yaml:3:5 grids.swissgrid_01.srs: 'toto:21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",  # noqa
                )
            )

    def test_wrong_srs_id(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs_id.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs_id.yaml:3:5 grids.swissgrid_01.srs: 'EPSG:21781a' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",  # noqa
                )
            )

    def test_wrong_srs(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs.yaml:3:5 grids.swissgrid_01.srs: 'EPSG21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",
                )
            )

    def test_wrong_map(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_map.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_map.yaml:3:5 layers.test.empty_tile_detection: 'test' is not of type 'object' (rule: properties.layers.additionalProperties.anyOf.0.properties.empty_tile_detection.type)
-- tilegeneration/wrong_map.yaml:3:5 layers.test.empty_tile_detection: 'test' is not of type 'object' (rule: properties.layers.additionalProperties.anyOf.1.properties.empty_tile_detection.type)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'layers' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'url' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'wmts_style' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'wmts_style' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)""",
                )
            )

    def test_wrong_sequence(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_sequence.yaml",
                main_func=controller.main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test.resolutions: 'test' is not of type 'array' (rule: properties.grids.additionalProperties.properties.resolutions.type)
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test: 'srs' is a required property (rule: properties.grids.additionalProperties.required)""",
                )
            )
