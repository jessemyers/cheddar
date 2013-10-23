"""
Implements a local package index.
"""
from os import makedirs
from os.path import isdir, join

from flask import abort
from requests import codes
from werkzeug import secure_filename

from cheddar.index import Index


class LocalIndex(Index):
    """
    Support register, upload, and retreival of packages.
    """
    def __init__(self, app):
        self.redis = app.redis
        self.cache_dir = app.config["LOCAL_CACHE_DIR"]
        if not isdir(self.cache_dir):
            makedirs(self.cache_dir)

    def register(self, name, version, data):
        """
        Register a distribution:

        - Record name in list of all local packages
        - Record name, version in list of release for package
        - Record metadata for release
        """
        self.redis.sadd(self._packages_key(), name)
        self.redis.sadd(self._releases_key(name), version)
        self.redis.hmset(self._release_key(name, version), data)

    def upload(self, upload_file):
        """
        Upload a distribution:

        - Validate name and version
        - Write to local cache
        - Record location in metadata
        """
        filename = secure_filename(upload_file.filename)
        name, version = self._parse_name_and_version(filename)
        key = self._release_key(name, version)
        if not self.redis.exists(key):
            # unknown distribution
            abort(codes.not_found)

        # write to cache
        path = join(self.cache_dir, filename)
        upload_file.save(path)

        # save filename in dictionary
        self.redis.hset(key, "_filename", filename)

    def get_local_packages(self):
        return self.redis.smembers(self._packages_key())

    def get_available_releases(self, name):
        releases = {}
        for version in self.redis.smembers(self._releases_key(name)):
            filename = self.redis.hget(self._release_key(name, version), "_filename")
            if filename is not None:
                path = "local/{}".format(filename)
                releases[filename] = path
        return releases

    def get_release(self, path, local):
        with open(join(self.cache_dir, path)) as file_:
            return file_.read(), "application/octet-stream"

    def _packages_key(self):
        return "cheddar.local"

    def _releases_key(self, name):
        return "cheddar.local.{}".format(name)

    def _release_key(self, name, version):
        return "cheddar.local.{}-{}".format(name, version)

    def _parse_name_and_version(self, filename):
        """
        Guess the distribution's name and version from its filename.

        This is quite crude. A better approach would be to read the
        egg-info/PKG-INFO file and parse its contents.
        """
        root = filename
        for extension in [".tar.gz", ".zip"]:
            if root.endswith(extension):
                root = root[:- len(extension)]
        return root.split("-", 1)
