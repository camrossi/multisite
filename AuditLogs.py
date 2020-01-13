from pprint import pprint
import requests
import json
import logging, sys
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class MSO:
    def __init__(self, mso_url):
        self.mso_url = mso_url
        self.auth_token = None
        self.hed = None
        self.schemas = {}
        # create logger
        self.logger = logging.getLogger(__name__)
        
        
        # create console handler and set level to debug
        self.ch = logging.StreamHandler()
        self.ch.setLevel(logging.DEBUG)
        
        # create formatter
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # add formatter to ch
        self.ch.setFormatter(self.formatter)
        
        # add ch to logger
        self.logger.addHandler(self.ch)
        
        #Disable URL Lib Warnings
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


    def login(self, username, password):
        data = {
                "username": username,
                "password": password,
               }
        # Login into MSO and get Authentication toke.  
        self.logger.debug("Log In to MSO")
        r = requests.post(self.mso_url + "/api/v1/auth/login",json=data, verify=False)
        login_data = json.loads(r.text) 
        self.auth_token = login_data['token']
        self.hed = {'Authorization': 'Bearer ' + self.auth_token}
    

    def getAudit(self):
        limit = str(100)
        offset = str(0)
        audit = []
        sort='-timestamp'
        while(offset):
            r = requests.get(self.mso_url + "/api/v1/audit-records?limit="+limit+"&offset="+offset+"&sort="+sort, headers=self.hed, verify=False)
            limit = r.headers['X-Page-Limit']
            if 'X-Page-Next-Offset' in r.headers:
                offset = r.headers['X-Page-Next-Offset']                
            else:
                offset = False
                
            audit= audit + (json.loads(r.text)['auditRecords'])
        return audit

mso = MSO("https://10.67.185.100:8083")
mso.login("admin","123Cisco123!")
audit = mso.getAudit()
pprint(audit)
print(len(audit))

