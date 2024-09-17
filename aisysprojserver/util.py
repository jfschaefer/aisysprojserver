from typing import Any, TypeVar

from pydantic import ValidationError, BaseModel, ConfigDict
from werkzeug.exceptions import BadRequest

try:
    import orjson  # faster than standard json library

    def json_dump(thing) -> str:
        return orjson.dumps(thing).decode()  # no spaces

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


PYDANTIC_REQUEST_CONFIG = ConfigDict(frozen=True, extra='ignore', populate_by_name=True)


_T = TypeVar('_T', bound=BaseModel)


def parse_request(model: type[_T], request) -> _T:
    try:
        return model.model_validate(request)
    except ValidationError as e:
        err = e.errors()
        assert err
        raise BadRequest(f'Malformed request body in field {err[0]["loc"]}: {err[0]["msg"]!r}')
