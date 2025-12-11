param location string
param environmentName string
param resourceToken string
param tags object
param userAssignedIdentityPrincipalId string
@secure()
param todoDbPassword string

var keyVaultName = 'azkv${resourceToken}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: userAssignedIdentityPrincipalId
        permissions: {
          secrets: [
            'Get'
            'List'
          ]
        }
      }
    ]
  }
}

resource todoDbPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'todo-db-password'
  parent: keyVault
  properties: {
    value: todoDbPassword
  }
}

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
