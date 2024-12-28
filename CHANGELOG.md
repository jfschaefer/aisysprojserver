# Changelog

## 0.1.3 (released on 2024-12-28)
 * bugfix: error when loading env's by group

## 0.1.2 (released on 2024-12-28)
* admin password hashes do not have to be hard-coded anymore
* feature: admins can now get all environment and group identifiers
* feature: admins can delete unused accounts

## 0.1.1 (released on 2024-10-02)
* bugfix telemetry: record pid also for `request_processing_duration`
* support abandoning runs on the server (already part of server protocol since 0.1.0)
* support abandoning old runs in `client.py`
* support `Agent` subclassing along with agent functions in `client.py`


## 0.1.0 (released on 2024-09-18)
* Improvements to web interface
* Switch to pydantic
* Server protocol v1 (the original protocol is still supported)
* Basic testing for Python clients
* use mypy
* fix for telemetry: record pid
