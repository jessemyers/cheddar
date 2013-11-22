"""
Default configuration values.
"""
from getpass import getuser

FORCE_READ_REQUESTS = True

# Where do we get remote package data?
INDEX_URL = "http://pypi.python.org/simple"

# Where do we find Redis?
REDIS_HOSTNAME = 'localhost'

# How many seconds should we cache version content?
VERSIONS_TTL = 600

# How long should we wait for remote HTTP requests to complete?
# Note that "pip install" has a default timeout of 15 seconds...
GET_TIMEOUT = 20

# Where should we cache remote package data?
REMOTE_CACHE_DIR = "/var/tmp/cheddar-{}/remote".format(getuser())

# Where should we cache local package data?
LOCAL_CACHE_DIR = "/var/tmp/cheddar-{}/local".format(getuser())

# How much history to keep?
HISTORY_SIZE = 50

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'debug': {
            'format': '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
            'datefmt': '%Y%m%d',
        },
        'default': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%Y%m%d',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'debug',
            'stream': 'ext://sys.stdout',
        },
        'app': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'default',
            'filename': '/var/log/cheddar/cheddar.log',
        },
    },

    'loggers': {
        '': {
            'handlers': ['console', 'app'],
            'level': 'INFO',
            'propagate': False,
        },
    }

}
