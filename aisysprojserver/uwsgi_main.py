from aisysprojserver.app import create_app
from aisysprojserver.config import UwsgiConfig

if __name__ == '__main__':
    application = create_app(UwsgiConfig())
