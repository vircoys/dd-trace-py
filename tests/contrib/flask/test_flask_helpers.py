from io import BytesIO

import flask

from ddtrace import Pin
from ddtrace.contrib.flask import unpatch
from ddtrace.contrib.flask.patch import flask_version
from ddtrace.internal.compat import StringIO
from tests.utils import snapshot

from . import BaseFlaskTestCase


class FlaskHelpersTestCase(BaseFlaskTestCase):
    def test_patch(self):
        """
        When we patch Flask
            Then ``flask.jsonify`` is patched
            Then ``flask.send_file`` is patched
        """
        # DEV: We call `patch` in `setUp`
        self.assert_is_wrapped(flask.jsonify)
        self.assert_is_wrapped(flask.send_file)

    def test_unpatch(self):
        """
        When we unpatch Flask
            Then ``flask.jsonify`` is unpatched
            Then ``flask.send_file`` is unpatched
        """
        unpatch()
        self.assert_is_not_wrapped(flask.jsonify)
        self.assert_is_not_wrapped(flask.send_file)

    @snapshot(ignores=["meta.flask.version"])
    def test_jsonify(self):
        """
        When we call a patched ``flask.jsonify``
            We create a span as expected
        """
        # DEV: `jsonify` requires a active app and request contexts
        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.jsonify(dict(key="value"))
                assert isinstance(response, flask.Response)
                assert response.status_code == 200

    @snapshot(ignores=["meta.flask.version"])
    def test_jsonify_pin_disabled(self):
        """
        When we call a patched ``flask.jsonify``
            When the ``flask.Flask`` ``Pin`` is disabled
                We do not create a span
        """
        # Disable the pin on the app
        pin = Pin.get_from(self.app)
        pin.tracer.enabled = False

        # DEV: `jsonify` requires a active app and request contexts
        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.jsonify(dict(key="value"))
                assert isinstance(response, flask.Response)
                assert response.status_code == 200

    @snapshot(ignores=["meta.flask.version"])
    def test_send_file(self):
        """
        When calling a patched ``flask.send_file``
            We create the expected spans
        """
        if flask_version >= (2, 0, 0):
            fp = BytesIO(b"static file")
        else:
            fp = StringIO("static file")

        with self.app.app_context():
            with self.app.test_request_context("/"):
                # DEV: Flask >= (0, 12, 0) tries to infer mimetype, so set explicitly
                response = flask.send_file(fp, mimetype="text/plain")
                assert isinstance(response, flask.Response)
                assert response.status_code == 200

    @snapshot(ignores=["meta.flask.version"])
    def test_send_file_pin_disabled(self):
        """
        When calling a patched ``flask.send_file``
            When the app's ``Pin`` has been disabled
                We do not create any spans
        """
        pin = Pin.get_from(self.app)
        pin.tracer.enabled = False

        if flask_version >= (2, 0, 0):
            fp = BytesIO(b"static file")
        else:
            fp = StringIO("static file")

        with self.app.app_context():
            with self.app.test_request_context("/"):
                # DEV: Flask >= (0, 12, 0) tries to infer mimetype, so set explicitly
                response = flask.send_file(fp, mimetype="text/plain")
                assert isinstance(response, flask.Response)
                assert response.status_code == 200
