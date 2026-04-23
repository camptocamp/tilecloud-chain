import subprocess
from pathlib import Path

import pytest
import skimage.io
from c2cwsgiutils.acceptance.image import check_image

REGENERATE = False


def test_should_not_commit():
    assert REGENERATE is False


@pytest.mark.parametrize(
    ("url", "expected_file_name", "height", "width"),
    [
        pytest.param("http://application:8080/tiles/admin/", "not-login", 250, 800, id="not-login"),
        pytest.param("http://application:8080/tiles/admin/test", "test", 800, 800, id="test-not-login"),
        pytest.param("http://app_test_user:8080/tiles/admin", "index", 1250, 1000, id="index"),
        pytest.param("http://app_test_user:8080/tiles/admin/test", "test", 800, 800, id="test"),
    ],
)
def test_ui(url, expected_file_name, height, width):
    subprocess.run(
        [
            "node",
            "screenshot.js",
            f"--url={url}",
            f"--width={width}",
            f"--height={height}",
            f"--output=/tmp/{expected_file_name}.png",
        ],
        check=True,
    )
    check_image(
        "/results",
        skimage.io.imread(f"/tmp/{expected_file_name}.png")[:, :, :3],
        Path(__file__).parent / f"{expected_file_name}.expected.png",
        generate_expected_image=REGENERATE,
    )


def test_openlayers_dimension_selection_uses_source_updates_and_permalink_sync():
    content = (Path(__file__).parent.parent / "templates" / "openlayers.html").read_text()

    assert "layer.setSource(nextSource);" in content
    assert "new ol.source.WMTS({" in content
    assert "source.setDimensions(nextDimensions);" not in content
    assert "url.searchParams.set('dimension_' + name, value);" in content
    assert "if (key.startsWith('dimension_'))" in content
    assert "url.searchParams.set('grid', activeGridDefinition.id);" in content


def test_openlayers_dimension_selection_disables_interim_tiles_on_error():
    content = (Path(__file__).parent.parent / "templates" / "openlayers.html").read_text()

    assert "useInterimTilesOnError: false," in content


def test_openlayers_grid_selector_handles_projection_change():
    content = (Path(__file__).parent.parent / "templates" / "openlayers.html").read_text()

    assert "const requestedGrid = urlParams.get('grid');" in content
    assert "gridDefinitions: gridDefinitions," in content
    assert "selectedGridId: selectedGridDefinition.id," in content
    assert "gridLabel.textContent = 'Grid';" in content
    assert "layer.set('selectedGridId', nextGridDefinition.id);" in content
    assert "map.setView(" in content
    assert "const canTransform = function (sourceProjectionCode, destinationProjectionCode)" in content
    assert "const transformCenterSafe = function (center, sourceProjectionCode, destinationProjectionCode)" in content
    assert "const transformExtentSafe = function (extent, sourceProjectionCode, destinationProjectionCode)" in content
    assert "const currentExtent = currentView.calculateExtent(size);" in content
    assert "transformedExtent = transformExtentSafe(" in content
    assert "nextView.fit(transformedExtent," in content
    assert "transformCenterSafe(currentCenter, currentProjectionCode, nextProjectionCode)" in content
