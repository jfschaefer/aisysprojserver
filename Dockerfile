FROM tiangolo/uwsgi-nginx-flask:latest

ENV STATIC_PATH=/app/aisysprojserver/static
WORKDIR /app

# Prometheus (can we somehow get newest release?)
RUN wget https://github.com/prometheus/prometheus/releases/download/v2.54.0/prometheus-2.54.0.linux-amd64.tar.gz && tar xvfz prometheus-*.tar.gz && rm prometheus-*.tar.gz
COPY ./prometheus.yml /app
RUN echo "nohup /app/prometheus-*/prometheus --config.file=/app/prometheus.yml --storage.tsdb.path=/app/persistent/prometheus --storage.tsdb.wal-compression --storage.tsdb.retention.time=15d&" >> /app/prestart.sh   # prestart will be called (indirectly) by

# open telemetry collector
RUN wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.107.0/otelcol-contrib_0.107.0_linux_amd64.deb && dpkg -i otelcol-contrib_0.107.0_linux_amd64.deb && rm otelcol-contrib_0.107.0_linux_amd64.deb
COPY ./otelcol-config.yaml /app
RUN echo "nohup otelcol-contrib --config=otelcol-config.yaml &" >> /app/prestart.sh

COPY ./requirements.txt /app
COPY ./optional-requirements.txt /app
RUN pip install -r ./requirements.txt
RUN pip install -r ./optional-requirements.txt
COPY ./uwsgi.ini /app
COPY ./aisysprojserver /app/aisysprojserver
VOLUME /app/persistent
