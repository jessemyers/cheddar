"""
Implements a local package index.
"""
from flask import abort
from requests import codes
from werkzeug import secure_filename

from cheddar.index import Index
from cheddar.versions import guess_name_and_version


class LocalIndex(Index):
    """
    Support register, upload, and retreival of packages.
    """
    def __init__(self, app):
        self.redis = app.redis
        self.storage = app.local_storage
        self.logger = app.logger

    def register(self, name, version, data):
        """
        Register a distribution:

        - Record name in list of all local packages
        - Record name, version in list of release for package
        - Record metadata for release
        """
        self.logger.debug("Registering local distribution", name, version, data)
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
        self.logger.info("Starting local upload")
        self.logger.debug(upload_file)
        filename = secure_filename(upload_file.filename)

        # Crude. A better approach would be to parse the egg-info/PKG-INFO file.
        name, version = guess_name_and_version(filename)

        key = self._release_key(name, version)
        if not self.redis.exists(key):
            # unknown distribution
            abort(codes.not_found)

        if self.redis.hget(key, "_filename") and self.storage.exists(filename):
            # already here
            self.logger.error("Upload failed")
            abort(codes.conflict)

        # write to cache
        self.storage.write(filename, upload_file.read())

        # save filename in dictionary
        self.redis.hset(key, "_filename", filename)

    def get_local_packages(self):
        self.logger.info("Getting local packages")
        local_packages = self.redis.smembers(self._packages_key())
        self.logger.debug(local_packages)
        return local_packages

    def get_available_releases(self, name):
        self.logger.info("Available local releases list")
        releases = {}
        for version in self.redis.smembers(self._releases_key(name)):
            filename = self.redis.hget(self._release_key(name, version), "_filename")
            if filename is not None:
                path = "local/{}".format(filename)
                releases[filename] = path
        self.logger.debug(releases)
        return releases

    def get_release(self, path, local):
        result = self.storage.read(path)
        if result is None:
            self.logger.error("Releases not found", codes.not_found)
            abort(codes.not_found)
        self.logger.debug("Releases list", result)
        return result

    def remove_release(self, name, version):
        """
        Remove a distribution.

        - Remove from local storage.
        - Remove register record.
        - Remove version from releases list.
        - If no versions are left, remove from packages list.
        """
        key = self._release_key(name, version)
        if not self.redis.exists(key):
            abort(codes.not_found)

        filename = self.redis.hget(key, "_filename")
        self.storage.remove(filename)

        # Here be race conditions...
        self.redis.delete(key)
        self.redis.srem(self._releases_key(name), version)
        if self.redis.scard(self._releases_key(name)) == 0:
            self.redis.srem(self._packages_key(), name)

    def _packages_key(self):
        return "cheddar.local"

    def _releases_key(self, name):
        return "cheddar.local.{}".format(name)

    def _release_key(self, name, version):
        return "cheddar.local.{}-{}".format(name, version)
