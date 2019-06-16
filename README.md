# basic-scraper

This scraper is designed to work in vanilla Chrome. It might also work in other browsers, but no promises (Chrome Canary complains of circular JavaScript or something). 

Download the appropriate Chrome driver and put it in the root of this repository. 

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
