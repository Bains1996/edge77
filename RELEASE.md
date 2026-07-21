# EDGE77 — Release Guide

## Local Development

```bash
cd edge77
cp .env.example .env
# Edit .env with your values (see Required Environment Variables below)
python -m uvicorn v1_ingestion.main_gateway:app --host 0.0.0.0 --port 8080 --reload
```

Landing page: http://localhost:8080/
Dashboard: http://localhost:8080/dashboard
Health: http://localhost:8080/health
API docs: http://localhost:8080/docs

### Dashboard Auth

The dashboard reads your API token from browser localStorage. To connect:

1. Open http://localhost:8080/dashboard
2. Open browser console (F12)
3. Run: `localStorage.setItem('edge77_api_token', 'YOUR_INTERNAL_API_TOKEN')`
4. Refresh the page

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase service_role key | `eyJ...` |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-...` |
| `INTERNAL_API_TOKEN` | Bearer token for API auth | Random string (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `ENVIRONMENT` | `production` or `development` | `production` |
| `RATE_LIMIT_PER_MINUTE` | Max requests per IP per minute | `100` |
| `MAX_PDF_SIZE_MB` | Max upload size in MB | `20` |
| `LOG_LEVEL` | `INFO`, `DEBUG`, `WARNING` | `INFO` |

Optional email providers (first configured wins):

| Variable | Description |
|----------|-------------|
| `AWS_SES_ACCESS_KEY` | AWS SES access key (best option) |
| `AWS_SES_SECRET_KEY` | AWS SES secret key |
| `AWS_SES_REGION` | AWS region (default: `us-east-1`) |
| `GMAIL_ADDRESS` | Gmail SMTP address |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `BREVO_API_KEY` | Brevo API key |
| `SENDGRID_API_KEY` | SendGrid API key |

## Run Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

Expected: 21 tests pass, 0 fail.

## Deploy to Cloud Run

### Prerequisites
- GCP project `edge77-prod` with billing enabled
- Artifact Registry repo `edge77` in `us-central1`
- GitHub secrets: `GCP_SA_KEY`, `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `INTERNAL_API_TOKEN`

### Deploy

```bash
git push origin main
```

CI/CD will:
1. Run tests
2. Build Docker image
3. Push to Artifact Registry
4. Deploy to Cloud Run
5. Verify health endpoint

### Manual Deploy

```bash
# Build
gcloud builds submit --tag us-central1-docker.pkg.dev/edge77-prod/edge77/edge77:latest

# Deploy
gcloud run deploy edge77 \
  --image us-central1-docker.pkg.dev/edge77-prod/edge77/edge77:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory=512Mi --cpu=1 \
  --min-instances=0 --max-instances=10 \
  --set-env-vars="ENVIRONMENT=production,OPENROUTER_API_KEY=<KEY>,SUPABASE_URL=<URL>,SUPABASE_KEY=<KEY>,INTERNAL_API_TOKEN=<TOKEN>,RATE_LIMIT_PER_MINUTE=100,MAX_PDF_SIZE_MB=20,LOG_LEVEL=INFO"
```

## Post-Deploy Verification

```bash
SERVICE_URL="https://edge77.app"

# 1. Health check
curl $SERVICE_URL/health

# 2. Expected: status=healthy, mode=production, supabase=ok

# 3. Landing page
curl -s $SERVICE_URL/ | head -5

# 4. Dashboard
curl -s $SERVICE_URL/dashboard | head -5
```

## Operational Runbook

### Service won't start
- Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=edge77" --limit 50`
- Common cause: missing env vars (service starts in mock mode, or crashes)

### Health returns "degraded"
- `supabase: error` — Supabase credentials wrong or DB down
- `openrouter: not_configured` — OPENROUTER_API_KEY not set

### Ingest returns 401
- Check INTERNAL_API_TOKEN is set in Cloud Run env vars
- Check client is sending `Authorization: Bearer <token>` header
- Check client is sending `X-Timestamp` header (within last 5 minutes)

### Dashboard shows mock data
- Open browser console — check for 401/403 errors
- Ensure `localStorage.edge77_api_token` is set with correct token
- Refresh the page

### Emails not sending
- Check Cloud Run logs for email provider errors
- Only one provider is active (first configured wins: SES > Gmail > Brevo > SendGrid)
- If no provider configured, disputes are logged but not sent

### Disk filling up
- Temp PDF files are auto-cleaned (try/finally in pdf_extractor.py)
- If issue persists, check `/tmp` usage in container
