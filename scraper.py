from datetime import datetime
import json
import os
import re
import requests
from time import sleep

from bs4 import BeautifulSoup
from elasticsearch_dsl import Boolean, connections, Date, DocType, Keyword, Text
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


class VersionDocument(DocType):
    '''
    Update metadata document
    '''
    id = Text(analyzer='snowball', fields={'raw': Keyword()})
    shortversion = Text()
    version = Text()
    date = Date()
    analyzed = Boolean()

    class Index:
        name = 'update-details'

    @classmethod
    def get_indexable(cls):
        return cls.get_model().get_objects()

    @classmethod
    def from_obj(cls, obj):
        return cls(
            id=obj.id,
            shortversion=obj.shortversion,
            version=obj.version,
            date=obj.date,
            analyzed=obj.analyzed,
            )

    def save(self, **kwargs):
        return super(VersionDocument, self).save(**kwargs)


class Scraper(object):

    def __init__(self, ip, username, password, \
        debug=False, isReleaseNotes=False, chrome_driver='chromedriver', binary_location='/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary', \
        download_dir='contentpacks', elastic_ip='localhost'):
        # Set up session details
        self.ip = ip
        self.username = username
        self.password = password

        # Set up driver
        chrome_options = Options()
        if not debug:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.binary_location = binary_location
        self.driver = webdriver.Chrome(executable_path=os.path.abspath(chrome_driver), options=chrome_options)

        # Init details
        self.download_dir = download_dir
        self.elastic_ip = elastic_ip
        self.latest = {'date': None, 'version': None, 'link': None}

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

        timeout = 10
        
        # If the default creds box pops up, handle it.
        while(True):
            timeout -= 1
            try:
                # Handle alert if we expect it to be there
                if(self.username == 'admin' and self.password == 'admin'):
                    alertBox = self.driver.switch_to.alert
                    alertBox.accept()
                return
            except NoAlertPresentException:
                # We expect an alert, but haven't seen one yet
                if timeout < 1:
                    return # Waited long enough
                try:
                    sleep(1) # Firewall is not warning us about default creds . . . yet?
                except UnexpectedAlertPresentException:
                    # Alert happened while we were sleeping, handle it
                    alertBox = self.driver.switch_to.alert
                    alertBox.accept()
                    return


    def find_update_page(self):
        self.driver.get(f'https://{self.ip}')
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
                sleep(1)

        # Wait for updates to load in
        sleep(10)

        # Wait for page to load
        timeout = 500
        try:
            avTablePresent = EC.presence_of_element_located((By.ID, 'ext-gen468-gp-type-anti-virus-bd'))
            WebDriverWait(self.driver, timeout).until(avTablePresent)
        except TimeoutException:
            print('Timed out waiting for updates to load.')

        avTable = self.driver.find_element_by_id('ext-gen468-gp-type-anti-virus-bd')
        avChildren = avTable.find_elements_by_xpath('*')
        self.latest = {'date': None, 'version': None, 'link': None}
        # Iterate all versions
        for child in avChildren:
            source = child.get_attribute('innerHTML')
            # Iterate details of each version
            date = re.search(r'[0-9]{4}\/[0-9]{2}\/[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} PDT', source).group(0) # e.g. 2019/06/14 04:02:07 PDT
            if self.latest['date'] == None or self.latest['date'] < date:
                self.latest['date'] = date
                self.latest['version'] = re.search(r'[0-9]{4}-[0-9]{4}', source).group(0) # e.g. 3009-3519
                self.latest['link'] = re.search(r'https://downloads\.paloaltonetworks\.com/virus/AntiVirusExternal-[0-9]*\.html\?__gda__=[0-9]*_[a-z0-9]*', source).group(0)

    def download_release(self):
        '''
        Download the page source of the latest release notes
        '''
        os.chdir(self.download_dir)
        self.driver.get(self.latest['link'])
        filename = f'Updates_{self.latest["version"]}.html'
        with open(filename, 'w') as f:
            f.write(self.driver.page_source)

    def write_details_to_db(self):
        '''
        Write version and date to elasticsearch
        '''
        connections.create_connection(host=self.elastic_ip)
        version_doc = VersionDocument(meta={'id':self.latest['version']})
        version_doc.shortversion = self.latest['version'].split('-')[0]
        version_doc.version = self.latest['version']
        version_doc.date = self.latest['date']
        version_doc.analyzed = False
        version_doc.save()

    def full_download(self):
        self.login()
        self.find_update_page()
        self.write_details_to_db()
        self.download_release()

if __name__ == '__main__':
    scraper = Scraper(ip=app.config['FIREWALL_IP'], username=app.config['USERNAME'], password=app.config['PASSWORD'], \
        debug=app.config['DEBUG'], chrome_driver=app.config['DRIVER'], binary_location=app.config['BINARY_LOCATION'], \
        download_dir=app.config['DOWNLOAD_DIR'], elastic_ip=app.config['ELASTIC_IP'])
    scraper.full_download()
