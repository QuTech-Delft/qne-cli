import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BACKEND_TYPE = 'NetSquid simulator'


class Settings(BaseSettings):
    """ Global settings

    config_dir: the directory in the user's home where application configuration is stored
    """
    config_dir: Path = Path.home() / ".qne"
