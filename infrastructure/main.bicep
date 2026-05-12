// ============================================================
// DACH IDP Platform — Azure Infrastructure (Bicep)
// Deploys: Document Intelligence, Blob Storage, SQL Server,
//          App Service, Key Vault, Application Insights
// ============================================================

@description('Environment name: dev, staging, prod')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region')
param location string = resourceGroup().location

@description('Project prefix for resource names')
param projectPrefix string = 'dach-idp'

@description('SQL Server admin username')
param sqlAdminUsername string

@secure()
@description('SQL Server admin password')
param sqlAdminPassword string

@description('Your IP address for SQL Server firewall rule')
param developerIpAddress string = '0.0.0.0'

var suffix = '${projectPrefix}-${environment}'
var tags = {
  project: 'dach-idp-platform'
  environment: environment
  owner: 'ai-team'
  costCenter: 'ai-innovation'
  dataClassification: 'confidential'
  gdprCompliant: 'true'
}

// ── Application Insights ──────────────────────────────────────────────────────
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 90
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${suffix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ── Azure Key Vault ───────────────────────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: 'kv-${replace(suffix, '-', '')}${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

// ── Storage Account (Blob) ────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${replace(suffix, '-', '')}${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: { name: environment == 'prod' ? 'Standard_GRS' : 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: { enabled: true, keyType: 'Account' }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

// ── Blob Containers ───────────────────────────────────────────────────────────
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30  // Soft delete for GDPR recovery window
    }
  }
}

resource invoicesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'invoices'
  properties: { publicAccess: 'None' }
}

resource cvsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'cvs'
  properties: { publicAccess: 'None' }
}

resource auditContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'audit-exports'
  properties: { publicAccess: 'None' }
}

// ── Azure AI Document Intelligence ───────────────────────────────────────────
resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'di-${suffix}'
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: { name: environment == 'prod' ? 'S0' : 'F0' }
  properties: {
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    customSubDomainName: 'di-${suffix}-${uniqueString(resourceGroup().id)}'
  }
}

// ── Azure SQL Server ─────────────────────────────────────────────────────────
resource sqlServer 'Microsoft.Sql/servers@2022-11-01-preview' = {
  name: 'sql-${suffix}'
  location: location
  tags: tags
  properties: {
    administratorLogin: sqlAdminUsername
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2022-11-01-preview' = {
  parent: sqlServer
  name: 'dach-idp'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'S2' : 'Basic'
    tier: environment == 'prod' ? 'Standard' : 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'prod' ? 10737418240 : 2147483648
  }
}

resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2022-11-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource developerFirewallRule 'Microsoft.Sql/servers/firewallRules@2022-11-01-preview' = if (developerIpAddress != '0.0.0.0') {
  parent: sqlServer
  name: 'DeveloperAccess'
  properties: {
    startIpAddress: developerIpAddress
    endIpAddress: developerIpAddress
  }
}

// ── App Service Plan ─────────────────────────────────────────────────────────
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: 'asp-${suffix}'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'P1v3' : 'B1'
    tier: environment == 'prod' ? 'PremiumV3' : 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true  // Linux
  }
}

// ── App Service (Web App) ─────────────────────────────────────────────────────
resource appService 'Microsoft.Web/sites@2022-09-01' = {
  name: 'app-${suffix}'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'  // Managed identity for Key Vault access
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2'
      alwaysOn: environment == 'prod'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'APP_MODE', value: 'live' }
        { name: 'APP_ENV', value: environment }
        { name: 'AZURE_DOC_INTEL_ENDPOINT', value: documentIntelligence.properties.endpoint }
        { name: 'AZURE_STORAGE_ACCOUNT_NAME', value: storageAccount.name }
        { name: 'AZURE_SQL_SERVER', value: '${sqlServer.name}.database.windows.net' }
        { name: 'AZURE_SQL_DATABASE', value: sqlDatabase.name }
        { name: 'USE_MANAGED_IDENTITY', value: 'true' }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: appInsights.properties.InstrumentationKey }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
      ]
    }
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint
output storageAccountName string = storageAccount.name
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output keyVaultName string = keyVault.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
