import flask

from ddtrace import Pin
from ddtrace.contrib.flask import unpatch
from tests.utils import snapshot

from . import BaseFlaskTestCase


class FlaskTemplateTestCase(BaseFlaskTestCase):
    def test_patch(self):
        """
        When we patch Flask
            Then ``flask.render_template`` is patched
            Then ``flask.render_template_string`` is patched
            Then ``flask.templating._render`` is patched
        """
        # DEV: We call `patch` in `setUp`
        self.assert_is_wrapped(flask.render_template)
        self.assert_is_wrapped(flask.render_template_string)
        self.assert_is_wrapped(flask.templating._render)

    def test_unpatch(self):
        """
        When we unpatch Flask
            Then ``flask.render_template`` is unpatched
            Then ``flask.render_template_string`` is unpatched
            Then ``flask.templating._render`` is unpatched
        """
        unpatch()
        self.assert_is_not_wrapped(flask.render_template)
        self.assert_is_not_wrapped(flask.render_template_string)
        self.assert_is_not_wrapped(flask.templating._render)

    @snapshot(ignores=["meta.flask.version"])
    def test_render_template(self):
        """
        When we call a patched ``flask.render_template``
            We create the expected spans
        """
        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.render_template("test.html", world="world")
                self.assertEqual(response, "hello world")

    @snapshot(ignores=["meta.flask.version"])
    def test_render_template_pin_disabled(self):
        """
        When we call a patched ``flask.render_template``
            When the app's ``Pin`` is disabled
                We do not create any spans
        """
        pin = Pin.get_from(self.app)
        pin.tracer.enabled = False

        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.render_template("test.html", world="world")
                self.assertEqual(response, "hello world")

    @snapshot(ignores=["meta.flask.version"])
    def test_render_template_string(self):
        """
        When we call a patched ``flask.render_template_string``
            We create the expected spans
        """
        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.render_template_string("hello {{world}}", world="world")
                self.assertEqual(response, "hello world")

    @snapshot(ignores=["meta.flask.version"])
    def test_render_template_string_pin_disabled(self):
        """
        When we call a patched ``flask.render_template_string``
            When the app's ``Pin`` is disabled
                We do not create any spans
        """
        pin = Pin.get_from(self.app)
        pin.tracer.enabled = False

        with self.app.app_context():
            with self.app.test_request_context("/"):
                response = flask.render_template_string("hello {{world}}", world="world")
                self.assertEqual(response, "hello world")
