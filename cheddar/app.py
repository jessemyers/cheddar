"""
Factory entry point for the Flask application.

Allows development and deployment to configurate the Flask
instance differently.
"""
from flask import Flask

from cheddar.configure import configure_app


def create_app(debug=False, testing=False):
    """
    Create and configure the application.
    """
    app = Flask(__name__.split('.')[0])
    configure_app(app, debug=debug, testing=testing)
    return app
