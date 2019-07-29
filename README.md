# firewall_scraper

Scrapes the latest release notes off a Palo Alto Networks firewall.

Written in Python 3.7. For this to work, you'll need a firewall to scrape. 

## Setup
Download [Google Chrome](https://www.google.com/chrome/) and a corresponding [Chrome driver](https://sites.google.com/a/chromium.org/chromedriver/downloads).

Create the file `~/.panrc` that looks like this:
```
FW_IP=10.48.60.12
BINARY_LOCATION=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
DRIVER=${HOME}/_dev/pandorica/vanilladriver
DOWNLOAD_DIR=${HOME}/_dev/versiondocs
LOGGING_LEVEL=INFO
```
* `FW_IP`: IP of your firewall
* `BINARY_LOCATION`: path to your Chrome executable
* `DRIVER`: path to your Chrome driver
* `DOWNLOAD_DIR`: path to the directory where you'd like to download files
* `LOGGING_LEVEL`: defines what log messages to print to console; one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`

Install the `requirements.txt` file, preferably in a virtual environment. From this repository: 
```
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

## Use
Source your virtual environment: `source .env/bin/activate`

Run the script: `python support_scraper.py`

Files will be downloaded to the directory specified in your `.panrc`.