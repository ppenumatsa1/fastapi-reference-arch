targetScope = 'resourceGroup'

@description('Azure Developer CLI environment name (maps to azd-env-name tag).')
param environmentName string
@description('Azure region for all resources.')
param location string = resourceGroup().location
@description('Service name used for azd-service-name tag on Container Apps.')
param serviceName string = 'api'
@description('Optional tags applied to every resource.')
param tags object = {}
@description('Virtual network CIDR block.')
param vnetCidr string = '10.24.0.0/16'
@description('Subnet used by Azure Container Apps environment.')
param acaSubnetCidr string = '10.24.0.0/24'
@description('Subnet for PostgreSQL VNet injection (delegated to Microsoft.DBforPostgreSQL/flexibleServers).')
param postgresSubnetCidr string = '10.24.1.0/28'
@description('Secure administrator password for PostgreSQL flexible server.')
@secure()
param postgresAdminPassword string
@description('Azure AD administrator definition for PostgreSQL flexible server. Expected properties: principalName, principalType, principalId, tenantId.')
param aadAdministrator object
@description('Optional array of environment variables applied to the container app. Each entry should include name/value or name/secretRef.')
param environmentVariables array = []

var resourceToken = uniqueString(subscription().id, resourceGroup().id, location, environmentName)
var baseTags = union(tags, {
  'azd-env-name': environmentName
})

module identityModule './modules/identity.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
  }
}

module registryModule './modules/registry.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
  }
}

module monitoringModule './modules/monitoring.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
  }
}

module networkModule './modules/network.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
    vnetCidr: vnetCidr
    acaSubnetCidr: acaSubnetCidr
    postgresSubnetCidr: postgresSubnetCidr
  }
}

module privateDnsModule './modules/privatedns.bicep' = {
  params: {
    environmentName: environmentName
    tags: baseTags
    vnetId: networkModule.outputs.vnetId
  }
}

module postgresModule './modules/postgres.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
    administratorPassword: postgresAdminPassword
    aadAdministrator: aadAdministrator
    delegatedSubnetId: networkModule.outputs.postgresSubnetId
    privateDnsZoneId: privateDnsModule.outputs.privateDnsZoneId
  }
}

module acaModule './modules/aca.bicep' = {
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: baseTags
    serviceName: serviceName
    logAnalyticsCustomerId: monitoringModule.outputs.logAnalyticsCustomerId
    logAnalyticsWorkspaceId: monitoringModule.outputs.logAnalyticsId
    acaSubnetId: networkModule.outputs.acaSubnetId
    registryLoginServer: registryModule.outputs.loginServer
    userAssignedIdentityId: identityModule.outputs.identityId
    environmentVariables: environmentVariables
  }
}

module rbacModule './modules/rbac.bicep' = {
  params: {
    acrId: registryModule.outputs.registryId
    userAssignedIdentityPrincipalId: identityModule.outputs.principalId
  }
}

output RESOURCE_GROUP_ID string = resourceGroup().id
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registryModule.outputs.loginServer
output CONTAINER_APP_FQDN string = acaModule.outputs.containerAppUrl
output POSTGRES_FQDN string = postgresModule.outputs.fullyQualifiedDomainName
