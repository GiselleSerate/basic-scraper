# release_scraper

Scrapes the latest release notes off a Palo Alto Networks firewall. This scraper has been refactored and integrated into [Pandorica](https://github.com/GiselleSerate/pandorica).

This scraper is designed to work in vanilla Chrome. It might also work in other browsers, but no promises (Chrome Canary complains of circular JavaScript or something). 

Download the appropriate Chrome driver and put it in the root of this repository. 

## Example `config.py` file
For a Mac install. Replace the firewall credentials and IP with the applicable ones on your firewall. 
```
class Config(object):
    USERNAME = 'admin'
    PASSWORD = 'admin'
    BINARY_LOCATION = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    DRIVER = 'vanilladriver'
    DOWNLOAD_DIR = '../versiondocs/'
    FIREWALL_IP = '0.0.0.0'
    ELASTIC_IP = 'localhost'
    DEBUG = False

class DebugConfig(Config):
    DEBUG = True
```
