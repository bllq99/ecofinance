import configparser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def get_config():
    config = configparser.ConfigParser()
    config.read(BASE_DIR / 'config.ini')
    return config