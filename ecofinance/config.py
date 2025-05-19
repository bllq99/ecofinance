import configparser
import os
from django.core.exceptions import ImproperlyConfigured

def get_config():
    """
    Lee la configuración desde config.ini
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
    if not os.path.exists(config_path):
        raise ImproperlyConfigured(
            "El archivo config.ini no existe. Por favor, créalo siguiendo el ejemplo en README.md"
        )
    
    config.read(config_path)
    return config