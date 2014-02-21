"""
Shared test fixtures.
"""
from os import environ
from os.path import join
from tempfile import mkdtemp

from mock import patch
from mockredis import MockRedis

from cheddar.app import create_app


def setup(self):
    """
    Setup an instance of the Flask app with suitable temporary directories and mocks.
    """
    self.config_dir = mkdtemp()
    self.config_file = join(self.config_dir, "cheddar.conf")
    self.local_cache_dir = mkdtemp()
    self.remote_cache_dir = mkdtemp()

    with open(self.config_file, "w") as file_:
        file_.write('LOCAL_CACHE_DIR = "{}"\n'.format(self.local_cache_dir))
        file_.write('REMOTE_CACHE_DIR = "{}"\n'.format(self.remote_cache_dir))

    self.previous_config_file = environ.get("CHEDDAR_SETTINGS")
    environ["CHEDDAR_SETTINGS"] = self.config_file

    with patch('cheddar.configure.Redis', MockRedis):
        self.app = create_app(testing=True)

