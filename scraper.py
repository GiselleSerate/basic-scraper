import os
from time import sleep

from bs4 import BeautifulSoup
from flask import Flask
from guerrillamail import GuerrillaMailSession
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


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
        self.email = email
        self.password = password
        self.package = package
        self.key = self.PACKAGE_KEY[package]
        self.filename_string = 'ReleaseNotesFileName' if isReleaseNotes else 'FileName'

        # Set up driver
        chrome_options = Options()
        chrome_options.add_argument('--headless')
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
        session = GuerrillaMailSession(email_address='phoenix@guerrillamailblock.com')
        # Wait for email to arrive
        while True:
            print('Making request.')
            latest_summary = session.get_email_list()[0]
            if(latest_summary.sender == self.email): # TODO there's a problem if we keep sending OTP emails from me. handle it
                break
            sleep(10)
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
        emailBox = self.driver.find_element_by_id('Email') # TODO maybe check this lol idk
        pwdBox = self.driver.find_element_by_id('Password')
        submit = self.driver.find_element_by_class_name('loginbtn')

        # Fill login form
        emailBox.clear()
        emailBox.send_keys(self.email)
        pwdBox.clear()
        pwdBox.send_keys(self.password)
        submit.click()

        print(self.driver.page_source) # TODO for now; later on verify this is okay and actually logged in

        # Get 2FA code from email
        otp = self.getOTP()

        # Submit the 2FA code
        otpBox = self.driver.find_element_by_id('otp')
        submitOtp = self.driver.find_element_by_xpath('//*[@id="otp-form"]/div[2]/input')
        otpBox.clear()
        otpBox.send_keys(otp)
        submitOtp.click()

        self.driver.get(self.update_url)
        print(self.driver.page_source) # TODO verify that the page is interesting html (currently it's not.)


if __name__ == '__main__':
    scraper = Scraper(email=app.config['EMAIL'], password=app.config['PASSWORD'], company_id=app.config['COMPANY_ID'],\
        package="appthreat", debug=False, isReleaseNotes=False, binary_location=app.config['BINARY_LOCATION'])
    scraper.login()


# self.browser.form['Email'] = self.username
# self.browser.form['Password'] = self.password
# self.last_request = datetime.now()
# self.browser.submit()

# about = driver.find_element_by_xpath('/html/body/ul/li[2]/a')
# linkTo = about.get_attribute('href')

# htmlSrc = driver.get(linkTo)

# print(driver.page_source)

# print(about.get_attribute('href'))
# print(about.get_attribute('title'))
# if about.is_displayed():
#   about.click()
#   print('here')


# search_field = driver.find_element_by_id('site-search')
# search_field.clear()
# search_field.send_keys('Olabode')
# search_field.send_keys(Keys.RETURN)
# assert 'Looking Back at Android Security in 2016' in driver.page_source   driver.close()