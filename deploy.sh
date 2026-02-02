#!/bin/bash
# GCP Cloud Functions Deployment Script
# Usage: ./deploy.sh <project-id> <function-name> <region>

set -e

PROJECT_ID=${1:-your-project-id}
FUNCTION_NAME=${2:-starwars-function}
REGION=${3:-us-central1}
MEMORY=256
TIMEOUT=60

echo "Deploying Cloud Function..."
echo "Project: $PROJECT_ID"
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"

# Set project
gcloud config set project $PROJECT_ID

# Deploy function
gcloud functions deploy $FUNCTION_NAME \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point starwars_function \
  --region $REGION \
  --memory ${MEMORY}MB \
  --timeout ${TIMEOUT}s \
  --set-env-vars "API_KEYS=${API_KEYS:-},REDIS_URL=${REDIS_URL:-}" \
  --source .

echo ""
echo "✓ Cloud Function deployed successfully!"
echo "Function URL: https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}"

# Optional: Create API Gateway config
echo ""
echo "Next: Create API Gateway..."
echo "Copy the openapi.yaml from this repo and deploy with:"
echo "gcloud api-gateway apis create starwars-api"
echo "gcloud api-gateway api-configs create starwars-config --api=starwars-api --openapi-spec=openapi.yaml"
echo "gcloud api-gateway gateways create starwars-gateway --api=starwars-api --api-config=starwars-config --location=global"
