# Cloudar-acm-plus

A custom resource written in Python to create acm certificates in cloudformation
with automatic DNS validation for domains managed by AWS Route53 or another DNS solution and the option to create the certificate in a different region then the cloudformation stack region.

## Features

- Create acm certificate with dns validation:
    - custom parameters:
        - Domain name
        - Additional domains
        - Validation domain
        - Region
        - Tags
        - DnsService (Currently Route53 or MenAndMice)
- Automatic DNS validation of the acm certificate
- Specify AWS region to create the certificate in, independent of the Cloudformation stack region
- Cleanup DNS validation records and deleting the acm certificate on delete of the Cloudformation stack     
    
## Requirements

- Python 3.7
- Pip
- Bash
- Zip

- S3 bucket to put the custom resource package

## Deploy the custom resource

`cd cloudar-acm-plus-custom-resource`  
`sh install_dependencies`  
`sh pack_custom_resource`

Upload the zip file _cloudar-acm-plus-custom-resource/packed/cloudar-acm-plus-custom-resource.zip_
to the S3 bucket you want to use with your custom resource in a cloudformation template.

## Implementation notes

See cfn.yaml as an example. 

Parameters for Type: Custom::CreateCertificates :
- DomainName: (REQUIRED type:String) The domain name for the acm certificate.
- AdditionalDomains: (OPTIONAL type:List) Additional domains for the acm certificate
- ValidationDomain: (REQUIRED type:String) The domain name for the validation domain of the acm certificate
- HostedZoneId: (OPTIONAL (REQUIRED FOR Route53) type:string) The hosted zone id for the validation domain of the acm certificate
- DnsApiCredentialLocation: (OPTIONAL (REQUIRED FOR MenAndMice) type:String) SSM Parameter Store path where credentials and api url is stored. (SecureString)
  The script will be looking for username, password and apiurl ssm parameters in the path. in case of MenAndMice dns service.
- HostedZoneName; (OPTIONAL (REQUIRED FOR MenAndMice) type:String) Zone name to add the dns validation record to 
- CertificateRegion: (REQUIRED type:string) The region to deploy the acm certificate in
- IdempotencyToken: (REQUIRED type:string pattern: \w+) The idempotency token for the create call of the acm certificate
  doc: https://docs.aws.amazon.com/acm/latest/APIReference/API_RequestCertificate.html#ACM-RequestCertificate-request-IdempotencyToken
- CertificateTags: (OPTIONAL type:list) The tags for the acm certificate
- KeepDNSRecord (OPTIONAL type:String) If value is set to "yes", the Validation records will not be deleted.

Outputs for Type: Custom::CreateCertificates :
- certificate_arn: The arn of the acm certificate created by the custom resource. (!GetAtt NameCustomResource.certificate_arn)