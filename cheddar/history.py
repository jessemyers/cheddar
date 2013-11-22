"""
Track release upload history
"""
from cheddar.defaults import HISTORY_SIZE


class History(object):

    def __init__(self, app, size=HISTORY_SIZE):
        self.redis = app.redis
        self.size = size

    @property
    def key(self):
        return "cheddar.history"

    def add(self, name, version):
        """
        Add a new/version and truncate history.
        """
        self.redis.lpush(self.key, "{}/{}".format(name, version))
        self.redis.ltrim(self.key, 0, self.size - 1)

    def remove(self, name, version):
        """
        Remove a new/version from history.
        """
        self.redis.lrem(self.key, value="{}/{}".format(name, version))

    def all(self):
        """
        Return everything in the history.
        """
        return self.redis.lrange(self.key, 0, self.size - 1)

    def __len__(self):
        """
        Return size of history.
        """
        return self.redis.llen(self.key)
