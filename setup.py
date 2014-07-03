# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = (
    open(os.path.join(here, 'README.rst')).read() + '\n\n' +
    open(os.path.join(here, 'CHANGES.rst')).read()
)

install_requires = open(os.path.join(here, 'requirements.txt')).read().splitlines()

if sys.version_info < (2, 7):
    install_requires.extend([
        'argparse',
    ])
if sys.version_info >= (3, 0) or (
    'BERKELEYDB_LIBDIR' in os.environ and 'BERKELEYDB_INCDIR' in os.environ
):
    install_requires.extend([
        'bsddb3',
    ])

setup_requires = [
    'nose',
]
tests_require = [
    'coverage',
    'unittest2',
    'testfixtures',
]

setup(
    name='tilecloud-chain',
    version='0.9.0',
    description="""
Tools to generates tiles from WMS or Mapnik, to S3, Berkley DB, MBTiles, """
    """or local filesystem in WMTS layout using Amazon cloud services.
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
            'generate_amazon = tilecloud_chain.amazon:main',
            'generate_cost = tilecloud_chain.cost:main',
            'generate_copy = tilecloud_chain.copy_:main',
            'generate_process = tilecloud_chain.copy_:process',
            'import_expiretiles = tilecloud_chain.expiretiles:main',
        ],
        'pyramid.scaffold': [
            'tilecloud_chain = tilecloud_chain.scaffolds:Create',
            'tilecloud_chain_ec2 = tilecloud_chain.scaffolds:Ec2',
        ],
        'paste.app_factory': [
            'server = tilecloud_chain.server:app_factory',
        ],
    }
)
