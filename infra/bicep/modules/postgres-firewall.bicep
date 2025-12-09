param serverName string
param acaOutboundIpAddresses array
param myIpAddress string

var acaIps = (acaOutboundIpAddresses == null || length(acaOutboundIpAddresses) == 0) ? [] : acaOutboundIpAddresses
var acaFirewallRules = [for (ip, idx) in acaIps: {
  name: 'aca-ip-${idx}'
  startIp: ip
  endIp: ip
}]
var devIpRule = myIpAddress == '' ? [] : [
  {
    name: 'dev-ip'
    startIp: myIpAddress
    endIp: myIpAddress
  }
]
var firewallRules = concat(acaFirewallRules, devIpRule)

resource postgresFirewallRules 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = [for rule in firewallRules: {
  name: '${serverName}/${rule.name}'
  properties: {
    startIpAddress: rule.startIp
    endIpAddress: rule.endIp
  }
}]
