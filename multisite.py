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
                "password": password
               }
        # Login into MSO and get Authentication toke.  
        self.logger.debug("Log In to MSO")
        r = requests.post(self.mso_url + "/api/v1/auth/login",json=data, verify=False)
        login_data = json.loads(r.text) 
    
        self.auth_token = login_data['token']
        self.hed = {'Authorization': 'Bearer ' + self.auth_token}
    
    def createSchema(self, name, templateName, tenant):

        tenantId = self.getTenantId(name = tenant)

        data = {
                   "displayName": name,
                   "templates": [
                                   {
                                       "name": templateName,
                                       "displayName": templateName,
                                       "tenantId": tenantId
                                   }
                               ]
                }


        r = requests.post(self.mso_url + "/api/v1/schemas",json=data,headers=self.hed, verify=False)
        self.logger.debug("Schema creation status %s, reson %s", r.status_code, r.reason)
        if r.reason == "Conflict":
             self.logger.info("Schema already exist! ")
        
        self.loadSchema(name)
       

    def loadSchema(self, name):
        self.schemas[name] = Schema(name, False, self.logger, self.mso_url, self.hed)
            
    def createTenant(self,name, displayName = None, desc = "", sites = []):
        
        if not displayName:
            displayName = name
        # Tenant Data 
        data = {
                "displayName": displayName,
                "name": name,
                "description": desc,
                "siteAssociations": []
                }
        
        #If I am mapping a Tenants to sites when I create it, then I add the site ID to the tenant siteAssociation.
        if len(sites) > 0:
            self.logger.debug("Create Tenant and map it to %d sites", len(sites))
            for site in sites:
               data['siteAssociations'].append({'siteId':self.getSiteId(site),'securityDomains':[]})
               print(data['siteAssociations'])
        
        else:
            self.logger.debug("Create Tenant, not mapped to any site")   

        r = requests.post(self.mso_url + "/api/v1/tenants",json=data,headers=self.hed, verify=False)
        self.logger.debug("Tenant creation status %s, reson %s", r.status_code, r.reason)
        if r.reason == "Conflict":
             self.logger.info("Tenant already exist! ")

    def getAllTenants(self):
        self.logger.debug("Get all Tenants")
        r = requests.get(self.mso_url + "/api/v1/tenants", headers=self.hed, verify=False)
        tenants = json.loads(r.text)
        self.logger.debug("Found a total of %d Tenants", len(tenants['tenants']))     
        return tenants


    def getTenantByName(self,name):
        
        #API does not support filtering so I need anyway to pull all the tenants and then find.
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

    def delTenantAssociations(self, name, sites = [], deleteAll = False):
        if len(sites) > 0 and not deleteAll :
            tenant = self.getTenantByName(name)
            for site in sites:
                siteId = self.getSiteId(site)
                tenant['siteAssociations'][:] = [d for d in tenant['siteAssociations'] if d.get('siteId') != siteId]
        elif deleteAll:
             tenant = self.getTenantByName(name)
             tenant['siteAssociations'] = []
        else:
             self.logger.error('You need to specify either a list of sites or deleteAll needs to be set to True')
             exit()
                
        r = requests.put(self.mso_url + "/api/v1/tenants/" + tenant['id'] ,json=tenant, headers=self.hed, verify=False)
        self.logger.debug('Tenant update status %s %s',r.status_code, r.reason)

    def createSite(self, name, url, username, password, siteID):
        data = {
                  "name": name,
                  "urls": url,
                  "username": username,
                  "password": password,
                  "apicSiteId" : siteID
               }

        r = requests.post(self.mso_url + "/api/v1/sites",json=data,headers=self.hed, verify=False)
        self.logger.debug("Site creation status %s, reson %s", r.status_code, r.reason)
        if r.reason == "Conflict":
             self.logger.info("Tenant already exist! ")

    def getAllSites(self):
        self.logger.debug("Get all Sites")
        r = requests.get(self.mso_url + "/api/v1/sites", headers=self.hed, verify=False)
        sites = json.loads(r.text)
        self.logger.debug("Found a total of %d sites", len(sites['sites']))   
        if len(sites['sites'])==0:
            self.logger.error("No sites found, please create a site first!\n Execution Aborted")
            exit()

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

class Schema:
    def __init__(self, name, create, logger, mso_url,  hed):
        self.logger = logger
        self.mso_url = mso_url
        self.hed = hed 
        if create:
            self.schema = self.createSchema(name, tenant, templateName)
                                             
        else:
            self.schema = self.getSchemaByName(name)

        self.schemId =  self.schema['id']



    
    def getTempListID(self, templates, name):
        index =  next((index for (index, d) in enumerate(templates) if d["name"] == name), None)
        if index != None :
            return index
        else:
            self.logger.error("Template %s not found", name)
            exit()

    def getAllSchema(self):
        self.logger.debug("Get all Schemas")
        r = requests.get(self.mso_url + "/api/v1/schemas", headers=self.hed, verify=False)
        schemas = json.loads(r.text)
        return schemas

    def getSchemaByName(self,name):
        self.logger.debug("Looking for Schema name %s", name)
        schemas = self.getAllSchema()
        for schema in schemas['schemas']:
            if schema['displayName'] == name:
                self.logger.debug("Found Schema %s",name)                
                return schema

    def getSchemaId(self, name):
        schema = self.getSchemaByName(name)
        self.logger.debug("Schema ID %s", schema['id']) 
        return schema['id'] 
    
    def addBD(self,bd_template_name, name,vrf, vrf_template_name = None, intersiteBumTrafficAllowm = True, 
        l2Stretch = True, l2UnknownUnicast = 'proxy',optimizeWanBandwidth = True, 
        subnets = []):
        # Here we need to pass a of parameters just keep in mind that the tempale for the VRF cab be different for the template
        #of the BD so I give the ability to specify this. 

        if not vrf_template_name:
            vrf_template_name = bd_template_name

        bd = {
                    "bdRef": "/schemas/" + self.schemId + "/templates/" + bd_template_name + "/bds/"+ name,
                    'vrfRef':"/schemas/" + self.schemId + "/templates/" + vrf_template_name + '/vrfs/' + vrf,
                    "displayName": name,
                    "intersiteBumTrafficAllow": intersiteBumTrafficAllowm,
                    "l2Stretch": l2Stretch,
                    "l2UnknownUnicast": l2UnknownUnicast,
                    "name": name,
                    "optimizeWanBandwidth": optimizeWanBandwidth,
                    "subnets": []

                     } 
        if l2Stretch:
            bd['subnets'] = subnets
        else:
            pass


        index =  self.getTempListID(self.schema['templates'], bd_template_name)
           
        if bd not in self.schema['templates'][index]['bds']:
           self.schema['templates'][index]['bds'].append(bd)
           self.logger.debug("Adding BD %s", name)
        else:
           self.logger.info("BD %s already exists, not addind", name)
    
    def delBD(self, name, template_name):
        self.logger.debug("Deleting BD %s", name)
        index =  self.getTempListID(self.schema['templates'], template_name)
        self.schema['templates'][index]['bds'][:] = [d for d in  self.schema['templates'][index]['bds'] if d.get('name') != name]

                    
    def commit(self):
        r = requests.put(self.mso_url + "/api/v1/schemas/" + self.schema['id'] ,json=self.schema, headers=self.hed, verify=False)
        self.logger.debug('Schema update status %s %s',r.status_code, r.reason)



       
