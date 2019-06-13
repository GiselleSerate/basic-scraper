from datetime import datetime
import json
import os
import re
import requests
from time import sleep

from bs4 import BeautifulSoup
from flask import Flask
from guerrillamail import GuerrillaMailSession
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


app = Flask(__name__)
app.config.from_object('config.Config')


class Scraper(object):
    PACKAGE_KEY = {
        "appthreat":  "CONTENTS",
        "app":        "APPS",
        "antivirus":  "VIRUS",
        "wildfire":   "WILDFIRE_OLDER",
        "wildfire2":  "WILDFIRE_NEWEST",
        "wf500":      "WF-500 CONTENT",
        "traps":      "TRAPS3.4",
        "clientless": "GPCONTENTS",
    }
    LOGIN_URL = "https://identity.paloaltonetworks.com/idp/startSSO.ping?PartnerSpId=supportCSP&TargetResource=https://support.paloaltonetworks.com/Updates/DynamicUpdates/{companyid}"
    UPDATE_URL = "https://support.paloaltonetworks.com/Updates/DynamicUpdates/{companyid}"
    GET_LINK_URL = "https://support.paloaltonetworks.com/Updates/GetDownloadUrl"

    def __init__(self, email, password, company_id, package="appthreat", \
        debug=False, isReleaseNotes=False, binary_location='/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'):
        # Set up session details
        if package is None:
            package = "appthreat"
        elif package not in self.PACKAGE_KEY:
            raise UnknownPackage("Unknown package type: %s" % package)
        self.fake_email = app.config['FAKE_EMAIL']
        self.email = email
        self.password = password
        self.package = package
        self.key = self.PACKAGE_KEY[package]
        self.filename_string = 'ReleaseNotesFileName' if isReleaseNotes else 'FileName'

        # Set up driver
        chrome_options = Options()
        # chrome_options.add_argument('--headless') # TODO for debugging purposes
        chrome_options.binary_location = binary_location
        self.driver = webdriver.Chrome(executable_path=os.path.abspath('chromedriver'), options=chrome_options)

        # Set up links
        company_id = app.config['COMPANY_ID']
        if company_id == '':
            logging.error('No \'companyid\' set in config file. This will probably result in some error.')
        url_options = {'companyid': company_id}
        self.login_url = self.LOGIN_URL.format(**url_options)
        self.update_url = self.UPDATE_URL.format(**url_options)
        self.get_link_url = self.GET_LINK_URL.format(**url_options)

    def __del__(self):
        self.driver.close()

    def getOTP(self):
        session = GuerrillaMailSession(email_address=self.fake_email)
        # Wait for email to arrive
        while True:
            print('Making request.')
            try:
                latest_summary = session.get_email_list()[0]
                if(latest_summary.sender == self.email): # TODO there's a problem if we keep sending OTP emails from me. handle it
                    break
            except IndexError:
                # Not enough mail, sleep anyway
                pass
            sleep(5)
        print('You\'ve got mail!')
        # Read the email with the OTP
        email = session.get_email(latest_summary.guid)

        # Parse out OTP code
        mailsoup = BeautifulSoup(email.body, 'html5lib')
        try:
            header = mailsoup.find('h1')
            otpElement = header.find_next_sibling('p').find_next_sibling('p')
            otpCode = otpElement.string.strip() # Remove whitespace
            print(f'Your OTP code is {otpCode}')
            return otpCode
        except Exception as e:
            print(e)
            print('Didn\'t get OTP code') # TODO handle errors better. 

    def login(self):
        # Load and identify login form
        self.driver.get(self.login_url)
        sleep(10)
        print(self.driver.page_source)
        emailBox = self.driver.find_element_by_id('Email') # TODO maybe check this lol idk
        pwdBox = self.driver.find_element_by_id('Password')
        submit = self.driver.find_element_by_class_name('loginbtn')

        # Fill login form
        emailBox.clear()
        emailBox.send_keys(self.email)
        pwdBox.clear()
        pwdBox.send_keys(self.password)
        submit.click()

        # Get 2FA code from email
        otp = self.getOTP()

        # Submit the 2FA code
        otpBox = self.driver.find_element_by_id('otp')
        submitOtp = self.driver.find_element_by_css_selector('#otp-form > div > input')
        otpBox.click()
        otpBox.clear()
        otpBox.send_keys(otp)

        # Hover first so it lets you submit
        hover = ActionChains(self.driver).move_to_element(submitOtp)
        hover.perform()
        otpBox.submit()

        # Wait for page to load
        timeout = 500
        try:
            dynamicHeader = EC.presence_of_element_located((By.ID, 'dynamicUpdates'))
            WebDriverWait(self.driver, timeout).until(dynamicHeader)
        except TimeoutException:
            print('Timed out waiting for post-login page to load.')

        # Get Request Verification Token and updates
        token = self.driver.find_element_by_name('__RequestVerificationToken')
        match = re.search(r'"data":({"Data":.*?"Total":\d+,"AggregateResults":null})', self.driver.page_source)
        if match is None:
            raise GetLinkError("You have no access to download files. Probably some hardcoded URL is wrong, or you set wrong 'companyid' in config file.")
        updates = json.loads(match.group(1))
        return token, updates['Data']

    def find_latest_update(self, updates):
        updates_of_type = [u for u in updates if u['Key'] == self.key]
        updates_sorted = sorted(updates_of_type, key=lambda x: datetime.strptime(x['ReleaseDate'], '%Y-%m-%dT%H:%M:%S'))
        latest = updates_sorted[-1]
        print(f'Found latest update:  {latest[self.filename_string]}  Released {latest["ReleaseDate"]}')
        return latest[self.filename_string], latest['FolderName'], latest['VersionNumber']

    def click_link(self):
        '''
        Maybe eventually we'll not hard-code this. 
        '''
        # Get section header
        body = self.driver.find_element_by_xpath('//tbody')
        

    def get_download_link(self, token, filename, foldername):
        '''
        Broken. fml.
        '''
        headers = {'Content-Type': 'application/json; charset=UTF-8',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'X-Requested-With': 'XMLHttpRequest',
                   }
        payload = {'__RequestVerificationToken': token,
                   'FileName': filename,
                   'FolderName': foldername,
                   }
        response = requests.post(self.get_link_url, data=payload, headers=headers).text
        print('Response text:')
        print(response)
        responseJson = json.loads(response)
        
        if 'Success' not in responseJson or not responseJson['Success']:
            raise GetLinkError(f'Failure getting download link: {responseJson}')
        return responseJson['DownloadUrl']

    def download(self, download_dir, url, filename):
        '''
        Didn't even get here yet tbh
        '''
        os.chdir(download_dir)
        self.browser.retrieve(url, filename)
        return filename



if __name__ == '__main__':
    download_dir = app.config['DOWNLOAD_DIR']

    scraper = Scraper(email=app.config['EMAIL'], password=app.config['PASSWORD'], company_id=app.config['COMPANY_ID'],\
        package="appthreat", debug=False, isReleaseNotes=False, binary_location=app.config['BINARY_LOCATION'])

    token, updates = scraper.login()
    
    # Determine latest update
    filename, foldername, latestversion = scraper.find_latest_update(updates)

    # Get previously downloaded versions from download directory
    downloaded_versions = []
    for f in os.listdir(download_dir):
        downloaded_versions.append(f)

    # Check if already downloaded latest and do nothing
    if filename in downloaded_versions:
        print(f'Already downloaded latest version: {filename}')
        sys.exit(0)

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
