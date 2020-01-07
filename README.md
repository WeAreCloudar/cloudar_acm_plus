# Cloudar-acm-plus

A custom resource written in Python to create acm certificates in cloudformation
with automatic DNS validation for domains managed by AWS hostedzone and the option to create the certificate in a different region then the cloudformation stack region.

## Features

- Create acm certificate with dns validation:
    - custom parameters:
        - Domain name
        - Additional domains
        - Validation domain
        - Region
        - Tags
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

IMPORTANT:  
For the delete and cleanup functionality it is required to set the following output in your cloudformation.

`Outputs:`  
&nbsp;&nbsp;  `NameCustomResource:`  
&nbsp;&nbsp;&nbsp;&nbsp;    `Description: The arn of the certificate created by NameCustomResource `  
&nbsp;&nbsp;&nbsp;&nbsp;    `Value: !GetAtt NameCustomResource.certificate_arn`  

Parameters for Type: Custom::CreateCertificates :
- DomainName: (REQUIRED type:String) The domain name for the acm certificate.
- AdditionalDomains: (OPTIONAL type:List) Additional domains for the acm certificate
- ValidationDomain: (REQUIRED type:string) The domain name for the validation domain of the acm certificate
- HostedZoneId: (REQUIRED type:string) The hosted zone id for the validation domain of the acm certificate
- CertificateRegion: (REQUIRED type:string) The region to deploy the acm certificate in
- IdempotencyToken: (REQUIRED type:string pattern: \w+) The idempotency token for the create call of the acm certificate
  doc: https://docs.aws.amazon.com/acm/latest/APIReference/API_RequestCertificate.html#ACM-RequestCertificate-request-IdempotencyToken
- CertificateTags: (OPTIONAL type:list) The tags for the acm certificate

Outputs for Type: Custom::CreateCertificates :
- certificate_arn: The arn of the acm certificate created by the custom resource. (!GetAtt NameCustomResource.certificate_arn)