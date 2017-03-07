from configparser import SafeConfigParser
from config import DATA_CONFIG

config = SafeConfigParser()

def getSetting(section, key):
    config.read(DATA_CONFIG)
    return config.get(section,key)
