import boto3
import logging
import time
from helper import get_resource_property

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MenAndMice:

    def __init__(self):
        self.client = None

    #def handle_event(self,event):
    #  #TODO: Implement M&M API


    def dns_record_exists(self,record_name,record_value):
        logger.info(
            "Checking if record already exists: Hosted Zone = %s, Record Name = %s, Record Value = %s.",
            self.hosted_zone_id, record_name, record_value)

        start_record_name = record_name.split('.')[0]
        #TODO: Implement M&M API

        logger.info("Record does not exist")
        return False

    def modify_dns_record(self, action, record_name, record_value):
        record_exists = self.dns_record_exists(record_name, record_value)
        if not record_exists or action == "DELETE":
            #TODO: Implement M&M API
            pass
        else:
            logger.info("Record exists, skipping create.")