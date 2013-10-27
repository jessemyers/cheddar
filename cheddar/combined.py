"""
Implements a combined local and remote package index.
"""
from requests import codes
from werkzeug.exceptions import HTTPException

from cheddar.index import Index
from cheddar.local import LocalIndex
from cheddar.remote import CachedRemoteIndex


class CombinedIndex(Index):
    """
    Combined local and remote index.
    """

    def __init__(self, app):
        self.local = LocalIndex(app)
        self.remote = CachedRemoteIndex(app)
        self.logger = app.logger

    def validate_metadata(self, **metadata):
        """
        Validate against the local index.
        """
        return self.local.validate_metadata(**metadata)

    def upload_distribution(self, upload_file):
        """
        Upload a distribution to the local index.
        """
        return self.local.upload_distribution(upload_file)

    def get_packages(self):
        """
        Show packages in the local index.
        """
        return self.local.get_packages()

    def get_releases(self, name):
        """
        Show packages from both indexes, favoring local packages if there are conflicts.
        """
        # remote access for packages that are local can be slow,
        # especially if there's a cache miss; we could check the
        # local index first and selectively not check the remote index,
        # at the expense of not seeing remote packages that were uploaded
        # locally
        self.logger.info("Computing combined releases listing for: {}".format(name))
        try:
            releases = self.remote.get_releases(name)
        except HTTPException as error:
            if error.code != codes.not_found:
                self.logger.warn("Unexpected response for remove releases listing for: {}: {}".format(name, error.code))
                raise
            releases = {}
        releases.update(self.local.get_releases(name))

        self.logger.debug("Obtained combined releases listing for: {}: {}".format(name, releases))
        return releases

    def get_release(self, path, local):
        """
        Get release data using hint from controller.
        """
        if local:
            return self.local.get_release(path, local)
        else:
            return self.remote.get_release(path, local)

    def remove_release(self, name, version):
        """
        Remove local release.
        """
        self.local.remove_release(name, version)
