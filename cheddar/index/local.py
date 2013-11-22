"""
Implements a local package index.
"""
from os.path import basename
from time import time

from flask import abort
from requests import codes
from werkzeug import secure_filename

from cheddar.index.index import Index
from cheddar.model.distribution import Version
from cheddar.model.versions import (guess_name_and_version,
                                    read_metadata)


class LocalIndex(Index):
    """
    Support register, upload, and management of locally hosted projects.
    """
    def __init__(self, app):
        self.redis = app.redis
        self.storage = app.local_storage
        self.logger = app.logger
        self.projects = app.projects
        self.history = app.history

    def get_projects(self):
        self.logger.info("Getting local projects")

        projects = self.projects.list_projects()

        self.logger.debug("Obtained local projects: {}".format(projects))
        return projects

    def get_versions(self, name):
        self.logger.info("Getting local versions listing for: {}".format(name))

        project = self.projects.get_project(name)
        if project is None:
            return None

        versions = {}
        for project_version in project.get_versions():
            metadata = project_version.get_metadata()
            if metadata is None:
                continue
            filename = metadata[Version.FILENAME]
            versions[filename] = "/local/{}".format(filename)

        self.logger.debug("Obtained local versions listing for: {}".format(name))
        return versions

    def get_metadata(self, name, version):
        self.logger.info("Getting local metatdata for: {} {}".format(name, version))

        metadata = self.projects.get_metadata(name, version)

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

        metadata = self.projects.get_metadata(name, version)
        if metadata is None:
            self.logger.info("Version not found: {} {}".format(name, version))
            abort(codes.not_found)

        self.storage.remove(metadata[Version.FILENAME])
        self.projects.remove_metadata(name, version)
        self.history.remove(name, version)

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
            metadata = self._get_metadata(path, filename)
        except:
            self.logger.debug("Removing uploaded file: {} on error".format(filename))
            self.storage.remove(filename)
            raise
        else:
            self.history.add(metadata["name"], metadata["version"])
            self.projects.add_metadata(metadata)

    def rebuild(self):
        """
        Rebuild redis index from file data.

        Rebuilding the index does not currently discard old index data,
        which could be accomplished by computing the set of all keys
        before and after the rebuild and removing the difference.
        """
        for path in self.storage:
            filename = basename(path)
            metadata = self._get_metadata(path, filename)
            self.projects.add_metadata(metadata)

    def _get_metadata(self, path, filename):
        metadata = read_metadata(path)

        # make sure metadata validates
        if not self.validate_metadata(metadata):
            abort(codes.bad_request)

        # make sure nothing fishy is going on
        if metadata.get(Version.FILENAME) not in [None, filename]:
            abort(codes.bad_request)

        # make sure metadata is consistent with filename
        expected_name, expected_version = guess_name_and_version(filename)
        if metadata["name"] != expected_name or metadata["version"] != expected_version:
            self.logger.warn("Aborting upload of: {}; conflicting filename and metadata".format(filename))
            abort(codes.bad_request)

        # include local path in metadata
        metadata[Version.FILENAME] = filename
        # add upload timestamp
        metadata["_uploaded_timestamp"] = time()

        return metadata
