from aisysprojserver.app import create_app
from aisysprojserver.config import UwsgiConfig


app = create_app(UwsgiConfig())
