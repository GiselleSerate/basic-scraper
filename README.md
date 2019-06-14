# basic-scraper

## Example `config.py` file
For a Mac install. Replace the firewall credentials and IP with the applicable ones on your firewall. 
```
class Config(object):
    USERNAME = 'admin'
    PASSWORD = 'admin'
    FIREWALL_IP = '0.0.0.0'
    BINARY_LOCATION = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    DRIVER = 'vanilladriver'
    DEBUG = False

class DebugConfig(Config):
    DEBUG = True
```