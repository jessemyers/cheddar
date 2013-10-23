"""
Implements a combined local and remote package index.
"""
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

    def register(self, name, version, data):
        """
        Register to the local index.
        """
        return self.local.register(name, version, data)

    def upload(self, upload_file):
        """
        Upload to the local index.
        """
        return self.local.upload(upload_file)

    def get_local_packages(self):
        """
        Show packages in the local index.
        """
        return self.local.get_local_packages()

    def get_available_releases(self, name):
        """
        Show available packages in both indexes, favoring
        the local if there are conflicts.
        """
        # remote access for packages that are local can be slow,
        # especially if there's a cache miss; we could check the
        # local index first and selectively not check the remote index,
        # at the expense of not seeing remote packages that were uploaded
        # locally
        try:
            releases = self.remote.get_available_releases(name)
        except HTTPException as error:
            if error.code != 404:
                raise
            releases = {}
        releases.update(self.local.get_available_releases(name))
        return releases

    def get_release(self, path, local):
        """
        Get release data using hint from controller.
        """
        if local:
            return self.local.get_release(path, local)
        else:
            return self.remote.get_release(path, local)
