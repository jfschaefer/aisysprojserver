from aisysprojserver.app import create_app
from aisysprojserver.config import GunicornConfig

config = GunicornConfig()
app = create_app(config)
