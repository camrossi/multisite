import requests
import json
import pprint
import logging, sys
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class MSO:
    def __init__(self, mso_url):
        self.mso_url = mso_url
        self.auth_token = None
        self.hed = None
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
                     "password": password
                }
    
        r = requests.post(self.mso_url + "/api/v1/auth/login",json=data, verify=False)
        login_data = json.loads(r.text) 
    
    
        self.logger.debug("Log In to MSO")
        self.auth_token = login_data['token']
        self.hed = {'Authorization': 'Bearer ' + self.auth_token}
        
    
    def createTenant(self,name, displayName = None, desc = "", site_Ids = []):

        if not displayName:
            displayName = name

        if len(site_Ids) > 0:
            self.logger.debug("Create Tenant and map it to %d sites", len(site_Ids))
        else:
            self.logger.debug("Create Tenant, not mapped to any site")            

        data = {
                "displayName": displayName,
                "name": name,
                "description": desc,
                "siteAssociations": []
                }
        if len(site_Ids) > 0:
           for siteId in site_Ids:
               data['siteAssociations'].append({'siteId':siteId,'securityDomains':[]})

        r = requests.post(self.mso_url + "/api/v1/tenants",json=data,headers=self.hed, verify=False)
        self.logger.debug("Log In to MSO %s, reason %s", r.status_code, r.reason)
        if r.reason == "Conflict":
             self.logger.error("Tenant already exist! Please use the modifyTenant method ")

    def getAllTenants(self):
        self.logger.debug("Get all Tenants")
        r = requests.get(self.mso_url + "/api/v1/tenants", headers=self.hed, verify=False)
        tenants = json.loads(r.text)
        self.logger.debug("Found a total of %d Tenants", len(tenants['tenants']))     
        return tenants

    def getTenantByName(self,name):
        
        tenants = self.getAllTenants()
        self.logger.debug("Looking for Tenant name %s", name)
        
        for tenant in tenants['tenants']:
            if tenant['name'] == name:
                self.logger.debug("Found Tenant %s",name)
                return tenant
        self.logger.debug("Site %s not found",name)                
        return None

    def getTenantId(self, name):
        tenant = self.getTenantByName(name)
        self.logger.debug("Tenant ID %s", tenant['id']) 
        return tenant['id']

    def addTenantAssociations(self, name, sites = []):
        if len(sites) > 0:
            tenant = self.getTenantByName(name)
            for site in sites:
                siteId = self.getSiteId(site)
                siteAssociation = {
                                   'siteId':siteId,
                                   'securityDomains':[]
                                  }
                if siteAssociation not in tenant['siteAssociations']:
                     tenant['siteAssociations'].append(siteAssociation)
                else:
                    self.logger.info('Tenant %s to Site %s  association already existing', tenant['name'], site)
                    


        r = requests.put(self.mso_url + "/api/v1/tenants/" + tenant['id'] ,json=tenant, headers=self.hed, verify=False)
        self.logger.debug('Tenant update status %s %s',r.status_code, r.reason)

    def delTenantAssociations(self, name, sites = []):
        if len(sites) > 0:
            tenant = self.getTenantByName(name)
            for site in sites:
                siteId = self.getSiteId(site)
                tenant['siteAssociations'][:] = [d for d in tenant['siteAssociations'] if d.get('siteId') != siteId]

                
        r = requests.put(self.mso_url + "/api/v1/tenants/" + tenant['id'] ,json=tenant, headers=self.hed, verify=False)
        self.logger.debug('Tenant update status %s %s',r.status_code, r.reason)

        


    
    def getAllSites(self):
        self.logger.debug("Get all Sites")
        r = requests.get(self.mso_url + "/api/v1/sites", headers=self.hed, verify=False)
        sites = json.loads(r.text)
        self.logger.debug("Found a total of %d sites", len(sites['sites']))     
        return sites
    
    def getSiteByName(self, name):

        sites = self.getAllSites()
        self.logger.debug("Looking for site name %s", name)
        
        for site in sites['sites']:
            if site['name'] == name:
                self.logger.debug("Found site %s",name)
                return site
        self.logger.debug("Site %s not found",name)                
        return None
        
    
    def getSiteId(self, name):
        site = self.getSiteByName(name)
        self.logger.debug("Site ID %s", site['id']) 
        return site['id'] 
    
    
    
