"""
Configure the Flask application.
"""
import logging
from logging.config import dictConfig

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
    _configure_logging(app)
    _configure_jinja(app)

    dictConfig(app.config['LOGGING'])

    app.redis = Redis(app.config['REDIS_HOSTNAME'])
    app.local_storage = DistributionStorage(app.config["LOCAL_CACHE_DIR"], app.logger)
    app.remote_storage = DistributionStorage(app.config["REMOTE_CACHE_DIR"], app.logger)
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
    if not app.debug and not app.testing:
        file_handler = TimedRotatingFileHandler(app.config["LOG_FILE"], when='d')
        file_handler.setLevel(app.config["LOG_LEVEL"])
        file_handler.setFormatter(logging.Formatter(
            app.config["LOG_FORMAT"]
        ))

        app.logger.addHandler(file_handler)


def _configure_jinja(app):
    def islist(obj):
        return isinstance(obj, list)

    app.jinja_env.filters.update({"islist": islist})
