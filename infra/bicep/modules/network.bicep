param location string
param environmentName string
param resourceToken string
param tags object
param vnetCidr string
param acaSubnetCidr string
param postgresSubnetCidr string = '10.24.1.0/28'

var vnetName = 'aznet${resourceToken}'
var acaSubnetName = 'aca'
var postgresSubnetName = 'postgres'

resource acaNsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: 'aznsg${resourceToken}-aca'
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    securityRules: [
      {
        name: 'AllowHttpFromInternet'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '80'
        }
      }
    ]
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetCidr
      ]
    }
    subnets: [
      {
        name: acaSubnetName
        properties: {
          addressPrefix: acaSubnetCidr
          delegations: [
            {
              name: 'acaDelegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          networkSecurityGroup: {
            id: acaNsg.id
          }
        }
      }
      {
        name: postgresSubnetName
        properties: {
          addressPrefix: postgresSubnetCidr
          delegations: [
            {
              name: 'postgresDelegation'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

output vnetId string = virtualNetwork.id
output acaSubnetId string = virtualNetwork.properties.subnets[0].id
output postgresSubnetId string = virtualNetwork.properties.subnets[1].id
