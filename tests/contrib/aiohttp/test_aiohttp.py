import asyncio

import aiohttp
from aiohttp import web

from ddtrace.contrib.aiohttp import patch
from ..asyncio.utils import mark_asyncio_no_close as mark_asyncio
from .utils import TraceTestCase


async def hello(request):
    return web.Response(text="Hello, world")


async def test_hello(aiohttp_client, spans):
    app = web.Application()
    app.router.add_get("/", hello)
    client = await aiohttp_client(app)
    resp = await client.get("/")
    assert resp.status == 200
    text = await resp.text()
    assert "Hello, world" in text
    assert len(spans)


"""
class TestAioHTTP(TraceTestCase):

    def setUp(self):
        super().setUp()
        patch()
        asyncio.set_event_loop(self.loop)

    @mark_asyncio
    async def test_something(self):
        app = aiohttp.web_app.Application()
        await app._handle(None)
        # assert isinstance(aiohttp.web_app.Application._handle, wrapt.ObjectProxy)
"""
