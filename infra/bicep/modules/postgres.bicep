param location string
param environmentName string
param resourceToken string
param tags object
@description('SKU name for Azure Database for PostgreSQL Flexible Server (e.g., Standard_B1ms).')
param skuName string = 'Standard_B1ms'
@description('Server version to deploy.')
@allowed([
  '13'
  '14'
  '15'
  '16'
])
param serverVersion string = '16'
@description('Storage size (GB).')
param storageSizeGb int = 32
@description('Number of days to retain backups.')
param backupRetentionDays int = 7
@allowed([
  'Enabled'
  'Disabled'
])
param geoRedundantBackup string = 'Disabled'
@description('Admin login used for break-glass scenarios (AAD recommended for day-to-day access).')
param administratorLogin string = 'aad_admin'
@secure()
@description('Admin password supplied via azd secret or pipeline variable. Not stored in source control.')
param administratorPassword string
@description('Enable or disable public network access (Enabled to use firewall allow lists).')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

var serverName = 'azpgs${resourceToken}'

#disable-next-line BCP081
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  sku: {
    name: skuName
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    version: serverVersion
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackup
    }
    storage: {
      storageSizeGB: storageSizeGb
    }
    network: {
      publicNetworkAccess: publicNetworkAccess
    }
    highAvailability: {
      mode: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled'
    }
  }
}

// AAD admin is set by postprovision hook after server is fully ready

@description('Firewall rule to allow all IPs for development. Restrict in production.')
#disable-next-line BCP081
resource postgresAllowAllFirewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgresServer
  name: 'AllowAll'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'
  }
}

output serverId string = postgresServer.id
output serverName string = postgresServer.name
output fullyQualifiedDomainName string = postgresServer.properties.fullyQualifiedDomainName
