import flask

from ddtrace.contrib.flask.patch import flask_version
from tests.utils import snapshot

from . import BaseFlaskTestCase


class FlaskErrorhandlerTestCase(BaseFlaskTestCase):
    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_default_404_handler(self):
        """
        When making a 404 request
            And no user defined error handler is defined
                We create the expected spans
        """
        # Make our 404 request
        res = self.client.get("/unknown")
        assert res.status_code == 404

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_abort_500(self):
        """
        When making a 500 request
            And no user defined error handler is defined
                We create the expected spans
        """

        @self.app.route("/500")
        def endpoint_500():
            flask.abort(500)

        # Make our 500 request
        res = self.client.get("/500")
        assert res.status_code == 500

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_abort_500_custom_handler(self):
        """
        When making a 500 request
            And a user defined error handler is defined
                We create the expected spans
        """

        @self.app.errorhandler(500)
        def handle_500(e):
            return "whoops", 200

        @self.app.route("/500")
        def endpoint_500():
            flask.abort(500)

        # Make our 500 request
        res = self.client.get("/500")
        assert res.status_code == 200
        assert res.data == b"whoops"

    @snapshot(
        ignores=["meta.flask.version", "meta.error.stack"],
        variants={"1-0": flask_version < (1, 1), "": flask_version >= (1, 1)},
    )
    def test_raise_user_exception(self):
        """
        When raising a custom user exception
            And no user defined error handler is defined
                We create the expected spans
        """

        class FlaskTestException(Exception):
            pass

        @self.app.route("/error")
        def endpoint_error():
            raise FlaskTestException("custom error message")

        # Make our 500 request
        res = self.client.get("/error")
        assert res.status_code == 500

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_raise_user_exception_handler(self):
        """
        When raising a custom user exception
            And a user defined error handler is defined
                We create the expected spans
        """

        class FlaskTestException(Exception):
            pass

        @self.app.errorhandler(FlaskTestException)
        def handle_error(e):
            return "whoops", 200

        @self.app.route("/error")
        def endpoint_error():
            raise FlaskTestException("custom error message")

        # Make our 500 request
        res = self.client.get("/error")
        assert res.status_code == 200
