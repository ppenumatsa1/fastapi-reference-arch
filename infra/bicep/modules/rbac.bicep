param acrId string
param userAssignedIdentityPrincipalId string


var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var acrName = last(split(acrId, '/'))

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: acrName
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, userAssignedIdentityPrincipalId, 'acr-pull')
  scope: acr
  properties: {
    principalId: userAssignedIdentityPrincipalId
    roleDefinitionId: acrPullRoleId
    principalType: 'ServicePrincipal'
  }
}

// Note: PostgreSQL access uses password-based authentication; managed identity is not used for database logins.
// Database-level permissions are managed within PostgreSQL itself, not via Azure RBAC.
