param location string
param environmentName string
param resourceToken string
param tags object

var workspaceName = 'azlog${resourceToken}'
var appInsightsName = 'azapp${resourceToken}'

resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: union(tags, {
    'azd-env-name': environmentName
  })
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logWorkspace.id
  }
}

output logAnalyticsId string = logWorkspace.id
output logAnalyticsCustomerId string = logWorkspace.properties.customerId
output appInsightsConnectionString string = applicationInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
