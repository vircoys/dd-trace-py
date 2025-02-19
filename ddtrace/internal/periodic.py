# -*- encoding: utf-8 -*-
import sys
import threading
import time
import typing

import attr

from ddtrace.internal import nogevent
from ddtrace.internal import service

from . import forksafe


class PeriodicThread(threading.Thread):
    """Periodic thread.

    This class can be used to instantiate a worker thread that will run its `run_periodic` function every `interval`
    seconds.

    """

    _ddtrace_profiling_ignore = True

    def __init__(
        self,
        interval,  # type: float
        target,  # type: typing.Callable[[], typing.Any]
        name=None,  # type: typing.Optional[str]
        on_shutdown=None,  # type: typing.Optional[typing.Callable[[], typing.Any]]
    ):
        # type: (...) -> None
        """Create a periodic thread.

        :param interval: The interval in seconds to wait between execution of the periodic function.
        :param target: The periodic function to execute every interval.
        :param name: The name of the thread.
        :param on_shutdown: The function to call when the thread shuts down.
        """
        super(PeriodicThread, self).__init__(name=name)
        self._target = target
        self._on_shutdown = on_shutdown
        self.interval = interval
        self.quit = forksafe.Event()
        self.daemon = True

    def stop(self):
        """Stop the thread."""
        # NOTE: make sure the thread is alive before using self.quit:
        # 1. self.quit is Lock-based
        # 2. if we're a child trying to stop a Thread,
        #    the Lock might have been locked in a parent process while forking so that'd block forever
        if self.is_alive():
            self.quit.set()

    def _is_proper_class(self):
        # DEV: Some frameworks, like e.g. gevent, seem to resuscitate some
        # of the threads that were running prior to the fork of the worker
        # processes. These threads are normally created via the native API
        # and are exposed to the child process as _DummyThreads. We check
        # whether the current thread is no longer an instance of the
        # original thread class to prevent it from running in the child
        # process while the state copied over from the parent is being
        # cleaned up. The restarting of the thread is responsibility to the
        # registered forksafe hooks.
        return isinstance(threading.current_thread(), self.__class__)

    def run(self):
        """Run the target function periodically."""
        while not self.quit.wait(self.interval):
            if not self._is_proper_class():
                break
            self._target()
        if self._on_shutdown is not None:
            self._on_shutdown()


class AwakeablePeriodicThread(PeriodicThread):
    """Periodic thread that can be awakened on demand.

    This class can be used to instantiate a worker thread that will run its
    `run_periodic` function every `interval` seconds, or upon request.
    """

    def __init__(
        self,
        interval,  # type: float
        target,  # type: typing.Callable[[], typing.Any]
        name=None,  # type: typing.Optional[str]
        on_shutdown=None,  # type: typing.Optional[typing.Callable[[], typing.Any]]
    ):
        # type: (...) -> None
        """Create a periodic thread that can be awakened on demand."""
        super(AwakeablePeriodicThread, self).__init__(interval, target, name, on_shutdown)
        self.request = forksafe.Event()
        self.served = forksafe.Event()
        self.awake_lock = forksafe.Lock()

    def stop(self):
        """Stop the thread."""
        super(AwakeablePeriodicThread, self).stop()

        if self.is_alive():
            self.awake()

    def awake(self):
        """Awake the thread."""
        with self.awake_lock:
            self.served.clear()
            self.request.set()
            self.served.wait()

    def run(self):
        """Run the target function periodically or on demand."""
        while not self.quit.is_set():
            if not self._is_proper_class():
                break

            self._target()

            if self.request.wait(self.interval):
                self.request.clear()
                self.served.set()

        if self._on_shutdown is not None:
            self._on_shutdown()


class _GeventPeriodicThread(PeriodicThread):
    """Periodic thread.

    This class can be used to instantiate a worker thread that will run its `run_periodic` function every `interval`
    seconds.

    """

    # That's the value Python 2 uses in its `threading` module
    SLEEP_INTERVAL = 0.005

    def __init__(self, interval, target, name=None, on_shutdown=None):
        """Create a periodic thread.

        :param interval: The interval in seconds to wait between execution of the periodic function.
        :param target: The periodic function to execute every interval.
        :param name: The name of the thread.
        :param on_shutdown: The function to call when the thread shuts down.
        """
        super(_GeventPeriodicThread, self).__init__(interval, target, name, on_shutdown)
        self._tident = None
        self._periodic_started = False
        self._periodic_stopped = False

    def _reset_internal_locks(self, is_alive=False):
        # Called by Python via `threading._after_fork`
        self._periodic_stopped = True

    @property
    def ident(self):
        return self._tident

    def start(self):
        """Start the thread."""
        self.quit = False
        if self._tident is not None:
            raise RuntimeError("threads can only be started once")
        self._tident = nogevent.start_new_thread(self.run, tuple())
        if nogevent.threading_get_native_id:
            self._native_id = nogevent.threading_get_native_id()

        # Wait for the thread to be started to avoid race conditions
        while not self._periodic_started:
            time.sleep(self.SLEEP_INTERVAL)

    def is_alive(self):
        return not self._periodic_stopped and self._periodic_started

    def join(self, timeout=None):
        # FIXME: handle the timeout argument
        while self.is_alive():
            time.sleep(self.SLEEP_INTERVAL)

    def stop(self):
        """Stop the thread."""
        self.quit = True

    def run(self):
        """Run the target function periodically."""
        # Do not use the threading._active_limbo_lock here because it's a gevent lock
        threading._active[self._tident] = self

        self._periodic_started = True

        try:
            while self.quit is False:
                self._target()
                slept = 0
                while self.quit is False and slept < self.interval:
                    nogevent.sleep(self.SLEEP_INTERVAL)
                    slept += self.SLEEP_INTERVAL
            if self._on_shutdown is not None:
                self._on_shutdown()
        except Exception:
            # Exceptions might happen during interpreter shutdown.
            # We're mimicking what `threading.Thread` does in daemon mode, we ignore them.
            # See `threading.Thread._bootstrap` for details.
            if sys is not None:
                raise
        finally:
            try:
                self._periodic_stopped = True
                del threading._active[self._tident]
            except Exception:
                # Exceptions might happen during interpreter shutdown.
                # We're mimicking what `threading.Thread` does in daemon mode, we ignore them.
                # See `threading.Thread._bootstrap` for details.
                if sys is not None:
                    raise


class _GeventAwakeablePeriodicThread(_GeventPeriodicThread):
    """Periodic awakeable thread."""

    def __init__(self, interval, target, name=None, on_shutdown=None):
        super(_GeventAwakeablePeriodicThread, self).__init__(interval, target, name, on_shutdown)
        self.request = False
        self.served = False
        self.awake_lock = nogevent.DoubleLock()

    def stop(self):
        """Stop the thread."""
        super(_GeventAwakeablePeriodicThread, self).stop()
        self.request = True

    def awake(self):
        with self.awake_lock:
            self.served = False
            self.request = True
            while not self.served:
                nogevent.sleep(self.SLEEP_INTERVAL)

    def run(self):
        """Run the target function periodically."""
        # Do not use the threading._active_limbo_lock here because it's a gevent lock
        threading._active[self._tident] = self

        self._periodic_started = True

        try:
            while not self.quit:
                self._target()

                slept = 0
                while self.request is False and slept < self.interval:
                    nogevent.sleep(self.SLEEP_INTERVAL)
                    slept += self.SLEEP_INTERVAL

                if self.request:
                    self.request = False
                    self.served = True

            if self._on_shutdown is not None:
                self._on_shutdown()
        except Exception:
            # Exceptions might happen during interpreter shutdown.
            # We're mimicking what `threading.Thread` does in daemon mode, we ignore them.
            # See `threading.Thread._bootstrap` for details.
            if sys is not None:
                raise
        finally:
            try:
                self._periodic_stopped = True
                del threading._active[self._tident]
            except Exception:
                # Exceptions might happen during interpreter shutdown.
                # We're mimicking what `threading.Thread` does in daemon mode, we ignore them.
                # See `threading.Thread._bootstrap` for details.
                if sys is not None:
                    raise


def PeriodicRealThreadClass():
    # type: () -> typing.Type[PeriodicThread]
    """Return a PeriodicThread class based on the underlying thread implementation (native, gevent, etc).

    The returned class works exactly like ``PeriodicThread``, except that it runs on a *real* OS thread. Be aware that
    this might be tricky in e.g. the gevent case, where ``Lock`` object must not be shared with the ``MainThread``
    (otherwise it'd dead lock).

    """
    if nogevent.is_module_patched("threading"):
        return _GeventPeriodicThread
    return PeriodicThread


def AwakeablePeriodicRealThreadClass():
    # type: () -> typing.Type[PeriodicThread]
    return _GeventAwakeablePeriodicThread if nogevent.is_module_patched("threading") else AwakeablePeriodicThread


@attr.s(eq=False)
class PeriodicService(service.Service):
    """A service that runs periodically."""

    _interval = attr.ib(type=float)
    _worker = attr.ib(default=None, init=False, repr=False)

    _real_thread = False
    "Class variable to override if the service should run in a real OS thread."

    __thread_class__ = (PeriodicRealThreadClass, PeriodicThread)

    @property
    def interval(self):
        # type: (...) -> float
        return self._interval

    @interval.setter
    def interval(
        self, value  # type: float
    ):
        # type: (...) -> None
        self._interval = value
        # Update the interval of the PeriodicThread based on ours
        if self._worker:
            self._worker.interval = value

    def _start_service(
        self,
        *args,  # type: typing.Any
        **kwargs  # type: typing.Any
    ):
        # type: (...) -> None
        """Start the periodic service."""
        real_class, python_class = self.__thread_class__
        periodic_thread_class = real_class() if self._real_thread else python_class
        self._worker = periodic_thread_class(
            self.interval,
            target=self.periodic,
            name="%s:%s" % (self.__class__.__module__, self.__class__.__name__),
            on_shutdown=self.on_shutdown,
        )
        self._worker.start()

    def _stop_service(
        self,
        *args,  # type: typing.Any
        **kwargs  # type: typing.Any
    ):
        # type: (...) -> None
        """Stop the periodic collector."""
        self._worker.stop()
        super(PeriodicService, self)._stop_service(*args, **kwargs)

    def join(
        self, timeout=None  # type: typing.Optional[float]
    ):
        # type: (...) -> None
        if self._worker:
            self._worker.join(timeout)

    @staticmethod
    def on_shutdown():
        pass

    def periodic(self):
        # type: (...) -> None
        pass


class AwakeablePeriodicService(PeriodicService):
    """A service that runs periodically but that can also be awakened on demand."""

    __thread_class__ = (AwakeablePeriodicRealThreadClass, AwakeablePeriodicThread)

    def awake(self):
        # type: (...) -> None
        self._worker.awake()
