"""
Implements a combined local and remote package index.
"""
from cheddar.index.index import Index
from cheddar.index.local import LocalIndex
from cheddar.index.remote import CachedRemoteIndex


class CombinedIndex(Index):
    """
    Combined local and remote index.
    """

    def __init__(self, app):
        self.local = LocalIndex(app)
        self.remote = CachedRemoteIndex(app)
        self.logger = app.logger

    def get_projects(self):
        """
        Get projects from the local index.
        """
        return self.local.get_projects()

    def get_versions(self, name):
        """
        Get versions from both indexes, favoring the local index.
        """
        # A project hosted locally will mask anything hosted remotedly.
        # It *is* possible to query both indexes and merge the results, but
        # this comes as the cost of the added latency of the remote index
        # on every query with a cache miss.
        #
        # At the moment, this overhead doesn't seem worthwhile.
        local_versions = self.local.get_versions(name)
        if local_versions:
            self.logger.info("Obtained versions listing for: {} using local index".format(name))
            return local_versions

        remote_versions = self.remote.get_versions(name)
        self.logger.info("Obtained versions listing for: {} using remote index".format(name))
        return remote_versions

    def get_metadata(self, name, version):
        """
        Get metadata from local index.
        """
        return self.local.get_metadata(name, version)

    def get_distribution(self, path, **kwargs):
        """
        Get distribution using hint from controller.
        """
        local = kwargs.get("local", True)
        if local:
            return self.local.get_distribution(path, **kwargs)
        else:
            return self.remote.get_distribution(path, **kwargs)

    def remove_version(self, name, version):
        """
        Remove from local index.
        """
        self.local.remove_version(name, version)

    def validate_metadata(self, metadata):
        """
        Validate against the local index.
        """
        return self.local.validate_metadata(metadata)

    def upload_distribution(self, upload_file):
        """
        Upload to the local index.
        """
        return self.local.upload_distribution(upload_file)
