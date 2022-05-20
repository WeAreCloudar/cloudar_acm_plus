import boto3
import logging
import time
import requests
from helper import get_resource_property

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MenAndMice:

    def __init__(self):
        self.client = None
        self.credential_store = 'ssm' #For now only ssm is used to retrieve credentials
        self.credentials = None
        self.headers = {'content-type': 'application/json'}
        logger.info(self.__class__.__name__ + " initialized")
        
    def get_credentials(self):
        handle_credentials = getattr(self, 'get_credentials_from_' + self.credential_store, None)
        if callable(handle_credentials):
            self.handle_credentials()
        
    def get_credentials_from_ssm(self):
        password = None
        username = None
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
            
        self.credentials=(username, password)
        
        

    def handle_event(self,event):
        self.credential_store_location = get_resource_property(
            event, 'DnsApiCredentialLocation')
        if not self.credential_store_location:
            raise AttributeError(self.__class__.__name__ +
                                 " Requires DnsApiCredentialLocation Parameter")
        self.apiurl = get_resource_property(
            event, 'DnsApiUrl')
        if not self.apiurl:
            raise AttributeError(self.__class__.__name__ +
                                 " Requires DnsApiUrl Parameter")
        self.hosted_zone_name = get_resource_property(event, 'HostedZoneName')
        if not self.hosted_zone_name:
            raise AttributeError(self.__class__.__name__ +
                                 " Requires HostedZoneName Parameter")
                                 
        self.get_credentials()


    def dns_record_exists(self,record_name,record_value):
        logger.info(
            "Checking if record already exists: Record Name = %s, Record Value = %s.",
            record_name, record_value)

        start_record_name = record_name.split('.')[0]
        #TODO: Implement M&M API
        mmsession = requests.Session()
        Params = {'filter': 'type=CNAME,name='+ record_name }
        response = mmsession.get(self.apiurl + '/DNSZones/' + self.hosted_zone_name +
                                 '/DNSRecords', headers=self.headers, auth=self.credentials)

        logger.info("Record does not exist")
        return False

    def modify_dns_record(self, action, record_name, record_value):
        record_exists = self.dns_record_exists(record_name, record_value)
        if not record_exists or action == "DELETE":
            #TODO: Implement M&M API
            pass
        else:
            logger.info("Record exists, skipping create.")