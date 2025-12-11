param location string
param environmentName string
param resourceToken string
param tags object
param serviceName string
param logAnalyticsCustomerId string
param logAnalyticsWorkspaceId string
param acaSubnetId string
param registryLoginServer string
param userAssignedIdentityId string
param minReplicas int = 0
param maxReplicas int = 3
param containerCpu int = 1
param containerMemory string = '2Gi'
param targetPort int = 8000
param secrets array = []
param corsConfig object = {
  allowedOrigins: [
    '*'
  ]
  allowedMethods: [
    'GET'
    'POST'
    'PUT'
    'DELETE'
    'OPTIONS'
    'PATCH'
  ]
  allowedHeaders: [
    '*'
  ]
  exposeHeaders: [
    '*'
  ]
  maxAge: 3600
  allowCredentials: false
}
param environmentVariables array = []
@description('Container image repository path inside ACR (e.g., fastapi-reference-arch/api-dev).')
param imageRepository string = 'fastapi-reference-arch/api-dev'
@description('Container image tag to deploy (e.g., git SHA or dev).')
param imageTag string = 'latest'
@description('Optional full image reference (registry/repo:tag). When set, overrides repository/tag concatenation. Defaults to public sample image to allow first provision before custom image exists.')
param image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var managedEnvironmentName = 'azace${resourceToken}'
var containerAppName = 'azaca${resourceToken}'
var logAnalyticsSharedKey = listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-02-02-preview' = {
  name: managedEnvironmentName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnetId
    }
    workloadProfiles: [
      {
        name: 'consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-02-02-preview' = {
  name: containerAppName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
    'azd-service-name': serviceName
  })
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      secrets: secrets
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'Auto'
        corsPolicy: corsConfig
      }
      registries: [
        {
          server: registryLoginServer
          identity: userAssignedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: serviceName
          image: image != '' ? image : '${registryLoginServer}/${imageRepository}:${imageTag}'
          resources: {
            cpu: containerCpu
            memory: containerMemory
          }
          env: environmentVariables
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output containerAppId string = containerApp.id
output containerAppPrincipalId string = containerApp.identity.principalId
output containerAppUrl string = containerApp.properties.configuration.?ingress.?fqdn
output outboundIpAddresses array = containerApp.properties.outboundIpAddresses ?? []
output managedEnvironmentId string = managedEnvironment.id
