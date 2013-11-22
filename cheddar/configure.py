"""
Configure the Flask application.
"""
from logging.config import dictConfig
from time import ctime

from flask import request
from redis import Redis

from cheddar import defaults
from cheddar.controllers import create_routes
from cheddar.history import History
from cheddar.index.combined import CombinedIndex
from cheddar.index.storage import DistributionStorage
from cheddar.model.distribution import Projects


def configure_app(app, debug=False, testing=False):
    """
    Load configuration and initialize collaborators.
    """

    app.debug = debug
    app.testing = testing

    _configure_from_defaults(app)
    _configure_from_environment(app)
    _configure_logging(app)
    _configure_jinja(app)

    app.redis = Redis(app.config['REDIS_HOSTNAME'])
    app.projects = Projects(app.redis, app.logger)
    app.local_storage = DistributionStorage(app.config["LOCAL_CACHE_DIR"], app.logger)
    app.remote_storage = DistributionStorage(app.config["REMOTE_CACHE_DIR"], app.logger)
    app.history = History(app)
    app.index = CombinedIndex(app)

    if app.config.get('FORCE_READ_REQUESTS'):
        # read the request fully so that nginx and uwsgi play nice
        @app.after_request
        def read_request(response):
            request.stream.read()
            return response

    create_routes(app)


def _configure_from_defaults(app):
    """
    Load configuration defaults from defaults.py in this package.
    """
    app.config.from_object(defaults)


def _configure_from_environment(app):
    """
    Load configuration from a file specified as the value of
    the CHEDDAR_SETTINGS environment variable.

    Don't complain if the variable is unset.
    """
    app.config.from_envvar("CHEDDAR_SETTINGS", silent=True)


def _configure_logging(app):
    if app.debug or app.testing:
        app.config['LOGGING']['loggers']['']['handlers'] = ['console']
        if 'app' in app.config['LOGGING']['handlers']:
            del app.config['LOGGING']['handlers']['app']

    dictConfig(app.config['LOGGING'])


def _configure_jinja(app):
    def islist(obj):
        return isinstance(obj, list)

    def localtime(timestamp):
        return ctime(timestamp)

    app.jinja_env.filters.update({"islist": islist})
    app.jinja_env.filters.update({"localtime": localtime})
