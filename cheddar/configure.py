"""
Configure the Flask application.
"""
from flask import request
from redis import Redis

from cheddar import defaults
from cheddar.combined import CombinedIndex
from cheddar.controllers import create_routes
from cheddar.storage import DistributionStorage


def configure_app(app, debug=False, testing=False):
    """
    Load configuration and initialize collaborators.
    """
    app.debug = debug
    app.testing = testing

    _configure_from_defaults(app)
    _configure_from_environment(app)

    app.redis = Redis(app.config['REDIS_HOSTNAME'])
    app.local_storage = DistributionStorage(app.config["LOCAL_CACHE_DIR"])
    app.remote_storage = DistributionStorage(app.config["REMOTE_CACHE_DIR"])
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
