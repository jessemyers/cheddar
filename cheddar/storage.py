"""
Implements distribution file storage.
"""
from os import makedirs, remove
from os.path import basename, exists, isdir, join

from magic import from_buffer

from cheddar.versions import is_pre_release


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
        self.release_dir = join(base_dir, "releases")
        self.pre_release_dir = join(base_dir, "pre-releases")
        self._make_base_dirs()

    def exists(self, name):
        return exists(self.compute_path(name))

    def read(self, name):
        """
        Read entry for name from storage.

        :returns: content data and content type, as a tuple
        """
        if not self.exists(name):
            return None

        with open(self.compute_path(name)) as file_:
            content_data = file_.read()
            content_type = from_buffer(content_data, mime=True)
            return content_data, content_type

    def write(self, name, data):
        """
        Write entry to storage.
        """
        self._make_base_dirs()
        path = self.compute_path(name)
        with open(path, "wb") as file_:
            file_.write(data)
        return path

    def remove(self, name):
        """
        Write entry to storage.
        """
        try:
            remove(self.compute_path(name))
            return True
        except OSError:
            return False

    def compute_path(self, path):
        """
        Compute file system path.

        Path incorporates "pre-release" or "release" to easily
        differentiate released distributions for backup.
        """
        base_dir = self.pre_release_dir if is_pre_release(path) else self.release_dir
        return join(base_dir, basename(path))

    def _make_base_dirs(self):
        """
        Ensure that base dirs exists.
        """
        for dir_ in [self.release_dir, self.pre_release_dir]:
            if not isdir(dir_):
                makedirs(dir_)
