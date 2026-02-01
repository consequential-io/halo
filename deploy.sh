#!/bin/bash
# Deploy script for Halo Ad Spend Agent
# Usage: ./deploy.sh [frontend|backend|all]

set -e

PROJECT_ID="otb-dev-platform"
REGION="us-central1"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Halo Deployment Script${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

deploy_all() {
    echo -e "${YELLOW}Deploying all services via Cloud Build...${NC}"
    gcloud builds submit --config cloudbuild.yaml --project $PROJECT_ID
    echo -e "${GREEN}All services deployed successfully!${NC}"
}

deploy_frontend() {
    echo -e "${YELLOW}Deploying frontend only...${NC}"

    BACKEND_URL="https://halo-backend-zqlsaqunba-uc.a.run.app"
    API_TOKEN="halo-demo-token-2026"

    # Build with proper build args
    cd frontend
    docker build \
        --build-arg VITE_API_URL=$BACKEND_URL \
        --build-arg VITE_API_TOKEN=$API_TOKEN \
        -t gcr.io/$PROJECT_ID/halo-frontend:latest .

    # Push to GCR
    docker push gcr.io/$PROJECT_ID/halo-frontend:latest

    # Deploy to Cloud Run
    gcloud run deploy halo-frontend \
        --image gcr.io/$PROJECT_ID/halo-frontend:latest \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --project $PROJECT_ID

    cd ..
    echo -e "${GREEN}Frontend deployed successfully!${NC}"
}

deploy_backend() {
    echo -e "${YELLOW}Deploying backend only...${NC}"

    cd backend
    gcloud run deploy halo-backend \
        --source . \
        --region $REGION \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=production,DATA_SOURCE=bq,GCP_PROJECT=$PROJECT_ID,API_TOKEN=halo-demo-token-2026,META_REDIRECT_URI=https://halo-backend-zqlsaqunba-uc.a.run.app/auth/meta/callback,FRONTEND_URL=https://adspend.consequential.io" \
        --project $PROJECT_ID

    cd ..
    echo -e "${GREEN}Backend deployed successfully!${NC}"
}

case "${1:-all}" in
    frontend)
        deploy_frontend
        ;;
    backend)
        deploy_backend
        ;;
    all)
        deploy_all
        ;;
    *)
        echo "Usage: ./deploy.sh [frontend|backend|all]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo "Frontend: https://adspend.consequential.io"
echo "Backend:  https://halo-backend-zqlsaqunba-uc.a.run.app"
