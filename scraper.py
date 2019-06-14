from datetime import datetime
import json
import os
import re
import requests
from time import sleep

from bs4 import BeautifulSoup
from flask import Flask
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, NoAlertPresentException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


app = Flask(__name__)
app.config.from_object('config.DebugConfig')


class Scraper(object):

    def __init__(self, ip, username, password, \
        debug=False, isReleaseNotes=False, chrome_driver='chromedriver', binary_location='/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'):
        # Set up session details
        self.ip = ip
        self.username = username
        self.password = password

        # Set up driver
        chrome_options = Options()
        if not debug:
            chrome_options.add_argument('--headless')
        chrome_options.binary_location = binary_location
        self.driver = webdriver.Chrome(executable_path=os.path.abspath(chrome_driver), options=chrome_options)

    def __del__(self):
        self.driver.close()

    def login(self):
        # Load firewall login interface
        self.driver.get(f'https://{self.ip}')

        # Fill login form and submit
        userBox = self.driver.find_element_by_id('user') # TODO maybe check this lol idk
        pwdBox = self.driver.find_element_by_id('passwd')
        userBox.clear()
        userBox.send_keys(self.username)
        pwdBox.clear()
        pwdBox.send_keys(self.password)
        pwdBox.send_keys(Keys.RETURN)
        
        # If the default creds box pops up, handle it.
        try:
            alertBox = self.driver.switch_to.alert
            alertBox.accept()
        except NoAlertPresentException:
            pass # Firewall is not warning us about default creds

    def find_update_page(self):
        # Wait for page to load
        timeout = 500
        try:
            deviceTabPresent = EC.presence_of_element_located((By.ID, 'device'))
            WebDriverWait(self.driver, timeout).until(deviceTabPresent)
        except TimeoutException:
            print('Timed out waiting for post-login page to load.')

        # Go to device tab
        deviceTab = self.driver.find_element_by_id('device')
        deviceTab.click()

        # Go to Dynamic Updates
        dynamicUpdates = self.driver.find_element_by_css_selector('div[ext\\3Atree-node-id="device/dynamic-updates"]')
        dynamicUpdates.click()

        # Get latest updates
        checkNow = self.driver.find_element_by_css_selector('table[itemid="Device/Dynamic Updates-Check Now"]')
        self.driver.execute_script("arguments[0].scrollIntoView(true);", checkNow);

        # Click as soon as in view
        while True:
            try:
                checkNow.click()
                break
            except ElementClickInterceptedException:
                print('NAPTIME')
                sleep(1)

        # Wait for updates to load in
        sleep(600)

        # Here's the progress element
        # <span class="ext-mb-text" id="ext-gen538" style="display: inline;">Checking for new content updates...</span>

        # # Get 2FA code from email
        # otp = self.getOTP()

        # # Submit the 2FA code
        # otpBox = self.driver.find_element_by_id('otp')
        # submitOtp = self.driver.find_element_by_css_selector('#otp-form > div > input')
        # otpBox.click()
        # otpBox.clear()
        # otpBox.send_keys(otp)

        # # Hover first so it lets you submit
        # hover = ActionChains(self.driver).move_to_element(submitOtp)
        # hover.perform()
        # otpBox.submit()

        # # Wait for page to load
        # timeout = 500
        # try:
        #     dynamicHeader = EC.presence_of_element_located((By.ID, 'dynamicUpdates'))
        #     WebDriverWait(self.driver, timeout).until(dynamicHeader)
        # except TimeoutException:
        #     print('Timed out waiting for post-login page to load.')

        # # Get Request Verification Token and updates
        # token = self.driver.find_element_by_name('__RequestVerificationToken')
        # match = re.search(r'"data":({"Data":.*?"Total":\d+,"AggregateResults":null})', self.driver.page_source)
        # if match is None:
        #     raise GetLinkError("You have no access to download files. Probably some hardcoded URL is wrong, or you set wrong 'companyid' in config file.")
        # updates = json.loads(match.group(1))
        # return token, updates['Data']

    # def find_latest_update(self, updates):
    #     updates_of_type = [u for u in updates if u['Key'] == self.key]
    #     updates_sorted = sorted(updates_of_type, key=lambda x: datetime.strptime(x['ReleaseDate'], '%Y-%m-%dT%H:%M:%S'))
    #     latest = updates_sorted[-1]
    #     print(f'Found latest update:  {latest[self.filename_string]}  Released {latest["ReleaseDate"]}')
    #     return latest[self.filename_string], latest['FolderName'], latest['VersionNumber']

    # def click_link(self):
    #     '''
    #     Maybe eventually we'll not hard-code this. 
    #     '''
    #     # Get section header
    #     body = self.driver.find_element_by_xpath('//tbody')
        

    # def download(self, download_dir, url, filename):
    #     '''
    #     Didn't even get here yet tbh
    #     '''
    #     os.chdir(download_dir)
    #     self.browser.retrieve(url, filename)
    #     return filename



if __name__ == '__main__':
    download_dir = app.config['DOWNLOAD_DIR']

    scraper = Scraper(ip=app.config['FIREWALL_IP'], username=app.config['USERNAME'], password=app.config['PASSWORD'], \
        debug=app.config['DEBUG'], chrome_driver=app.config['DRIVER'], binary_location=app.config['BINARY_LOCATION'])

    scraper.login()
    scraper.find_update_page()
    
    # # Determine latest update
    # filename, foldername, latestversion = scraper.find_latest_update(updates)

    # # Get previously downloaded versions from download directory
    # downloaded_versions = []
    # for f in os.listdir(download_dir):
    #     downloaded_versions.append(f)

    # # Check if already downloaded latest and do nothing
    # if filename in downloaded_versions:
    #     print(f'Already downloaded latest version: {filename}')
    #     sys.exit(0)

    # content = scraper.click_link()

    # # Get download URL
    # fileurl = scraper.get_download_link(token, filename, foldername)

    # # Download latest version to download directory
    # print(f'Downloading latest version: {latestversion}')
    # filename = scraper.download(download_dir, fileurl, filename)
    # if filename is not None:
    #     print(f'Finished downloading file: {filename}')
    # else:
    #     print('Unable to download latest content update')
