import pytest

from tests.contrib.flask import BaseFlaskTestCase
from tests.utils import snapshot


class FlaskAppSecTestCase(BaseFlaskTestCase):
    @snapshot(ignores=["meta.flask.version", "meta.error.stack", "meta.http.request.headers.user-agent"])
    def test_flask_simple_attack(self):
        self.tracer._appsec_enabled = True
        # Hack: need to pass an argument to configure so that the processors are recreated
        self.tracer.configure(api_version="v0.4")
        resp = self.client.get("/.git?q=1")
        assert resp.status_code == 404

    @pytest.mark.skip("broken for now")
    @snapshot(ignores=["meta.flask.version", "meta.error.stack", "meta.http.request.headers.user-agent"])
    def test_flask_dynamic_url_param(self):
        @self.app.route("/params/<item>")
        def dynamic_url(item):
            return item

        self.tracer._appsec_enabled = True
        # Hack: need to pass an argument to configure so that the processors are recreated
        self.tracer.configure(api_version="v0.4")
        resp = self.client.get("/params/attack")
        assert resp.status_code == 200

    @snapshot(ignores=["meta.flask.version", "meta.error.stack", "meta.http.request.headers.user-agent"])
    def test_flask_querystrings(self):
        self.tracer._appsec_enabled = True
        # Hack: need to pass an argument to configure so that the processors are recreated
        self.tracer.configure(api_version="v0.4")
        self.client.get("/?a=1&b&c=d")
        self.client.get("/")
