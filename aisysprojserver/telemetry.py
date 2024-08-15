import time
from contextlib import contextmanager
from functools import cached_property, wraps
from pathlib import Path
from typing import Optional, Iterable

from flask import Blueprint
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import Meter, Histogram, Counter, Observation, CallbackOptions
from opentelemetry.sdk.metrics import MeterProvider
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


_instruments: _Instruments = _Instruments()


@contextmanager
def measure_action_processing(env_class_refstr: str):
    start = time.time()
    try:
        yield
    finally:
        _instruments.action_processing_duration_histogram.record(
            (time.time() - start) * 1000, {'env_class': env_class_refstr}
        )


@contextmanager
def measure_run_creation_duration(env_class_refstr: str):
    start = time.time()
    try:
        yield
    finally:
        _instruments.run_creation_duration_histogram.record(
            (time.time() - start) * 1000, {'env_class': env_class_refstr}
        )


def report_action(env_id: str, number_of_actions: int = 1):
    _instruments.action_counter.add(number_of_actions, {'env_id': env_id})


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

    provider = MeterProvider(
        metric_readers=[
            PrometheusMetricReader()
        ],
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
