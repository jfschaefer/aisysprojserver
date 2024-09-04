import time
from contextlib import contextmanager
from functools import cached_property, wraps
from pathlib import Path
from typing import Optional, Iterable

import psutil
from flask import Blueprint
from opentelemetry import metrics
from opentelemetry.metrics import Meter, Histogram, Counter, Observation, CallbackOptions
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from prometheus_client import start_http_server

from aisysprojserver import __version__
from aisysprojserver.config import Config


class _Instruments:
    _meter: Optional[Meter] = None

    def set_meter(self, meter: Meter):
        if self._meter is not None:
            raise RuntimeError('Meter already set')
        self._meter = meter

    @property
    def meter(self) -> Meter:
        if self._meter is None:
            raise RuntimeError('Meter not set')
        return self._meter

    @cached_property
    def run_creation_duration_histogram(self) -> Histogram:
        return self.meter.create_histogram(
            name='run_creation_duration',
            description='Time it takes to create a run',
            unit='ms',
        )

    @cached_property
    def request_processing_duration(self) -> Histogram:
        return self.meter.create_histogram(
            name='request_processing_duration',
            description='Time it takes to process a request',
            unit='ms',
        )

    @cached_property
    def action_processing_duration_histogram(self) -> Histogram:
        return self.meter.create_histogram(
            name='action_evaluation_duration',
            description='Time it takes to evaluate an action',
            unit='ms',
        )

    @cached_property
    def action_counter(self) -> Counter:
        return self.meter.create_counter(
            name='env_usage',
            description='Number of actions sent to an environment',
            unit='1',
        )


def get_pid() -> int:
    return psutil.Process().pid


_instruments: _Instruments = _Instruments()


@contextmanager
def measure_action_processing(env_class_refstr: str):
    start = time.time()
    try:
        yield
    finally:
        _instruments.action_processing_duration_histogram.record(
            (time.time() - start) * 1000, {'env_class': env_class_refstr, 'pid': get_pid()}
        )


@contextmanager
def measure_run_creation_duration(env_class_refstr: str):
    start = time.time()
    try:
        yield
    finally:
        _instruments.run_creation_duration_histogram.record(
            (time.time() - start) * 1000, {'env_class': env_class_refstr, 'pid': get_pid()}
        )


def report_action(env_id: str, number_of_actions: int = 1):
    _instruments.action_counter.add(number_of_actions, {'env_id': env_id, 'pid': get_pid()})


def _setup_db_size_gauge(config: Config):
    def get_db_size(_options: CallbackOptions) -> Iterable[Observation]:
        if config.DATABASE_URI.startswith('sqlite:///'):
            yield Observation(Path(config.DATABASE_URI[len('sqlite:///'):]).stat().st_size / 1024 / 1024)

    _instruments.meter.create_observable_gauge(
        name='db_size',
        description='Size of the database file (currently only for SQLite)',
        unit='MiB',
        callbacks=[get_db_size]
    )


def _setup_system_metrics():
    def get_cpu_usage(options: CallbackOptions) -> Iterable[Observation]:
        # psutil.cpu_percent(X) is a blocking call (records CPU usage over X seconds)
        yield Observation(psutil.cpu_percent(min(options.timeout_millis * 1000 / 2, 1.0)))

    def get_rel_memory_usage(_options: CallbackOptions) -> Iterable[Observation]:
        yield Observation(psutil.virtual_memory().percent)

    def get_abs_memory_usage(_options: CallbackOptions) -> Iterable[Observation]:
        yield Observation(psutil.virtual_memory().used / 1024 / 1024)

    _instruments.meter.create_observable_gauge(
        name='cpu_usage',
        description='CPU usage',
        unit='%',
        callbacks=[get_cpu_usage]
    )

    _instruments.meter.create_observable_gauge(
        name='rel_memory_usage',
        description='Memory usage',
        unit='%',
        callbacks=[get_rel_memory_usage]
    )

    _instruments.meter.create_observable_gauge(
        name='abs_memory_usage',
        description='Memory usage',
        unit='MiB',
        callbacks=[get_abs_memory_usage]
    )


class MonitoredBlueprint(Blueprint):
    def route(self, rule, **options):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                start = time.time()
                try:
                    return f(*args, **kwargs)
                finally:
                    _instruments.request_processing_duration.record(
                        (time.time() - start) * 1000, {'rule': rule}
                    )

            return Blueprint.route(self, rule, **options)(wrapped)

        return decorator


def setup(config: Config):
    global _instruments

    if config.PROMETHEUS_PORT is not None:
        start_http_server(port=config.PROMETHEUS_PORT, addr='localhost')

    resource = Resource(attributes={
        SERVICE_NAME: 'aisysprojserver',
        SERVICE_VERSION: __version__
    })

    readers = []

    if config.PROMETHEUS_PORT is not None:
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        readers.append(PrometheusMetricReader())
    if config.OTLP_ENDPOINT is not None:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=config.OTLP_ENDPOINT)))

    provider = MeterProvider(
        metric_readers=readers,
        resource=resource,
        views=[View(
            instrument_name='*_duration',
            aggregation=ExplicitBucketHistogramAggregation(
                (0.0, 0.01, 0.1, 0.5, 1.0, 5.0, 20.0, 100.0, 1000.0)  # in milliseconds
            )
        )],
    )
    metrics.set_meter_provider(provider)

    _instruments.set_meter(metrics.get_meter('aisysproj-meter'))

    _setup_db_size_gauge(config)
    _setup_system_metrics()
