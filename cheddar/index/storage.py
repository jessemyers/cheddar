"""
Implements distribution file storage.
"""
from os import makedirs, remove, walk
from os.path import basename, exists, isdir, join

from magic import from_buffer

from cheddar.model.versions import is_pre_release


class DistributionStorage(object):
    """
    File system storage with release/pre-release partitioning.
    """

    def __init__(self, base_dir, logger):
        """
        Initialize storage.

        :param base_dir: root directory for storage
        """
        self.logger = logger
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
            self.logger.debug("No file exists for: {}".format(name))
            return None

        with open(self.compute_path(name)) as file_:
            content_data = file_.read()
            content_type = from_buffer(content_data, mime=True)
            self.logger.debug("Computed content type: {} for: {}".format(content_type, name))
            return content_data, content_type

    def write(self, name, data):
        """
        Write entry to storage.
        """
        self._make_base_dirs()
        path = self.compute_path(name)
        with open(path, "wb") as file_:
            file_.write(data)
        self.logger.debug("Wrote file for: {}".format(name))
        return path

    def remove(self, name):
        """
        Write entry to storage.
        """
        try:
            remove(self.compute_path(name))
            self.logger.debug("Removed file for: {}".format(name))
            return True
        except OSError:
            self.logger.debug("Unable to remove file for: {}".format(name))
            return False

    def compute_path(self, name):
        """
        Compute file system path.

        Path incorporates "pre-release" or "release" to easily
        differentiate released distributions for backup.
        """
        base_dir = self.pre_release_dir if is_pre_release(name) else self.release_dir
        path = join(base_dir, basename(name))
        self.logger.debug("Computed path: {} for: {}".format(path, name))
        return path

    def __iter__(self):
        for dirpath, _, filenames in walk(self.base_dir):
            for filename in filenames:
                yield join(dirpath, filename)

    def _make_base_dirs(self):
        """
        Ensure that base dirs exists.
        """
        for dir_ in [self.release_dir, self.pre_release_dir]:
            if not isdir(dir_):
                makedirs(dir_)
