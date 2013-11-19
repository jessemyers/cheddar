"""
Production WSGI hook.

Creates and configures a new application.

By default uwsgi will use a module's 'application' value.
"""
from cheddar.app import create_app


application = create_app()
