import boto3
import logging
import cfnresponse
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        if event['RequestType'] == "Create":
            domain_name = get_resource_property(event, 'DomainName')
            additional_domains = get_resource_property(event, 'AdditionalDomains')
            validation_domain = get_resource_property(event, 'ValidationDomain')
            certificate_region = get_resource_property(event, 'CertificateRegion')
            certificate_tags = get_resource_property(event, 'CertificateTags')
            hosted_zone_id = get_resource_property(event, 'HostedZoneId')

            certificate_arn = create_acm_certificate(event, context, domain_name, additional_domains, validation_domain, certificate_region)

            if certificate_tags is not None:
                add_tags_to_acm_certificate(certificate_region, certificate_arn, certificate_tags)

            validate_acm_certificate(event, context, certificate_arn, certificate_region, additional_domains, hosted_zone_id)

            wait_for_cert_to_validate(event, context, certificate_arn, certificate_region)
            send_cfnresponse(event, context, "SUCCESS", {'response': 'validated', 'certificate_arn': certificate_arn})
        elif event['RequestType'] == "Delete":
            certificate_region = get_resource_property(event, 'CertificateRegion')
            hosted_zone_id = get_resource_property(event, 'HostedZoneId')

            certificate_arn = get_certificate_arn_from_cfn_stack(event, context, certificate_region)
            deleting_records(event, context, certificate_region, certificate_arn, hosted_zone_id)
            delete_certificate(event, context, certificate_arn, certificate_region)
            send_cfnresponse(event, context, "SUCCESS", {'response': 'deleted', 'certificate_arn': certificate_arn})
        else:
            certificate_region = get_resource_property(event, 'CertificateRegion')
            certificate_arn = get_certificate_arn_from_cfn_stack(event, context, certificate_region)
            send_cfnresponse(event, context, "SUCCESS", {'response': 'skipped_because_update', 'certificate_arn': certificate_arn})

    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def deleting_records(event, context, certificate_region, certificate_arn, hosted_zone_id):
    try:
        client = boto3.client('acm', region_name=certificate_region)
        response = client.describe_certificate(
            CertificateArn=certificate_arn
        )

        crt_data = response['Certificate']
        validation_options = crt_data['DomainValidationOptions']
        for validations in validation_options:
            record = validations['ResourceRecord']
            modify_dns_record(event, context, 'DELETE', hosted_zone_id, record['Name'], record['Value'], certificate_region)
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def dns_record_exists(event, context, hosted_zone_id, record_name, record_value, certificate_region):
    try:
        exists = False
        start_record_name = record_name.split('.')[0]

        r53_client = boto3.client('route53', region_name=certificate_region)
        response = r53_client.list_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            StartRecordName=start_record_name,
            StartRecordType='CNAME'
        )

        for record in response['ResourceRecordSets']:
            if record_name == record['Name']:
                exists = True
                return exists
        return exists

    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def modify_dns_record(event, context, action, hosted_zone_id, record_name, record_value, certificate_region):
    try:
        record_exists = dns_record_exists(event, context, hosted_zone_id, record_name, record_value, certificate_region)
        if not record_exists:
            r53_client = boto3.client('route53', region_name=certificate_region)
            response = r53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': action,
                            'ResourceRecordSet': {
                                'Name': record_name,
                                'SetIdentifier': record_name,
                                'TTL': 60,
                                'Type': 'CNAME',
                                'Region': certificate_region,
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

def delete_certificate(event, context, certificate_arn, certificate_region):
    try:
        logger.info("Deleting certificate: " + certificate_arn)
        client = boto3.client('acm', region_name=certificate_region)
        response = client.delete_certificate(
            CertificateArn=certificate_arn
        )
        logger.info("Deleted certificate: " + certificate_arn)
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def wait_for_cert_to_validate(event, context, certificate_arn, certificate_region):
    try:
        logger.info("Waiting for certificate to validate.")
        client = boto3.client('acm', region_name=certificate_region)

        not_validated = True

        while not_validated:
            time.sleep(10)
            response = client.describe_certificate(
                CertificateArn=certificate_arn
            )

            if 'Certificate' in response:
                crt_data = response['Certificate']
                status = crt_data['Status']
                logger.info("Certificate status: " + status)
                if status == "ISSUED":
                    not_validated = False

        logger.info("Certificate validated.")
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def validate_acm_certificate(event, context, certificate_arn, certificate_region, additional_domains, hosted_zone_id):
    try:
        number_of_additional_domains = 0
        if additional_domains is not None:
            number_of_additional_domains = len(additional_domains)

        logger.info("Creating validation records.")
        client = boto3.client('acm', region_name=certificate_region)

        no_records = True

        while no_records:
            time.sleep(10)
            response = client.describe_certificate(
                CertificateArn=certificate_arn
            )

            if 'Certificate' in response:
                crt_data = response['Certificate']
                if 'DomainValidationOptions' in crt_data:
                    validation_options = crt_data['DomainValidationOptions']
                    if len(validation_options) == number_of_additional_domains +1:
                        no_records = False
                        for validations in validation_options:
                            record = validations['ResourceRecord']
                            modify_dns_record(event, context, 'CREATE', hosted_zone_id, record['Name'], record['Value'], certificate_region)

        logger.info("Creating validation records complete.")
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def create_acm_certificate(event, context, domain_name, additional_domains, validation_domain, certificate_region):
    try:
        client = boto3.client('acm', region_name=certificate_region)
        idem_potency_token = get_resource_property(event, 'IdempotencyToken')

        if additional_domains is None:
            response = client.request_certificate(
                DomainName=domain_name,
                ValidationMethod='DNS',
                IdempotencyToken=idem_potency_token,
                DomainValidationOptions=[
                    {
                        'DomainName': domain_name,
                        'ValidationDomain': validation_domain
                    },
                ],
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                }
            )
        else:
            response = client.request_certificate(
                DomainName=domain_name,
                ValidationMethod='DNS',
                SubjectAlternativeNames=additional_domains,
                IdempotencyToken=idem_potency_token,
                DomainValidationOptions=[
                    {
                        'DomainName': domain_name,
                        'ValidationDomain': validation_domain
                    },
                ],
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                }
            )
        logger.info("Created acm certificate " + response['CertificateArn'])
        return response['CertificateArn']
    except Exception as e:
        send_cfnresponse(event, context, "FAILED", {'error': str(e)})

def add_tags_to_acm_certificate(certificate_region, certificate_arn, certificate_tags):
    client = boto3.client('acm', region_name=certificate_region)
    client.add_tags_to_certificate(
        CertificateArn=certificate_arn,
        Tags=certificate_tags
    )
    logger.info("Added tags to certificate " + certificate_arn)

def get_resource_property(event, resource_property):
    resource_properties = event['ResourceProperties']
    if resource_property in resource_properties:
        return resource_properties[resource_property]
    else:
        return None

def send_cfnresponse(event, context, status, data):
    if status == "SUCCESS":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, data)
    else:
        logger.error(str(data))
        cfnresponse.send(event, context, cfnresponse.FAILED, data)