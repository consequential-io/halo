# Ad Spend Agent - Cloud Run Deployment Guide

## Prerequisites

- Google Cloud SDK installed (`gcloud`)
- Project: `otb-dev-platform`
- Region: `us-central1`

## Quick Deploy

```bash
cd /Users/jaidevk/Work/dev/halo
export PROJECT_ID=otb-dev-platform
gcloud config set project $PROJECT_ID
```

---

## Step 1: Deploy Backend

```bash
cd backend

gcloud run deploy halo-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,DATA_SOURCE=bq,GCP_PROJECT=$PROJECT_ID"

# Get backend URL
BACKEND_URL=$(gcloud run services describe halo-backend --region us-central1 --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

**Backend URL:** https://halo-backend-zqlsaqunba-uc.a.run.app

---

## Step 2: Deploy Frontend

```bash
cd ../frontend

gcloud run deploy halo-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "VITE_API_URL=$BACKEND_URL"
```

**Frontend URL:** https://halo-frontend-zqlsaqunba-uc.a.run.app

---

## Step 3: Configure Custom Domain

### 3.1 Add Domain Mapping (via Console)

```bash
open "https://console.cloud.google.com/run/domains?project=otb-dev-platform"
```

1. Click **"Add Mapping"**
2. Select service: `halo-frontend`
3. Enter domain: `adspend.consequential.io`
4. Copy the DNS records shown

### 3.2 Update DNS

Add to your DNS provider (for consequential.io):

| Type | Name | Value |
|------|------|-------|
| CNAME | adspend | ghs.googlehosted.com |

*Wait 15-30 mins for DNS propagation and SSL certificate provisioning*

---

## Step 4: Update Backend with Production URLs

```bash
gcloud run services update halo-backend --region us-central1 \
  --set-env-vars "ENVIRONMENT=production,DATA_SOURCE=bq,GCP_PROJECT=otb-dev-platform,META_REDIRECT_URI=https://halo-backend-zqlsaqunba-uc.a.run.app/auth/meta/callback,FRONTEND_URL=https://adspend.consequential.io"
```

---

## Step 5: Configure Meta OAuth

### 5.1 Meta Developer Console

Go to: https://developers.facebook.com/apps/3719964444932293/fb-login/settings/

Add to **Valid OAuth Redirect URIs**:
```
https://halo-backend-zqlsaqunba-uc.a.run.app/auth/meta/callback
```

### 5.2 Add Test Users (Development Mode)

Since the app is in Development mode, add demo users:
1. Go to App Roles → Roles
2. Add testers by Facebook email

---

## Step 6: Verify Deployment

```bash
# Backend health
curl https://halo-backend-zqlsaqunba-uc.a.run.app/

# Backend tenants
curl https://halo-backend-zqlsaqunba-uc.a.run.app/api/tenants

# Frontend (after DNS propagation)
curl -I https://adspend.consequential.io
```

---

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://adspend.consequential.io |
| Backend API | https://halo-backend-zqlsaqunba-uc.a.run.app |
| Meta OAuth Callback | https://halo-backend-zqlsaqunba-uc.a.run.app/auth/meta/callback |

---

## Redeploy Commands

### Backend Only
```bash
cd backend
gcloud run deploy halo-backend --source . --region us-central1
```

### Frontend Only
```bash
cd frontend
gcloud run deploy halo-frontend --source . --region us-central1
```

---

## Troubleshooting

### Check Logs
```bash
# Backend logs
gcloud run logs read halo-backend --region us-central1 --limit 50

# Frontend logs
gcloud run logs read halo-frontend --region us-central1 --limit 50
```

### Check Domain Mapping Status
```bash
gcloud beta run domain-mappings list --platform managed --region us-central1
```

### Force New Revision
```bash
gcloud run services update halo-backend --region us-central1 --no-traffic
gcloud run services update-traffic halo-backend --region us-central1 --to-latest
```
