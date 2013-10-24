"""
Default configuration values.
"""
from getpass import getuser

FORCE_READ_REQUESTS = True

# Where do we get remote package data?
INDEX_URL = "http://pypi.python.org/simple"

# Where do we find Redis?
REDIS_HOSTNAME = 'localhost'

# How many seconds should we cache releases content?
RELEASES_TTL = 600

# How long should we wait for remote HTTP requests to complete?
# Note that "pip install" has a default timeout of 15 seconds...
GET_TIMEOUT = 20

# Where should we cache remote package data?
REMOTE_CACHE_DIR = "/var/tmp/cheddar-{}/remote".format(getuser())

# Where should we cache local package data?
LOCAL_CACHE_DIR = "/var/tmp/cheddar-{}/local".format(getuser())

LOG_FILE = "/var/log/cheddar.log"
LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
LOG_LEVEL = "DEBUG"