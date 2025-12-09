param location string
param environmentName string
param resourceToken string
param tags object

var identityName = 'azmid${resourceToken}'

resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
}

output identityId string = userIdentity.id
output clientId string = userIdentity.properties.clientId
output principalId string = userIdentity.properties.principalId
