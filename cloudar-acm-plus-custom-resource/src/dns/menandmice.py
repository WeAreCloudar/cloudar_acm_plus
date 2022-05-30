import boto3
import logging
import time
import requests
from helper import get_resource_property,strip_domain

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MenAndMice:

    def __init__(self):
        self.client = None
        self.credential_store = 'ssm' #For now only ssm is used to retrieve credentials
        self.credentials = None
        self.server = None 
        self.records = []
        self.mmsession = requests.Session()
        logger.info(self.__class__.__name__ + " initialized")
        
        
    def get_credentials(self):
        handle_credentials = getattr(self, 'get_credentials_from_' + self.credential_store, None)
        if callable(handle_credentials):
            self.handle_credentials()
        
    def get_credentials_from_ssm(self):
        password = None
        username = None
        apiurl = None
        client = boto3.client('ssm')
        response = client.get_parameters_by_path(
            Path=self.credential_store_location,
            Recursive = False,
            WithDecryption=True
        )
        for parameter in response['Parameters']:
            if parameter['Name'] == 'username':
                username = parameter['Value']
            elif parameter['Name'] == 'password':
                password = parameter['Value']
            elif parameter['Name'] == 'apiurl':
                apiurl = parameter['Value']
            
        self.credentials=(username, password)
        self.apiurl = apiurl
        

    def handle_event(self,event):
        self.credential_store_location = get_resource_property(
            event, 'DnsApiCredentialLocation')
        if not self.credential_store_location:
            raise AttributeError(self.__class__.__name__ +
                                 " Requires DnsApiCredentialLocation Parameter")
        self.hosted_zone_name = get_resource_property(event, 'HostedZoneName')
        if not self.hosted_zone_name:
            raise AttributeError(self.__class__.__name__ +
                                 " Requires HostedZoneName Parameter")
                                 
        self.get_credentials()


    def dns_record_exists(self,record_name,record_value):
        logger.info(
            "Checking if record already exists: Record Name = %s, Record Value = %s.",
            record_name, record_value)

        host_name = strip_domain(record_name, self.hosted_zone_name)

        zone_params = {'filter': 'name=' + self.hosted_zone_name + '.&type=Master'}
        response = self.mmsession.get(
            self.apiurl + '/DNSZones/', params=zone_params, headers=self.headers, auth=self.credentials)
        
        record_params = {'filter': 'type=CNAME&name='+ host_name }
        if response.ok:
            for zone in response.json()['result']['dnsZones']:
                resp = self.mmsession.get(self.apiurl + "/" + zone['ref'] + '/DNSRecords', params=record_params, auth=self.credentials, headers=self.headers)
            if resp.ok:
                for rec in resp.json()['result']['dnsRecords']:
                    self.records.append(rec)
        if self.records and len(self.records) > 0:
            logger.info("Record exists")
            return True
        logger.info("Record does not exist")
        return False

    def modify_dns_record(self, action, record_name, record_value): 
        record_exists = self.dns_record_exists(record_name, record_value)
        if not record_exists or action == "DELETE":
            if action == "DELETE":
                for record in self.records:
                    response = self.mmsession.delete(self.apiurl + "/" + record['ref'], headers=self.headers, auth=self.credentials)
                    if response.ok:
                        logger.info(record['name'] + ' (' + record['ref'] + ') Deleted')
                    else:
                        logger.warn("Could not delete " + record['name'] + ' (' + record['ref'] + ')')
            else:
                # Create new record
                pass
        else:
            logger.info("Record exists, skipping create.")