FROM tiangolo/uwsgi-nginx-flask:latest

ENV STATIC_PATH /app/aisysprojserver/static
COPY ./requirements.txt /app
COPY ./optional-requirements.txt /app
RUN pip install -r ./requirements.txt
RUN pip install -r ./optional-requirements.txt
COPY ./uwsgi.ini /app
COPY ./aisysprojserver /app/aisysprojserver
VOLUME /app/persistent

