#!/bin/bash

# Strict mode, fail on any error
set -euo pipefail

# Azure configuration
FILE=".deploy.env"
if [[ -f $FILE ]]; then
	echo "loading from $FILE"
  eval $(egrep "^[^#;]" $FILE | tr '\n' '\0' | xargs -0 -n1 | sed 's/^/export /')
else
	cat << EOF > .deploy.env
RESOURCE_GROUP=""
LOCATION=""
LOG_ANALYTICS_WORKSPACE=""
CONTAINERAPPS_ENVIRONMENT="dm-dab-aca-env"
CONTAINERAPPS_APP_NAME="dm-dab-aca-app"
MSSQL=''
EOF
	echo "Enviroment file (.deploy.env) not detected."
	echo "Please configure values for your environment in the created .env file and run the script again."
	echo "Read the docs/running-in-azure.md to get info on needed enviroment variables."
	exit 1
fi

echo "starting"
cat << EOF > log.txt
EOF

echo "creating resource group '$RESOURCE_GROUP'"  | tee -a log.txt
az group create --name $RESOURCE_GROUP --location $LOCATION \
    -o json >> log.txt

echo "create log analytics workspace '$LOG_ANALYTICS_WORKSPACE'" | tee -a log.txt
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  -o json >> log.txt

echo "retrieving log analytics client id" | tee -a log.txt
LOG_ANALYTICS_WORKSPACE_CLIENT_ID=$(az monitor log-analytics workspace show  \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_WORKSPACE" \
  --query customerId  \
  --output tsv | tr -d '[:space:]')

echo "retrieving log analytics secret" | tee -a log.txt
LOG_ANALYTICS_WORKSPACE_CLIENT_SECRET=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_WORKSPACE" \
  --query primarySharedKey \
  --output tsv | tr -d '[:space:]')

echo "creating container apps environment: '$CONTAINERAPPS_ENVIRONMENT'" | tee -a log.txt
az containerapp env create \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --name "$CONTAINERAPPS_ENVIRONMENT" \
  --logs-workspace-id "$LOG_ANALYTICS_WORKSPACE_CLIENT_ID" \
  --logs-workspace-key "$LOG_ANALYTICS_WORKSPACE_CLIENT_SECRET" \
  -o json >> log.txt

echo "waiting to finalize the ACA environment" | tee -a log.txt
while [ "$(az containerapp env show -n $CONTAINERAPPS_ENVIRONMENT -g $RESOURCE_GROUP --query properties.provisioningState -o tsv | tr -d '[:space:]')" != "Succeeded" ]; do sleep 10; done

echo "get ACA environment id" | tee -a log.txt
CONTAINERAPPS_ENVIRONMENTID=$(az containerapp env show -n "$CONTAINERAPPS_ENVIRONMENT" -g "$RESOURCE_GROUP" --query id -o tsv |sed 's/\r$//')

echo "creating container app : '$CONTAINERAPPS_APP_NAME' on the environment : '$CONTAINERAPPS_ENVIRONMENT'" | tee -a log.txt
az deployment group create \
  -g $RESOURCE_GROUP \
  -f ./bicep/aca.bicep \
  -p appName=$CONTAINERAPPS_APP_NAME environmentId=$CONTAINERAPPS_ENVIRONMENTID connectionString="$MSSQL" \
  -o json >> log.txt

echo "get the azure container app FQDN" | tee -a log.txt
ACA_FQDN=$(az containerapp show -n $CONTAINERAPPS_APP_NAME -g $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')

echo "application deployed at: https://${ACA_FQDN}"

echo "done" | tee -a log.txt
