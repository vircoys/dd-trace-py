# Do not import aiohttp or anything that will import aiohttp

from tests.contrib.patch import PatchTestCase

from ddtrace.contrib.aiohttp import patch, unpatch


class AioHTTPPatchTestCase(PatchTestCase.Base):
    __integration_name__ = "aiohttp"
    __module_name__ = "aiohttp"
    __patch_func__ = patch
    __unpatch_func__ = unpatch

    def assert_module_patched(self, aiohttp):
        self.assert_wrapped(aiohttp.web_app.Application._handle)

    def assert_not_module_patched(self, aiohttp):
        self.assert_not_wrapped(aiohttp.web_app.Application._handle)

