# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

install_requires = [
    'tilecloud>=0.2dev-20130516',
    'psycopg2',
    'Shapely',
    'boto>=2.0',
    'PyYAML',
    'jinja2',
    'pyramid',
    'simplejson',
]
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
        version='0.6',
        description='tilecloud chain',
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
        }
)
