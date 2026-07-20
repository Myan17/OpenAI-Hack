@description('Azure region for this environment. Deployment values are supplied outside source control.')
param location string

@description('Environment label, for example staging or production.')
param environment string

@description('Globally unique PostgreSQL server name; do not use a customer identifier.')
param postgresServerName string

@description('Container registry name for immutable application images.')
param registryName string

var tags = {
  application: 'interlock'
  environment: environment
  managedBy: 'iac'
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: { name: 'Basic' }
  tags: tags
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Disabled'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresServerName
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
    }
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7 }
    network: { publicNetworkAccess: 'Disabled' }
  }
}

output registryLoginServer string = registry.properties.loginServer
output postgresResourceId string = postgres.id
