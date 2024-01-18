@secure()
param connectionString string

param appName string

param environmentId string

param isExternalIngress bool = true

param location string = resourceGroup().location

param tag string = 'latest'

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  properties: {
    environmentId: environmentId
    configuration: {
      activeRevisionsMode:'Single'
      ingress: {
        allowInsecure:true
        external: isExternalIngress
        targetPort: 5000
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          image: 'yorek/azure-sql-db-vectors-kmeans:${tag}'
          name: appName
          env: [
            {
              name: 'MSSQL'
              value: connectionString
            }
          ]          
          resources:{
            cpu: json('2')
            memory:'4Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
        rules:[
          {
            name: 'http'
            http:{
              metadata:{
                concurrentRequests: '200'
              }
            }
          }
        ]
      } 
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
