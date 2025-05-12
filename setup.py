import os
import site
import sys

from setuptools import find_packages, setup

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as r:
    with open(os.path.join(here, "CHANGES.md"), encoding="utf-8") as c:
        README = r.read() + "\n\n" + c.read()

install_requires = [
    "c2cwsgiutils",
    "Jinja2",
    "jsonschema",
    "pyramid_mako",
    "PyYAML",
    "Shapely",
    "tilecloud>=1.3.0",
]

setup(
    name="tilecloud-chain",
    version="1.17.0",
    description=(
        "Tools to generate tiles from WMS or Mapnik, to S3, "
        "Berkeley DB, MBTiles, or local filesystem in WMTS layout using "
        "Amazon cloud services."
    ),
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Pyramid",
        "Intended Audience :: Other Audience",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: GIS",
        "Typing :: Typed",
    ],
    author="Stéphane Brunner",
    author_email="stephane.brunner@camptocamp.com",
    url="http://github.com/camptocamp/tilecloud-chain",
    license="BSD",
    keywords="gis tilecloud chain",
    packages=find_packages(exclude=["*.tests", "*.tests.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "generate_tiles = tilecloud_chain.generate:main",
            "generate_controller = tilecloud_chain.controller:main",
            "generate_cost = tilecloud_chain.cost:main",
            "generate_copy = tilecloud_chain.copy_:main",
            "generate_process = tilecloud_chain.copy_:process",
            "import_expiretiles = tilecloud_chain.expiretiles:main",
            "generate-tiles = tilecloud_chain.generate:main",
            "generate-controller = tilecloud_chain.controller:main",
            "generate-cost = tilecloud_chain.cost:main",
            "generate-copy = tilecloud_chain.copy_:main",
            "generate-process = tilecloud_chain.copy_:process",
            "import-expiretiles = tilecloud_chain.expiretiles:main",
        ],
        "pyramid.scaffold": ["tilecloud_chain = tilecloud_chain.scaffolds:Create"],
        "paste.app_factory": ["main = tilecloud_chain.server:main"],
    },
    package_data={"tilecloud_chain": ["py.typed"]},
)
