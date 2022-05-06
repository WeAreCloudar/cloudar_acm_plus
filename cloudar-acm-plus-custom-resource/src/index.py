import boto3
import logging
import cfnresponse
import time
import sys
from helper import get_resource_property
from dns.route53 import Route53
from dns.menandmice import MenAndMice

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class acm_certificate:
    def __init__(self,event):
        self.domain_name = get_resource_property(event, 'DomainName')
        self.additional_domains = get_resource_property(event, 'AdditionalDomains')
        self.validation_domain = get_resource_property(event, 'ValidationDomain')
        self.certificate_region = get_resource_property(event, 'CertificateRegion')
        self.certificate_tags = get_resource_property(event, 'CertificateTags')
        self.dns_service = None
        self.idem_potency_token = get_resource_property(event,
                                                       'IdempotencyToken')
        self.client = boto3.client('acm', region_name=self.certificate_region)
        self.certificate_arn = None

    def load_dns_handler(self,event):
        self.dns_service = instantiate_class(
            get_resource_property(event, 'DnsService'))
        handle_event = getattr(self.dns_service, 'handle_event', None)
        if callable(handle_event):
            self.dns_service.handle_event(event)

    def set_certificate_arn(self,certificate_arn):
        self.certificate_arn = certificate_arn

    def get_certificate_arn(self):
        if self.certificate_arn:
            return self.certificate_arn
        else:
            return ""

    def get_certificate_region(self):
        return self.certificate_region

    def create_certificate(self):
        if self.additional_domains is None:
            response = self.client.request_certificate(
                DomainName=self.domain_name,
                ValidationMethod='DNS',
                IdempotencyToken=self.idem_potency_token,
                DomainValidationOptions=[
                    {
                        'DomainName': self.domain_name,
                        'ValidationDomain': self.validation_domain
                    },
                ],
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                })
        else:
            response = self.client.request_certificate(
                DomainName=self.domain_name,
                ValidationMethod='DNS',
                SubjectAlternativeNames=self.additional_domains,
                IdempotencyToken=self.idem_potency_token,
                DomainValidationOptions=[
                    {
                        'DomainName': self.domain_name,
                        'ValidationDomain': self.validation_domain
                    },
                ],
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                })
        logger.info("Created acm certificate " + response['CertificateArn'])
        self.set_certificate_arn(response['CertificateArn'])

    def delete_certificate(self):
        logger.info("Deleting certificate: " + self.certificate_arn)
        response = self.client.delete_certificate(CertificateArn=self.certificate_arn)
        logger.info("Deleted certificate: " + self.certificate_arn)

    def add_tags(self):
        if self.certificate_tags is not None:
            self.client.add_tags_to_certificate(
                CertificateArn=self.certificate_arn,
                Tags=self.certificate_tags)
            logger.info("Added tags to certificate " + self.certificate_arn)

    def validate_certificate(self):
        number_of_additional_domains = 0
        if self.additional_domains is not None:
            number_of_additional_domains = len(self.additional_domains)

        logger.info("Creating validation records.")

        no_records = True

        while no_records:
            time.sleep(10)
            response = self.client.describe_certificate(
                CertificateArn=self.certificate_arn
            )

            if 'Certificate' in response:
                crt_data = response['Certificate']
                if 'DomainValidationOptions' in crt_data:
                    validation_options = crt_data['DomainValidationOptions']
                    if len(validation_options) == number_of_additional_domains +1:
                        no_records = False
                        for validations in validation_options:
                            record = validations['ResourceRecord']
                            self.dns_service.modify_dns_record('CREATE',record['Name'], record['Value'])

        logger.info("Creating validation records complete.")

    def wait_for_cert_to_validate(self):
        logger.info("Waiting for certificate to validate.")

        not_validated = True

        while not_validated:
            time.sleep(10)
            response = self.client.describe_certificate(
                CertificateArn=self.certificate_arn)

            if 'Certificate' in response:
                crt_data = response['Certificate']
                status = crt_data['Status']
                logger.info("Certificate status: " + status)
                if status == "ISSUED":
                    not_validated = False

        logger.info("Certificate validated.")

    def delete_records(self):
        response = self.client.describe_certificate(CertificateArn=self.certificate_arn)
        crt_data = response['Certificate']
        validation_options = crt_data['DomainValidationOptions']
        for validations in validation_options:
            record = validations['ResourceRecord']
            self.dns_service.modify_dns_record('DELETE',record['Name'], record['Value'])

def handler(event, context):
    try:
        acm = acm_certificate(event)
        if event['RequestType'] == "Create":
            acm.load_dns_handler(event)
            acm.create_certificate()
            acm.add_tags()
            acm.validate_certificate()
            acm.wait_for_cert_to_validate()
            send_cfnresponse(event, context, "SUCCESS", {'response': 'validated', 'certificate_arn': acm.get_certificate_arn()})
        elif event['RequestType'] == "Delete":
            acm.load_dns_handler(event)
            certificate_arn = get_certificate_arn_from_cfn_stack(event, context, acm.get_certificate_region())
            acm.set_certificate_arn(certificate_arn)
            acm.delete_records()
            acm.delete_certificate()
            send_cfnresponse(event, context, "SUCCESS", {'response': 'deleted', 'certificate_arn': certificate_arn})
        else:
            certificate_arn = get_certificate_arn_from_cfn_stack(event, context, acm.get_certificate_region())
            send_cfnresponse(event, context, "SUCCESS", {'response': 'skipped_because_update', 'certificate_arn': certificate_arn})

    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def get_certificate_arn_from_cfn_stack(event, context, certificate_region):
    try:
        resource_id = event['LogicalResourceId']
        stack_id = event['StackId']
        certificate_arn = ""

        client = boto3.client('cloudformation', region_name=certificate_region)
        response = client.describe_stacks(
            StackName=stack_id
        )

        for stack in response['Stacks']:
            outputs = stack['Outputs']
            for output in outputs:
                if output['OutputKey'] == resource_id:
                    certificate_arn = output['OutputValue']

        return certificate_arn
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def instantiate_class(classname):
    return getattr(sys.modules[__name__], classname)()
    
def send_cfnresponse(event, context, status, data):
    if status == "SUCCESS":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, data)
    else:
        logger.error(str(data))
        cfnresponse.send(event, context, cfnresponse.FAILED, data)
