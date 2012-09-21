# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

install_requires = [
    'tilecloud',
    'psycopg2',
    'Shapely',
    'boto',
    'PasteScript',
    'PyYAML',
    'jinja2',
]

setup(
        name='tilecloud-chain',
        version='0.1',
        description='tilecloud chain',
        long_description='tilecloud chain',
        classifiers=[
            "Programming Language :: Python",
        ],
        author='Stéphane Brunner',
        author_email='stephane.brunner@camptocamp.com',
        url='http://github.com/sbrunner/tilecloud-chain',
        license='BSD',
        keywords='gis tilecloud chain',
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        install_requires=install_requires,
        entry_points={
            'console_scripts': [
                'generate_tiles = tilecloud_chain.generate_tiles:main',
                'generate_tiles_controller = tilecloud_chain.generate_tiles_controller:main',
            ],
        }
)
