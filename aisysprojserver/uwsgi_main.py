from aisysprojserver.app import create_app
from aisysprojserver.config import UwsgiConfig

application = create_app(UwsgiConfig())
