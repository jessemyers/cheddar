"""
Implements distribution file storage.
"""
from os import makedirs
from os.path import basename, exists, isdir, join

from magic import from_buffer


class DistributionStorage(object):
    """
    A section
    """

    def __init__(self, base_dir):
        """
        Initialize storage.

        :param base_dir: root directory for storage
        """
        self.base_dir = base_dir
        self._make_cache_dir()

    def read(self, path):
        if not exists(self._cache_path(path)):
            return None

        with open(self._cache_path(path)) as file_:
            content_data = file_.read()
            content_type = from_buffer(content_data, mime=True)
            return content_data, content_type

    def write(self, path, data):
        self._make_cache_dir()
        with open(self._cache_path(path), "wb") as file_:
            file_.write(data)

    def _make_cache_dir(self):
        if not isdir(self.base_dir):
            makedirs(self.base_dir)

    def _cache_path(self, path):
        return join(self.base_dir, basename(path))
