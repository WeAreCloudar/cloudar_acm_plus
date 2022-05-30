def get_resource_property(event, resource_property):
    resource_properties = event['ResourceProperties']
    if resource_property in resource_properties:
        return resource_properties[resource_property]
    else:
        return None
        

def strip_domain(fqdn, domain):
    if fqdn.endswith("." + domain):
        return fqdn[:-(len("." + domain))]
    return None
