"""
Implements a local package index.
"""
from flask import abort
from requests import codes
from pkginfo import SDist
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
        - Write to local storage
        - Record location in metadata
        """
        filename = secure_filename(upload_file.filename)

        if self.storage.exists(filename):
            abort(codes.conflict)

        # write to storage first because SDist needs a file path
        path = self.storage.write(filename, upload_file.read())

        try:
            # derive name and version from sdist
            distribution = SDist(path)
            name, version = distribution.name, distribution.version
            expected_name, expected_version = guess_name_and_version(filename)

            # make file names match expectations
            if name != expected_name or version != expected_version:
                abort(codes.bad_request)

            key = self._release_key(name, version)

            # ensure that register was called
            if not self.redis.exists(key):
                abort(codes.not_found)

            # ensure that upload wasn't already performed
            if self.redis.hget(key, "_filename"):
                abort(codes.conflict)
        except:
            self.storage.remove(filename)
            raise
        else:
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
        result = self.storage.read(path)
        if result is None:
            abort(codes.not_found)
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
