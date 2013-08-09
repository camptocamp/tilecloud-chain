# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = (
    open(os.path.join(here, 'README.rst')).read() + '\n\n' +
    open(os.path.join(here, 'CHANGES.rst')).read()
)

install_requires = [
    'tilecloud>=0.2dev-20130808',
    'psycopg2',
    'Shapely',
    'boto>=2.0',
    'PyYAML',
    'jinja2',
    'pyramid',
    'simplejson',
    'requests',
]
if sys.version_info < (2, 7):
    install_requires.extend([
        'argparse',
        'bsddb3',
    ])
if sys.version_info >= (3, 0):
    install_requires.extend([
        'bsddb3',
    ])

setup_requires = [
    'nose==1.3.0',
]
tests_require = [
    'coverage',
    'unittest2',
    'testfixtures',
]

setup(
    name='tilecloud-chain',
    version='0.7',
    description="""
The goal of TileCloud Chain is to have tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally use an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, on S3, on Berkley DB (``bsddb``), on MBTiles, or on local filesystem.

Feature:

- Generate tiles.
- Drop empty tiles.
- Drop tiles outside a geometry or a bbox.
- Use MetaTiles
- Generate GetCapabilities.
- Generate OpenLayers example page.
- Obtain the hash of an empty tile
- In future, measure tile generation speed
- Calculate cost and generation time.
- In future, manage the AWS hosts that generate tiles.
- Delete empty tiles.
""",
    long_description=README,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS',
    ],
    author='Stéphane Brunner',
    author_email='stephane.brunner@camptocamp.com',
    url='http://github.com/sbrunner/tilecloud-chain',
    license='BSD',
    keywords='gis tilecloud chain',
    packages=find_packages(exclude=["*.tests", "*.tests.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    entry_points={
        'console_scripts': [
            'generate_tiles = tilecloud_chain.generate:main',
            'generate_controller = tilecloud_chain.controller:main',
        ],
        'pyramid.scaffold': [
            'tilecloud_chain = tilecloud_chain.scaffolds:Create',
        ],
        'paste.app_factory': [
            'server = tilecloud_chain.server:app_factory',
        ],
    }
)
