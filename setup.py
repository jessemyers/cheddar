#!/usr/bin/env python

from setuptools import setup, find_packages

__version__ = '1.0'

__build__ = ''

setup(name='cheddar',
      version=__version__ + __build__,
      description='PyPI clone',
      author='Jesse Myers',
      author_email='jesse@locationlabs.com',
      url='https://github.com/jessemyers/cheddar',
      packages=find_packages(exclude=['*.tests']),
      setup_requires=[
          #'nose>=1.0',
      ],
      install_requires=[
          'Flask>=0.10',
          'redis>=2.8.0',
          'requests>=2.0.0',
          'BeautifulSoup>=3.2.1',
          'python-magic>=0.4.6',
      ],
      tests_require=[
      ],
      test_suite='cheddar.tests',
      entry_points={
          'console_scripts': [
              'development = cheddar.development:main',
          ]
      },
      include_package_data=True,
      )
