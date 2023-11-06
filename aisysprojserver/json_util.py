from typing import Any

try:
    import orjson

    def json_dump(thing) -> str:
        return orjson.dumps(thing).decode()   # no spaces

    def json_load(string: str) -> Any:
        return orjson.loads(string)

except (ImportError, ModuleNotFoundError):
    # logging.warning(
    #   f'Failed to import orjson - following back to the slower json implementation from the standard library'
    # )
    import json

    def json_dump(thing) -> str:
        return json.dumps(thing, separators=(',', ':'))

    def json_load(string: str) -> Any:
        return json.loads(string)
