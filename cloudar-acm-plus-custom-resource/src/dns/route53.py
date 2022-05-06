import boto3
import logging
import time
from helper import get_resource_property

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Route53:

    def __init__(self):
        self.certificate_region = None
        self.client = None

    def handle_event(self,event):
        self.certificate_region = get_resource_property(event, 'CertificateRegion')
        self.client = boto3.client('route53',region_name=self.certificate_region)
        self.hosted_zone_id = get_resource_property(event, 'HostedZoneId')
        if not self.hosted_zone_id:
            raise AttributeError(self.__class__.__name__  + " Requires HostedZoneId Parameter")

    
    def dns_record_exists(self,record_name,record_value):
        logger.info(
            "Checking if record already exists: Hosted Zone = %s, Record Name = %s, Record Value = %s.",
            self.hosted_zone_id, record_name, record_value)

        start_record_name = record_name.split('.')[0]
        iterator = self.client.get_paginator('list_resource_record_sets').paginate(HostedZoneId=self.hosted_zone_id)
        for page in iterator:
            for record in page.get('ResourceRecordSets'):
                if record_name == record['Name']:
                    logger.info("Record exists")
                    return True

        logger.info("Record does not exist")
        return False
        
    def modify_dns_record(self, action, record_name, record_value):
        record_exists = self.dns_record_exists(record_name, record_value)
        if not record_exists or action == "DELETE":
            response = self.client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': action,
                            'ResourceRecordSet': {
                                'Name': record_name,
                                'SetIdentifier': record_name,
                                'TTL': 60,
                                'Type': 'CNAME',
                                'Region': self.certificate_region,
                                'ResourceRecords': [
                                    {
                                        'Value': record_value
                                    },
                                ]
                            }
                        }
                    ]
                }
            )
        else:
            logger.info("Record exists, skipping create.")