"""
Implements a local package index.
"""
from flask import abort
from json import dumps, loads
from requests import codes
from werkzeug import secure_filename

from cheddar.index import Index
from cheddar.versions import (guess_name_and_version,
                              read_metadata)


class LocalIndex(Index):
    """
    Support register, upload, and management of locally hosted projects.
    """
    def __init__(self, app):
        self.redis = app.redis
        self.storage = app.local_storage
        self.logger = app.logger

    def get_projects(self):
        self.logger.info("Getting local projects")

        local_projects = self.redis.smembers(self._projects_key())

        self.logger.debug("Obtained local projects: {}".format(list(local_projects)))
        return local_projects

    def get_versions(self, name):
        self.logger.info("Getting local versions listing for: {}".format(name))

        versions = {}
        for version in self.redis.smembers(self._versions_key(name)):
            metadata = self.get_metadata(name, version)
            if metadata is not None:
                filename = metadata["_filename"]
                location = "local/{}".format(filename)
                versions[filename] = location

        self.logger.debug("Obtained local versions listing for: {}: {}".format(name, versions))
        return versions

    def get_metadata(self, name, version):
        self.logger.info("Getting local metatdata for: {} {}".format(name, version))

        raw_metadata = self.redis.get(self._version_key(name, version))
        if raw_metadata is None:
            self.logger.info("Metadata not found for: {} {}".format(name, version))
            return None

        metadata = loads(raw_metadata)

        if "_filename" not in metadata:
            self.logger.info("Incomplete metadata for: {} {}".format(name, version))
            return None

        self.logger.debug("Obtained metadata: {} for: {}: {}".format(metadata, name, version))
        return metadata

    def get_distribution(self, location, **kwargs):
        self.logger.info("Getting local distribution: {}".format(location))

        result = self.storage.read(location)
        if result is None:
            self.logger.info("Distribution not found for: {}".format(location))
            abort(codes.not_found)

        # don't log binary version content (.tar.gz, .zip, etc.), even at debug
        return result

    def remove_version(self, name, version):
        """
        Remove redis and file data for project version.
        """
        self.logger.info("Removing version: {} {}".format(name, version))

        metadata = self.get_metadata(name, version)
        if metadata is None:
            self.logger.info("Version not found: {} {}".format(name, version))
            abort(codes.not_found)

        self.storage.remove(metadata["_filename"])

        self._remove_metadata(name, version)

    def validate_metadata(self, metadata):
        """
        Validate that name and version are provided in the metadata.
        """
        self.logger.info("Validating metadata: {}".format(metadata))
        for required in ["name", "version"]:
            if required not in metadata:
                return False
        return True

    def upload_distribution(self, upload_file):
        """
        Upload distribution file and update redis data.
        """
        filename = secure_filename(upload_file.filename)
        self.logger.info("Uploading distribution: {}".format(filename))
        # don't log binary version content (.tar.gz, .zip, etc.), even at debug

        if self.storage.exists(filename):
            self.logger.warn("Aborting upload of: {}; already exists".format(filename))
            abort(codes.conflict)

        # write to storage first because read_metadata needs a file path
        path = self.storage.write(filename, upload_file.read())

        try:
            # extract metadata
            self.logger.debug("Parsing source distribution for metadata")
            metadata = read_metadata(path)

            # make sure it validates and nothing fishy is going on
            if not self.validate_metadata(metadata) or "_filename" in metadata:
                abort(400)

            # make sure it is consistent with filename
            expected_name, expected_version = guess_name_and_version(filename)
            if metadata["name"] != expected_name or metadata["version"] != expected_version:
                self.logger.warn("Aborting upload of: {}; conflicting filename and metadata".format(filename))
                abort(codes.bad_request)

            # include local path in metadata
            metadata["_filename"] = filename
        except:
            self.logger.debug("Removing uploaded file: {} on error".format(filename))
            self.storage.remove(filename)
            raise
        else:
            self._add_metadata(metadata)

    def _projects_key(self):
        return "cheddar.local"

    def _versions_key(self, name):
        return "cheddar.local.{}".format(name)

    def _version_key(self, name, version):
        return "cheddar.local.{}-{}".format(name, version)

    def _add_metadata(self, metadata):
        name, version = metadata["name"], metadata["version"]

        self.logger.debug("Saving distribution: {} {}".format(name, version))
        self.redis.sadd(self._projects_key(), name)
        self.redis.sadd(self._versions_key(name), version)

        self.logger.debug("Saving distribution metadata: {}".format(metadata))
        self.redis.set(self._version_key(name, version), dumps(metadata))

    def _remove_metadata(self, name, version):
        # Here be race conditions...
        self.redis.delete(self._version_key(name, version))
        self.redis.srem(self._versions_key(name), version)
        if self.redis.scard(self._versions_key(name)) == 0:
            self.redis.srem(self._projects_key(), name)
            self.redis.delete(self._versions_key(name))
