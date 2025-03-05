import os
import subprocess

import pytest
import skimage.io
from c2cwsgiutils.acceptance.image import check_image

REGENERATE = False


def test_should_not_commit():
    assert REGENERATE is False


@pytest.mark.parametrize(
    ("url", "expected_file_name", "height", "width"),
    [
        pytest.param("http://application:8080/admin/", "not-login", 250, 800, id="not-login"),
        pytest.param("http://application:8080/admin/test", "test", 800, 800, id="test-not-login"),
        pytest.param("http://app_test_user:8080/admin", "index", 1250, 1000, id="index"),
        pytest.param("http://app_test_user:8080/admin/test", "test", 800, 800, id="test"),
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
        os.path.join(os.path.dirname(__file__), f"{expected_file_name}.expected.png"),
        generate_expected_image=REGENERATE,
    )
