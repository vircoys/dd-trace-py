import asyncio
import pytest
import time


from ddtrace.context import Context
from ddtrace.internal.context_manager import CONTEXTVARS_IS_AVAILABLE
from ddtrace.provider import DefaultContextProvider
from ddtrace.contrib.asyncio.patch import patch, unpatch
from ddtrace.contrib.asyncio.helpers import set_call_context

from tests.opentracer.utils import init_tracer
from .utils import AsyncioTestCase, mark_asyncio
from ...base import BaseTracerTestCase


_orig_create_task = asyncio.BaseEventLoop.create_task


class TestAsyncio(BaseTracerTestCase):

    def test_coroutine(self):

        async def coroutine2():
            with self.tracer.trace("coroutine2"):
                pass

        async def coroutine():
            with self.tracer.trace("coroutine"):
                await coroutine2()

        asyncio.run(coroutine())
        self.assert_trace_count(1)
        self.assert_span_count(2)
        spans = self.get_spans()
        assert spans[0].trace_id == spans[1].trace_id
        assert spans[1].parent_id == spans[0].span_id

    def test_task(self):
        pass

    def test_cross_executor(self):
        pass
