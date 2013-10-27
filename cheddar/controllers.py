"""
URL mappings for package index functionality.
"""
from collections import OrderedDict
from functools import wraps

from flask import abort, jsonify, make_response, render_template, request

from cheddar.auth import check_authentication
from cheddar.versions import sort_key


def create_routes(app):

    def authenticated(func):
        """
        Basic Auth decorator.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_authentication(app.redis):
                response = make_response("", 401)
                response.headers["WWW-Authenticate"] = 'Basic realm="cheddar"'
                return response
            return func(*args, **kwargs)
        return wrapper

    @app.route("/")
    def index():
        """
        Index page.
        """
        app.logger.debug("Showing index page")
        return _render("index.html")

    @app.route("/simple/")
    @app.route("/simple")
    def simple():
        """
        Simple package index.

        Lists known packages.
        """
        app.logger.debug("Showing package index")
        return _render("simple.html",
                       packages=sorted(app.index.get_local_packages()))

    @app.route("/simple/<name>/")
    @app.route("/simple/<name>")
    def list_releases(name):
        """
        Simple package index for a single package.

        Lists known releases and their locations.
        """
        app.logger.debug("Showing package index for: {}".format(name))
        releases = app.index.get_available_releases(name)

        sorted_releases = OrderedDict()
        for name in sorted(releases.keys(), key=sort_key):
            sorted_releases[name] = releases[name]

        return _render("package.html",
                       releases=sorted_releases)

    @app.route("/simple/<name>/<version>/", methods=["DELETE"])
    @app.route("/simple/<name>/<version>", methods=["DELETE"])
    @authenticated
    def remove_package(name, version):
        """
        Delete distribution data. Requires auth.
        """
        app.logger.debug("Removing package for: {} {}".format(name, version))
        app.index.remove_release(name, version)
        return ""

    @app.route("/local/<path:path>/")
    @app.route("/local/<path:path>")
    def get_local_distribution(path):
        """
        Local distribution download access.
        """
        app.logger.debug("Getting local distribution: {}".format(path))
        content_data, content_type = app.index.get_release(path, True)
        response = make_response(content_data)
        response.headers['Content-Type'] = content_type
        return response

    @app.route("/remote/<path:path>/")
    @app.route("/remote/<path:path>")
    def get_remote_distribution(path):
        """
        Remote distribution download access.

        Proxies and caches content.
        """
        app.logger.debug("Getting remote distribution: {}".format(path))
        content_data, content_type = app.index.get_release(path, False)
        response = make_response(content_data)
        response.headers['Content-Type'] = content_type
        return response

    @app.route("/pypi/", methods=["POST"])
    @app.route("/pypi", methods=["POST"])
    def pypi():
        """
        PyPI upload endpoint, handles setuptools register and upload commands.
        """
        if request.files:
            return upload()
        else:
            return register()

    @authenticated
    def upload():
        """
        Upload distribution data. Requires auth.
        """
        app.logger.debug("Uploading distribution")

        _, upload_file = next(request.files.iterlists())
        app.index.upload(upload_file[0])

        return ""

    def register():
        """
        Register a distribution.

        For no reason that I understand, setuptools does not send Basic Auth
        credentials for register, so this is *not* authenticated and only
        validates the metadata.
        """
        app.logger.debug("Registering distribution")

        metadata = {key: values[0] for key, values in request.form.iterlists()}
        if not app.index.validate_metadata(**metadata):
            abort(400)

        return ""

    def _render(template, **data):
        """
        Render response as either a template or just the raw JSON data.
        """
        if _wants_json():
            return jsonify(data)
        else:
            return render_template(template, **data)

    def _wants_json():
        """
        Should response use JSON?
        """
        for mime_type, _ in request.accept_mimetypes:
            # If we see a mime type that means HTML before JSON, return False
            if mime_type.startswith("text/html"):
                return False
            elif mime_type.startswith("application/xhtml"):
                return False
            # If we see JSON explicitly, return True
            elif mime_type.startswith("application/json"):
                return True
        # Default to False (HTML)
        return False
