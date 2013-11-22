#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from cheddar import __version__

__build__ = ''

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(name='cheddar',
      version=__version__ + __build__,
      description='PyPI clone with Flask and Redis',
      long_description=readme + '\n\n' + history,
      author='Jesse Myers',
      author_email='jesse@locationlabs.com',
      url='https://github.com/jessemyers/cheddar',
      packages=find_packages(exclude=['*.tests']),
      setup_requires=[
          'nose>=1.3.0',
      ],
      install_requires=[
          'Flask>=0.10',
          'redis>=2.8.0',
          'requests>=2.0.0',
          'BeautifulSoup>=3.2.1',
          'python-magic>=0.4.6',
          'pkginfo>=1.1',
      ],
      tests_require=[
          'mock>=1.0.1',
          'mockredispy>=2.8.0.0',
      ],
      test_suite='cheddar.tests',
      entry_points={
          'console_scripts': [
              'development = cheddar.development:main',
          ]
      },
      include_package_data=True,
      )
