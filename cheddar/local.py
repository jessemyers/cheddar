"""
Implements a local package index.
"""
from flask import abort
from requests import codes
from werkzeug import secure_filename

from cheddar.index import Index
from cheddar.versions import guess_name_and_version, read_metadata


class LocalIndex(Index):
    """
    Support register, upload, and retreival of packages.
    """
    def __init__(self, app):
        self.redis = app.redis
        self.storage = app.local_storage
        self.logger = app.logger

    def register(self, name, version, metadata):
        """
        Register a distribution:

        - Record name in list of all local packages
        - Record name, version in list of release for package
        - Record metadata for release
        """
        self.logger.info("Registering local distribution: {} {}".format(name, version))
        self.redis.sadd(self._packages_key(), name)
        self.redis.sadd(self._releases_key(name), version)
        self.logger.debug("Saving local distribution meta data: {}".format(metadata))
        self.redis.hmset(self._release_key(name, version), metadata)

    def upload(self, upload_file):
        """
        Upload a distribution:

        - Validate name and version
        - Write to local storage
        - Record location in metadata
        """
        filename = secure_filename(upload_file.filename)
        self.logger.info("Uploading distribution: {}".format(filename))
        # don't log binary release content (.tar.gz, .zip, etc.), even at debug

        if self.storage.exists(filename):
            self.logger.warn("Aborting upload of: {}; already exists".format(filename))
            abort(codes.conflict)

        # write to storage first because SDist needs a file path
        path = self.storage.write(filename, upload_file.read())

        try:
            # derive name and version from sdist
            self.logger.debug("Parsing source distribution for name and version")
            metadata = read_metadata(path)
            name, version = metadata["name"], metadata["version"]
            expected_name, expected_version = guess_name_and_version(filename)

            # make file names match expectations
            if name != expected_name or version != expected_version:
                self.logger.warn("Aborting upload of: {}; conflicting metadata".format(filename))
                abort(codes.bad_request)

            key = self._release_key(name, version)

            # ensure that register was called
            if not self.redis.exists(key):
                self.logger.warn("Aborting upload of: {}; not registered".format(filename))
                abort(codes.not_found)

            # ensure that upload wasn't already performed
            if self.redis.hget(key, "_filename"):
                self.logger.warn("Aborting upload of: {}; already uploaded".format(filename))
                abort(codes.conflict)
        except:
            self.logger.debug("Removing uploaded file: {} on error".format(filename))
            self.storage.remove(filename)
            raise
        else:
            # save filename in dictionary
            self.redis.hset(key, "_filename", filename)

    def get_local_packages(self):
        self.logger.info("Getting local packages")

        local_packages = self.redis.smembers(self._packages_key())
        self.logger.debug("Obtained local packages: {}".format(list(local_packages)))

        return local_packages

    def get_available_releases(self, name):
        self.logger.info("Getting local releases listing for: {}".format(name))
        releases = {}
        for version in self.redis.smembers(self._releases_key(name)):
            filename = self.redis.hget(self._release_key(name, version), "_filename")
            if filename is not None:
                path = "local/{}".format(filename)
                releases[filename] = path

        self.logger.debug("Obtained local releases listing for: {}: {}".format(name, releases))
        return releases

    def get_release(self, path, local):
        self.logger.info("Getting local release: {}".format(path))

        result = self.storage.read(path)
        if result is None:
            self.logger.info("Release not found for: {}: {}".format(path))
            abort(codes.not_found)

        # don't log binary release content (.tar.gz, .zip, etc.), even at debug
        return result

    def remove_release(self, name, version):
        """
        Remove a distribution.

        - Remove from local storage.
        - Remove register record.
        - Remove version from releases list.
        - If no versions are left, remove from packages list.
        """
        self.logger.info("Removing release: {} {}".format(name, version))

        key = self._release_key(name, version)
        if not self.redis.exists(key):
            self.logger.info("Release not found: {} {}".format(name, version))
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
