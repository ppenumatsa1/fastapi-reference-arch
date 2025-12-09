param location string
param environmentName string
param resourceToken string
param tags object
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Basic'

var registryName = 'azacr${resourceToken}'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: registryName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output registryId string = containerRegistry.id
output loginServer string = containerRegistry.properties.loginServer
